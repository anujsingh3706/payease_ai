# backend/app/routers/ai/fraud.py

from fastapi        import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic       import BaseModel, Field
from typing         import Optional
from decimal        import Decimal

from app.database            import get_db
from app.models.user         import User
from app.models.account      import Account, AccountStatus
from app.ai.fraud_detector   import run_fraud_check
from app.utils.dependencies  import get_current_user

router = APIRouter(prefix="/api/v1/ai/fraud", tags=["🔴 Fraud Detection"])


# ── Request / Response Schemas ────────────────────────────────────────────────

class FraudCheckRequest(BaseModel):
    amount:           float   = Field(..., gt=0)
    transfer_mode:    str     = Field(default="imps")
    to_account_number: Optional[str] = None
    to_upi_id:        Optional[str]  = None

    class Config:
        json_schema_extra = {
            "example": {
                "amount":            50000,
                "transfer_mode":     "imps",
                "to_account_number": "2024987654321"
            }
        }


class FraudCheckResponse(BaseModel):
    fraud_score: float
    is_fraud:    bool
    risk_level:  str
    action:      str
    reasons:     list
    message:     str


# ── Pre-Transaction Fraud Check ───────────────────────────────────────────────

@router.post("/check", response_model=FraudCheckResponse)
async def check_transaction_fraud(
    request: FraudCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run fraud check on a transaction BEFORE executing it.

    Risk Levels:
    - LOW (< 0.3)      → ✅ ALLOW — Safe transaction
    - MEDIUM (0.3-0.5) → ✅ ALLOW — Minor anomaly, proceed with caution
    - HIGH (0.5-0.7)   → ⚠️ REVIEW — Flagged, requires extra OTP
    - CRITICAL (> 0.7) → 🚫 BLOCK — Transaction blocked

    Fraud factors checked:
    - Transaction amount vs user history
    - Time of transaction (odd hours flag)
    - Transaction frequency in last hour
    - New beneficiary + large amount
    - Amount vs account balance ratio
    """

    # Get user's primary account
    account = db.query(Account).filter(
        Account.user_id    == current_user.id,
        Account.is_primary == True,
        Account.account_status == AccountStatus.ACTIVE
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Active account not found")

    result = run_fraud_check(
        db                = db,
        user              = current_user,
        account           = account,
        amount            = request.amount,
        transfer_mode     = request.transfer_mode,
        to_account_number = request.to_account_number,
        to_upi_id         = request.to_upi_id
    )

    # Generate user-friendly message
    if result["risk_level"] == "LOW":
        message = "Transaction appears safe. Proceed normally."
    elif result["risk_level"] == "MEDIUM":
        message = "Transaction looks slightly unusual. Verify recipient details before proceeding."
    elif result["risk_level"] == "HIGH":
        message = "⚠️ This transaction has been flagged as suspicious. Additional OTP verification required."
    else:
        message = "🚫 Transaction blocked due to high fraud risk. Contact support if this is a genuine transaction."

    return FraudCheckResponse(
        fraud_score = result["fraud_score"],
        is_fraud    = result["is_fraud"],
        risk_level  = result["risk_level"],
        action      = result["action"],
        reasons     = result["reasons"],
        message     = message
    )


# ── Fraud Statistics (Admin) ──────────────────────────────────────────────────

@router.get("/my-flagged")
async def get_my_flagged_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all flagged transactions for the current user"""
    from app.models.transaction import Transaction

    flagged = db.query(Transaction).filter(
        Transaction.user_id    == current_user.id,
        Transaction.is_flagged == True
    ).order_by(Transaction.initiated_at.desc()).all()

    return {
        "total_flagged": len(flagged),
        "transactions": [
            {
                "ref":          t.transaction_ref,
                "amount":       float(t.amount),
                "fraud_score":  float(t.fraud_score) if t.fraud_score else 0,
                "fraud_reason": t.fraud_reason,
                "status":       t.transaction_status.value,
                "date":         t.initiated_at.isoformat()
            }
            for t in flagged
        ]
    }


# ── Train Model Endpoint (Admin only) ────────────────────────────────────────

@router.post("/retrain")
async def retrain_fraud_model(
    current_user: User = Depends(get_current_user)
):
    """
    Retrain fraud detection model with latest data.
    Admin only — call when you have new transaction data.
    """
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.ai.fraud_model import train_fraud_model
    train_fraud_model()

    return {"message": "✅ Fraud model retrained successfully"}