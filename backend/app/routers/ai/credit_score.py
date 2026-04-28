# backend/app/routers/ai/credit_score.py

from fastapi        import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy     import func
from pydantic       import BaseModel, Field
from typing         import Optional
from datetime       import datetime, timedelta

from app.database            import get_db
from app.models.user         import User
from app.models.account      import Account
from app.models.transaction  import Transaction, TransactionStatus, TransactionType
from app.models.loan         import LoanApplication, LoanStatus
from app.ai.credit_model     import predict_credit_score
from app.utils.dependencies  import get_current_user

router = APIRouter(prefix="/api/v1/ai/credit", tags=["💳 Credit Score"])


# ── Manual Input Schema (for users who enter data manually) ──────────────────

class CreditScoreManualRequest(BaseModel):
    monthly_income:         float = Field(..., gt=0,  description="Monthly income in ₹")
    monthly_expenses:       float = Field(..., gt=0,  description="Monthly expenses in ₹")
    payment_history_score:  float = Field(default=80, ge=0, le=100)
    credit_utilization:     float = Field(default=30, ge=0, le=100)
    num_missed_payments:    int   = Field(default=0,  ge=0)
    num_active_loans:       int   = Field(default=0,  ge=0)
    num_credit_inquiries:   int   = Field(default=1,  ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "monthly_income":        50000,
                "monthly_expenses":      30000,
                "payment_history_score": 90,
                "credit_utilization":    25,
                "num_missed_payments":   0,
                "num_active_loans":      1,
                "num_credit_inquiries":  2
            }
        }


# ── Auto Credit Score (uses real account data) ────────────────────────────────

@router.get("/score")
async def get_auto_credit_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-calculate credit score using real account data.
    No manual input needed — pulls data from your account.

    Factors used:
    - Account age
    - Transaction history
    - Balance levels
    - Active loan applications
    """

    # Get account
    account = db.query(Account).filter(
        Account.user_id    == current_user.id,
        Account.is_primary == True
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Account age in months
    account_age = 0
    if account.opened_at:
        delta           = datetime.utcnow() - account.opened_at
        account_age     = int(delta.days / 30)

    # Transaction stats
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)

    total_txns = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id == current_user.id,
        Transaction.initiated_at >= twelve_months_ago
    ).scalar() or 0

    txn_per_month = max(1, total_txns // 12)

    # Estimate monthly income from credits
    monthly_credits = db.query(func.avg(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.CREDIT,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= twelve_months_ago
    ).scalar() or 30000

    # Estimate expenses from debits
    monthly_debits = db.query(func.avg(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_([
            TransactionType.DEBIT,
            TransactionType.TRANSFER,
            TransactionType.PAYMENT
        ]),
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= twelve_months_ago
    ).scalar() or 20000

    # Active loans
    active_loans = db.query(func.count(LoanApplication.id)).filter(
        LoanApplication.user_id == current_user.id,
        LoanApplication.loan_status.in_([LoanStatus.APPROVED, LoanStatus.DISBURSED])
    ).scalar() or 0

    # Flagged transactions (proxy for issues)
    flagged_count = db.query(func.count(Transaction.id)).filter(
        Transaction.user_id    == current_user.id,
        Transaction.is_flagged == True
    ).scalar() or 0

    monthly_income   = float(monthly_credits)
    monthly_expenses = float(monthly_debits)
    savings_rate     = max(0, (monthly_income - monthly_expenses) / max(monthly_income, 1))
    loan_repayment   = min(1.0, active_loans * 5000 / max(monthly_income, 1))

    features = {
        "payment_history_score":  max(60, 100 - flagged_count * 5),
        "credit_utilization":     min(90, 30 + flagged_count * 5),
        "account_age_months":     account_age,
        "num_active_loans":       active_loans,
        "num_missed_payments":    flagged_count,
        "total_balance":          float(account.balance),
        "monthly_income":         monthly_income,
        "monthly_expenses":       monthly_expenses,
        "num_credit_inquiries":   1,
        "transaction_frequency":  txn_per_month,
        "savings_rate":           savings_rate,
        "loan_repayment_ratio":   loan_repayment
    }

    result = predict_credit_score(features)

    return {
        **result,
        "data_source": "auto",
        "note": "Score calculated from your real account activity"
    }


# ── Manual Credit Score (user provides own data) ─────────────────────────────

@router.post("/score/manual")
async def get_manual_credit_score(
    request: CreditScoreManualRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate credit score with manually entered financial data.
    Useful for checking score with different financial scenarios.
    """

    account = db.query(Account).filter(
        Account.user_id    == current_user.id,
        Account.is_primary == True
    ).first()

    account_age = 0
    if account and account.opened_at:
        delta       = datetime.utcnow() - account.opened_at
        account_age = int(delta.days / 30)

    savings_rate     = max(0, (request.monthly_income - request.monthly_expenses)
                         / max(request.monthly_income, 1))
    loan_repayment   = min(1.0, request.num_active_loans * 5000
                         / max(request.monthly_income, 1))

    features = {
        "payment_history_score":  request.payment_history_score,
        "credit_utilization":     request.credit_utilization,
        "account_age_months":     account_age,
        "num_active_loans":       request.num_active_loans,
        "num_missed_payments":    request.num_missed_payments,
        "total_balance":          float(account.balance) if account else 10000,
        "monthly_income":         request.monthly_income,
        "monthly_expenses":       request.monthly_expenses,
        "num_credit_inquiries":   request.num_credit_inquiries,
        "transaction_frequency":  10,
        "savings_rate":           savings_rate,
        "loan_repayment_ratio":   loan_repayment
    }

    result = predict_credit_score(features)
    return {**result, "data_source": "manual"}


# ── Score History Chart Data ──────────────────────────────────────────────────

@router.get("/score/history")
async def credit_score_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns simulated monthly credit score trend.
    Shows how score has changed over the last 6 months.
    """
    import random
    random.seed(int(str(current_user.id)[:8], 16))

    base   = random.randint(650, 800)
    months = []
    score  = base

    for i in range(6, 0, -1):
        month = (datetime.utcnow() - timedelta(days=30*i))
        delta = random.randint(-15, 20)
        score = int(max(300, min(900, score + delta)))
        months.append({
            "month": month.strftime("%b %Y"),
            "score": score
        })

    return {
        "history":       months,
        "current_score": score,
        "trend":         "improving" if months[-1]["score"] > months[0]["score"] else "declining"
    }