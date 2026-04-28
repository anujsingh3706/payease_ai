# backend/app/ai/fraud_detector.py

"""
Real-time fraud detection integrated with transaction pipeline.
Called BEFORE every transaction is processed.
"""

from sqlalchemy.orm import Session
from sqlalchemy     import func
from datetime       import datetime, timedelta
from decimal        import Decimal
import logging

from app.models.user        import User
from app.models.account     import Account
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.wallet      import Beneficiary
from app.ai.fraud_model     import score_transaction

logger = logging.getLogger(__name__)


def get_user_transaction_stats(db: Session, user_id, account_id) -> dict:
    """
    Compute user's historical transaction statistics.
    Used to calculate z-score (how unusual current amount is).
    """

    # Last 30 days transactions
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    stats = db.query(
        func.avg(Transaction.amount).label("avg_amount"),
        func.stddev(Transaction.amount).label("std_amount"),
        func.count(Transaction.id).label("total_count")
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= thirty_days_ago
    ).first()

    # Transactions in the last 1 hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_count = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == user_id,
        Transaction.initiated_at >= one_hour_ago
    ).scalar() or 0

    return {
        "avg_amount":    float(stats.avg_amount or 5000),
        "std_amount":    float(stats.std_amount or 3000),
        "total_count":   stats.total_count or 0,
        "txn_count_1hr": recent_count
    }


def is_new_beneficiary_account(
    db: Session,
    user_id,
    to_account_number: str = None,
    to_upi_id: str = None
) -> bool:
    """
    Check if this is the first time sending to this beneficiary.
    New beneficiary = higher fraud risk for large amounts.
    """
    # Check saved beneficiaries list
    if to_account_number:
        saved = db.query(Beneficiary).filter(
            Beneficiary.user_id        == user_id,
            Beneficiary.account_number == to_account_number
        ).first()
        if saved:
            return False   # Known beneficiary

        # Check transaction history
        previous_txn = db.query(Transaction).filter(
            Transaction.user_id           == user_id,
            Transaction.to_account_number == to_account_number,
            Transaction.transaction_status == TransactionStatus.SUCCESS
        ).first()
        return previous_txn is None

    if to_upi_id:
        previous = db.query(Transaction).filter(
            Transaction.user_id   == user_id,
            Transaction.to_upi_id == to_upi_id,
            Transaction.transaction_status == TransactionStatus.SUCCESS
        ).first()
        return previous is None

    return True   # Default: treat as new


def run_fraud_check(
    db:              Session,
    user:            User,
    account:         Account,
    amount:          float,
    transfer_mode:   str,
    to_account_number: str = None,
    to_upi_id:       str = None
) -> dict:
    """
    Main fraud check function.
    Call this before processing ANY transaction.

    Returns fraud assessment with score, risk level, and action.
    """

    # Get user's transaction history stats
    stats = get_user_transaction_stats(db, user.id, account.id)

    # Check if new beneficiary
    new_bene = is_new_beneficiary_account(
        db, user.id, to_account_number, to_upi_id
    )

    # Run fraud scoring
    result = score_transaction(
        amount              = amount,
        transfer_mode       = transfer_mode,
        is_new_beneficiary  = new_bene,
        user_avg_amount     = stats["avg_amount"],
        user_std_amount     = stats["std_amount"],
        txn_count_1hr       = stats["txn_count_1hr"],
        account_balance     = float(account.balance),
        transaction_time    = datetime.utcnow()
    )

    # Log high-risk transactions
    if result["risk_level"] in ["HIGH", "CRITICAL"]:
        logger.warning(
            f"🚨 FRAUD ALERT | User: {user.email} | "
            f"Amount: ₹{amount:,.2f} | "
            f"Score: {result['fraud_score']} | "
            f"Level: {result['risk_level']} | "
            f"Reasons: {result['reasons']}"
        )

    return result