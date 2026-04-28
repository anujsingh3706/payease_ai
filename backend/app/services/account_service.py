# backend/app/services/account_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
import logging

from app.models.user    import User
from app.models.account import Account, AccountStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionMode
from app.models.wallet  import Wallet, Beneficiary
from app.schemas.account import (
    FundTransferRequest, BeneficiaryCreate,
    TransactionFilter
)
from app.utils.password_handler import verify_mpin
from app.utils.account_generator import generate_transaction_ref

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION CHARGES (like real banks)
# ─────────────────────────────────────────────────────────────────────────────

TRANSFER_CHARGES = {
    "neft": {
        (0,     10000):  2.00,
        (10000, 100000): 5.00,
        (100000, 200000): 15.00,
        (200000, 500000): 25.00,
    },
    "rtgs":  {
        (200000, 500000):  25.00,
        (500000, 10000000): 50.00,
    },
    "imps":  {
        (0,      1000):  2.50,
        (1000,   25000): 5.00,
        (25000,  100000): 15.00,
        (100000, 200000): 25.00,
    },
    "upi":   {},   # UPI is free
    "wallet": {},  # Wallet is free
}

def calculate_charges(mode: str, amount: Decimal) -> Decimal:
    """Calculate transaction charges based on mode and amount"""
    charges_map = TRANSFER_CHARGES.get(mode.lower(), {})
    for (low, high), charge in charges_map.items():
        if low <= float(amount) < high:
            return Decimal(str(charge))
    return Decimal("0.00")


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class AccountService:

    @staticmethod
    def get_user_accounts(db: Session, user_id) -> List[Account]:
        """Get all accounts of a user"""
        return db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_status != AccountStatus.CLOSED
        ).all()

    @staticmethod
    def get_account_by_number(db: Session, account_number: str) -> Optional[Account]:
        """Get account by account number"""
        return db.query(Account).filter(
            Account.account_number == account_number
        ).first()

    @staticmethod
    def get_balance(db: Session, user_id) -> dict:
        """Get total balance across all accounts"""
        accounts = AccountService.get_user_accounts(db, user_id)
        total = sum(acc.balance for acc in accounts)
        return {
            "accounts": [
                {
                    "account_number": acc.account_number,
                    "account_type":   acc.account_type.value,
                    "balance":        float(acc.balance),
                    "status":         acc.account_status.value
                }
                for acc in accounts
            ],
            "total_balance": float(total)
        }

    # ─────────────────────────────────────────────────────────────────────────
    # FUND TRANSFER — Core Banking Logic
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def fund_transfer(
        db: Session,
        user: User,
        transfer_data: FundTransferRequest
    ) -> dict:
        """
        NEFT / RTGS / IMPS fund transfer with:
        - MPIN verification
        - Balance check
        - Daily limit check
        - Charge calculation
        - Fraud detection check
        - Atomic DB transaction (ACID)
        """

        # ── Step 1 — Verify MPIN ──────────────────────────────────────────────
        if not user.mpin_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Set your MPIN first before making transactions"
            )
        if not verify_mpin(transfer_data.mpin, user.mpin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MPIN"
            )

        # ── Step 2 — Get sender's primary account ─────────────────────────────
        from_account = db.query(Account).filter(
            Account.user_id == user.id,
            Account.is_primary == True,
            Account.account_status == AccountStatus.ACTIVE
        ).first()

        if not from_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active account found"
            )

        # ── Step 3 — Get receiver's account ───────────────────────────────────
        if transfer_data.to_account_number == from_account.account_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer to your own account"
            )

        to_account = db.query(Account).filter(
            Account.account_number == transfer_data.to_account_number,
            Account.account_status == AccountStatus.ACTIVE
        ).first()

        if not to_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination account not found or inactive"
            )

        # ── Step 4 — Calculate charges ────────────────────────────────────────
        charges   = calculate_charges(transfer_data.transfer_mode, transfer_data.amount)
        net_total = transfer_data.amount + charges   # Total deducted from sender

        # ── Step 5 — Check minimum balance ────────────────────────────────────
        if float(from_account.balance) - float(net_total) < float(from_account.minimum_balance):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Minimum balance ₹{from_account.minimum_balance} must be maintained."
            )

        # ── Step 6 — Check daily limit ────────────────────────────────────────
        today = date.today()
        today_sent = db.query(func.sum(Transaction.net_amount)).filter(
            Transaction.from_account_id == from_account.id,
            Transaction.transaction_status == TransactionStatus.SUCCESS,
            func.date(Transaction.initiated_at) == today
        ).scalar() or 0

        if float(today_sent) + float(net_total) > float(from_account.daily_limit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily transfer limit of ₹{from_account.daily_limit} exceeded"
            )

        # ── Step 7 — RTGS minimum check ───────────────────────────────────────
        if transfer_data.transfer_mode == "rtgs" and float(transfer_data.amount) < 200000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RTGS minimum transfer amount is ₹2,00,000"
            )

        # ── Step 7B — FRAUD DETECTION CHECK ──────────────────────────────────
        from app.ai.fraud_detector import run_fraud_check

        fraud_result = run_fraud_check(
            db                = db,
            user              = user,
            account           = from_account,
            amount            = float(transfer_data.amount),
            transfer_mode     = transfer_data.transfer_mode,
            to_account_number = transfer_data.to_account_number
        )

        # Block CRITICAL risk transactions
        if fraud_result["action"] == "BLOCK":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message":    "Transaction blocked by fraud detection system",
                    "risk_level": fraud_result["risk_level"],
                    "reasons":    fraud_result["reasons"],
                    "contact":    "Contact support if this is a genuine transaction"
                }
            )

        # For HIGH risk — still allow but flag it in the record
        is_flagged   = fraud_result["is_fraud"]
        fraud_score  = fraud_result["fraud_score"]
        fraud_reason = "; ".join(fraud_result["reasons"]) if fraud_result["reasons"] else None

        # ── Step 8 — ATOMIC DATABASE TRANSACTION ─────────────────────────────
        try:
            # Debit sender
            from_account.balance = Decimal(str(from_account.balance)) - net_total

            # Credit receiver
            to_account.balance = Decimal(str(to_account.balance)) + transfer_data.amount

            # Create transaction record
            txn = Transaction(
                transaction_ref    = generate_transaction_ref(),
                user_id            = user.id,
                from_account_id    = from_account.id,
                to_account_id      = to_account.id,
                to_account_number  = transfer_data.to_account_number,
                amount             = transfer_data.amount,
                charges            = charges,
                net_amount         = net_total,
                transaction_type   = TransactionType.TRANSFER,
                transaction_mode   = TransactionMode[transfer_data.transfer_mode.upper()],
                transaction_status = TransactionStatus.SUCCESS,
                description        = transfer_data.description or f"{transfer_data.transfer_mode.upper()} Transfer",
                completed_at       = datetime.utcnow(),
                metadata           = {"initiated_by": str(user.id)},
                # ── Fraud Detection Results ───────────────────────────────────
                is_flagged         = is_flagged,
                fraud_score        = fraud_score,
                fraud_reason       = fraud_reason,
            )
            db.add(txn)
            db.commit()
            db.refresh(txn)

            logger.info(
                f"✅ Transfer {txn.transaction_ref} | "
                f"₹{transfer_data.amount} | "
                f"{user.email} | "
                f"Fraud Score: {fraud_score} | "
                f"Flagged: {is_flagged}"
            )

            return {
                "message":         "Transfer successful",
                "transaction_ref": txn.transaction_ref,
                "amount":          float(transfer_data.amount),
                "charges":         float(charges),
                "net_deducted":    float(net_total),
                "status":          "success",
                "to_account":      transfer_data.to_account_number,
                "new_balance":     float(from_account.balance),
                "timestamp":       txn.initiated_at.isoformat(),
                "fraud_score":     fraud_score,
                "is_flagged":      is_flagged,
                "risk_level":      fraud_result["risk_level"]
            }

        except HTTPException:
            # Re-raise HTTP exceptions (don't swallow them)
            db.rollback()
            raise

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Transfer failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transaction failed. Please try again."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # TRANSACTION HISTORY
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_transactions(
        db: Session,
        user_id,
        filters: TransactionFilter
    ) -> dict:
        """Get paginated transaction history with filters"""

        query = db.query(Transaction).filter(Transaction.user_id == user_id)

        # Apply filters
        if filters.transaction_type:
            query = query.filter(
                Transaction.transaction_type == filters.transaction_type
            )
        if filters.status:
            query = query.filter(
                Transaction.transaction_status == filters.status
            )
        if filters.from_date:
            query = query.filter(Transaction.initiated_at >= filters.from_date)
        if filters.to_date:
            query = query.filter(Transaction.initiated_at <= filters.to_date)
        if filters.min_amount:
            query = query.filter(Transaction.amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(Transaction.amount <= filters.max_amount)

        total  = query.count()
        offset = (filters.page - 1) * filters.limit
        transactions = query.order_by(
            Transaction.initiated_at.desc()
        ).offset(offset).limit(filters.limit).all()

        return {
            "total":        total,
            "page":         filters.page,
            "limit":        filters.limit,
            "total_pages":  (total + filters.limit - 1) // filters.limit,
            "transactions": [
                {
                    "id":               str(t.id),
                    "ref":              t.transaction_ref,
                    "amount":           float(t.amount),
                    "charges":          float(t.charges),
                    "type":             t.transaction_type.value,
                    "mode":             t.transaction_mode.value if t.transaction_mode else None,
                    "status":           t.transaction_status.value,
                    "description":      t.description,
                    "category":         t.category,
                    "is_flagged":       t.is_flagged,
                    "fraud_score":      float(t.fraud_score) if t.fraud_score else 0.0,
                    "to_account":       t.to_account_number,
                    "to_upi":           t.to_upi_id,
                    "date":             t.initiated_at.isoformat()
                }
                for t in transactions
            ]
        }

    @staticmethod
    def get_mini_statement(db: Session, user_id, limit: int = 10) -> dict:
        """Get last N transactions — passbook style"""

        account = db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_primary == True
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        transactions = db.query(Transaction).filter(
            or_(
                Transaction.from_account_id == account.id,
                Transaction.to_account_id == account.id
            ),
            Transaction.transaction_status == TransactionStatus.SUCCESS
        ).order_by(Transaction.initiated_at.desc()).limit(limit).all()

        total_credit = db.query(func.sum(Transaction.amount)).filter(
            Transaction.to_account_id == account.id,
            Transaction.transaction_status == TransactionStatus.SUCCESS
        ).scalar() or 0

        total_debit = db.query(func.sum(Transaction.net_amount)).filter(
            Transaction.from_account_id == account.id,
            Transaction.transaction_status == TransactionStatus.SUCCESS
        ).scalar() or 0

        return {
            "account_number":  account.account_number,
            "account_type":    account.account_type.value,
            "current_balance": float(account.balance),
            "total_credit":    float(total_credit),
            "total_debit":     float(total_debit),
            "transactions": [
                {
                    "ref":         t.transaction_ref,
                    "type":        "CR" if t.to_account_id == account.id else "DR",
                    "amount":      float(t.amount),
                    "description": t.description,
                    "date":        t.initiated_at.strftime("%d %b %Y %H:%M"),
                    "status":      t.transaction_status.value
                }
                for t in transactions
            ]
        }