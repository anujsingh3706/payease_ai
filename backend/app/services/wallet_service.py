# backend/app/services/wallet_service.py

from sqlalchemy.orm import Session
from sqlalchemy   import func
from fastapi       import HTTPException, status
from datetime      import datetime, date
from decimal       import Decimal
import logging

from app.models.user        import User
from app.models.wallet      import Wallet, Beneficiary
from app.models.account     import Account, AccountStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionMode
from app.schemas.account    import WalletTransferRequest
from app.utils.password_handler  import verify_mpin
from app.utils.account_generator import generate_transaction_ref

logger = logging.getLogger(__name__)


class WalletService:

    @staticmethod
    def get_wallet(db: Session, user_id) -> Wallet:
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        return wallet

    # ─────────────────────────────────────────────────────────────────────────
    # ADD MONEY TO WALLET (after Razorpay payment success)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def add_money_to_wallet(
        db: Session,
        user_id,
        amount: Decimal,
        razorpay_payment_id: str
    ) -> dict:
        """Credit wallet after successful Razorpay payment"""

        wallet = WalletService.get_wallet(db, user_id)

        if not wallet.is_active or wallet.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet is blocked or inactive"
            )

        # Check monthly limit
        if float(wallet.month_spent) + float(amount) > float(wallet.monthly_limit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Monthly wallet limit of ₹{wallet.monthly_limit} exceeded"
            )

        try:
            wallet.balance      = Decimal(str(wallet.balance)) + amount
            wallet.updated_at   = datetime.utcnow()

            txn = Transaction(
                transaction_ref    = generate_transaction_ref(),
                user_id            = user_id,
                amount             = amount,
                charges            = Decimal("0.00"),
                net_amount         = amount,
                transaction_type   = TransactionType.WALLET_TOPUP,
                transaction_mode   = TransactionMode.WALLET,
                transaction_status = TransactionStatus.SUCCESS,
                description        = "Wallet Top-up via Razorpay",
                razorpay_payment_id = razorpay_payment_id,
                completed_at       = datetime.utcnow()
            )
            db.add(txn)
            db.commit()

            return {
                "message":       "Wallet topped up successfully",
                "amount_added":  float(amount),
                "new_balance":   float(wallet.balance),
                "transaction_ref": txn.transaction_ref
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Wallet top-up failed: {e}")
            raise HTTPException(status_code=500, detail="Wallet top-up failed")

    # ─────────────────────────────────────────────────────────────────────────
    # WALLET TO WALLET TRANSFER (UPI style)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def wallet_transfer(
        db: Session,
        user: User,
        transfer_data: WalletTransferRequest
    ) -> dict:
        """Transfer money between wallets using UPI ID"""

        # Verify MPIN
        if not user.mpin_hash:
            raise HTTPException(status_code=400, detail="Set MPIN first")
        if not verify_mpin(transfer_data.mpin, user.mpin_hash):
            raise HTTPException(status_code=401, detail="Invalid MPIN")

        sender_wallet = WalletService.get_wallet(db, user.id)

        # Check sender wallet balance
        if float(sender_wallet.balance) < float(transfer_data.amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient wallet balance"
            )

        # Cannot send to yourself
        if sender_wallet.upi_id == transfer_data.to_upi_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer to your own wallet"
            )

        # Check daily limit
        today = date.today()
        today_sent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_type == TransactionType.PAYMENT,
            Transaction.transaction_status == TransactionStatus.SUCCESS,
            func.date(Transaction.initiated_at) == today
        ).scalar() or 0

        if float(today_sent) + float(transfer_data.amount) > float(sender_wallet.daily_limit):
            raise HTTPException(
                status_code=400,
                detail=f"Daily wallet limit of ₹{sender_wallet.daily_limit} exceeded"
            )

        # Find receiver wallet by UPI ID
        receiver_wallet = db.query(Wallet).filter(
            Wallet.upi_id == transfer_data.to_upi_id
        ).first()

        if not receiver_wallet:
            raise HTTPException(status_code=404, detail="UPI ID not found")

        if not receiver_wallet.is_active or receiver_wallet.is_blocked:
            raise HTTPException(status_code=400, detail="Receiver wallet is inactive")

        try:
            # Debit sender
            sender_wallet.balance = (
                Decimal(str(sender_wallet.balance)) - transfer_data.amount
            )
            sender_wallet.today_spent = (
                Decimal(str(sender_wallet.today_spent)) + transfer_data.amount
            )

            # Credit receiver
            receiver_wallet.balance = (
                Decimal(str(receiver_wallet.balance)) + transfer_data.amount
            )

            txn_ref = generate_transaction_ref()

            # Debit transaction for sender
            debit_txn = Transaction(
                transaction_ref    = txn_ref,
                user_id            = user.id,
                to_upi_id          = transfer_data.to_upi_id,
                amount             = transfer_data.amount,
                charges            = Decimal("0.00"),
                net_amount         = transfer_data.amount,
                transaction_type   = TransactionType.PAYMENT,
                transaction_mode   = TransactionMode.UPI,
                transaction_status = TransactionStatus.SUCCESS,
                description        = transfer_data.note or "UPI Transfer",
                completed_at       = datetime.utcnow()
            )
            db.add(debit_txn)

            # Credit transaction for receiver
            credit_txn = Transaction(
                transaction_ref    = generate_transaction_ref(),
                user_id            = receiver_wallet.user_id,
                amount             = transfer_data.amount,
                charges            = Decimal("0.00"),
                net_amount         = transfer_data.amount,
                transaction_type   = TransactionType.CREDIT,
                transaction_mode   = TransactionMode.UPI,
                transaction_status = TransactionStatus.SUCCESS,
                description        = f"Received from {sender_wallet.upi_id}",
                completed_at       = datetime.utcnow()
            )
            db.add(credit_txn)

            db.commit()

            logger.info(f"✅ UPI Transfer {txn_ref} | ₹{transfer_data.amount}")

            return {
                "message":         "Transfer successful",
                "transaction_ref": txn_ref,
                "amount":          float(transfer_data.amount),
                "to_upi_id":       transfer_data.to_upi_id,
                "new_balance":     float(sender_wallet.balance),
                "status":          "success"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"UPI transfer failed: {e}")
            raise HTTPException(status_code=500, detail="Transfer failed")