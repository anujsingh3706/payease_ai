# backend/app/services/dashboard_service.py

from sqlalchemy.orm import Session
from sqlalchemy     import func
from datetime       import datetime, date
from decimal        import Decimal

from app.models.account     import Account, AccountStatus
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.wallet      import Wallet


class DashboardService:

    @staticmethod
    def get_dashboard(db: Session, user_id) -> dict:
        """
        Returns complete dashboard data:
        - Account & wallet balances
        - Monthly stats
        - Recent transactions
        - Quick spend by category
        """

        # Get primary account
        account = db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_primary == True
        ).first()

        # Get wallet
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()

        now   = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # This month's stats
        month_sent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_([
                TransactionType.TRANSFER,
                TransactionType.PAYMENT,
                TransactionType.DEBIT
            ]),
            Transaction.transaction_status == TransactionStatus.SUCCESS,
            Transaction.initiated_at >= month_start
        ).scalar() or 0

        month_received = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_([
                TransactionType.CREDIT,
                TransactionType.WALLET_TOPUP
            ]),
            Transaction.transaction_status == TransactionStatus.SUCCESS,
            Transaction.initiated_at >= month_start
        ).scalar() or 0

        # Total transaction counts
        total_txns    = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0

        pending_txns  = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_status == TransactionStatus.PENDING
        ).scalar() or 0

        flagged_txns  = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id,
            Transaction.is_flagged == True
        ).scalar() or 0

        # Recent 5 transactions
        recent = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.initiated_at.desc()).limit(5).all()

        return {
            "account_balance":       float(account.balance) if account else 0.0,
            "account_number":        account.account_number if account else None,
            "wallet_balance":        float(wallet.balance) if wallet else 0.0,
            "upi_id":                wallet.upi_id if wallet else None,
            "this_month_spent":      float(month_sent),
            "this_month_received":   float(month_received),
            "total_transactions":    total_txns,
            "pending_transactions":  pending_txns,
            "flagged_transactions":  flagged_txns,
            "recent_transactions": [
                {
                    "ref":         t.transaction_ref,
                    "amount":      float(t.amount),
                    "type":        t.transaction_type.value,
                    "status":      t.transaction_status.value,
                    "description": t.description,
                    "date":        t.initiated_at.strftime("%d %b %Y %H:%M"),
                    "is_flagged":  t.is_flagged
                }
                for t in recent
            ]
        }