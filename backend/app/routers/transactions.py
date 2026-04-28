# backend/app/routers/transactions.py

from fastapi        import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database              import get_db
from app.models.user           import User
from app.schemas.account       import FundTransferRequest
from app.services.account_service import AccountService
from app.utils.dependencies    import get_current_user

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions & Transfers"])


# ── Fund Transfer ─────────────────────────────────────────────────────────────

@router.post("/transfer")
async def fund_transfer(
    transfer_data: FundTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Transfer funds via NEFT / RTGS / IMPS.

    - NEFT: ₹1 to ₹5,00,000 | Charges apply
    - RTGS: Minimum ₹2,00,000 | Charges apply
    - IMPS: ₹1 to ₹2,00,000 | Charges apply
    - Requires MPIN verification
    """
    return AccountService.fund_transfer(db, current_user, transfer_data)


# ── Transfer Charges Info ─────────────────────────────────────────────────────

@router.get("/charges")
async def get_transfer_charges():
    """Get information about transfer charges"""
    return {
        "neft": {
            "description": "National Electronic Fund Transfer",
            "min_amount":  1,
            "max_amount":  500000,
            "charges": {
                "up_to_10000":         "₹2.00",
                "10001_to_100000":     "₹5.00",
                "100001_to_200000":    "₹15.00",
                "200001_to_500000":    "₹25.00"
            },
            "timing": "Available 24x7 (NEFT batches every 30 mins)"
        },
        "rtgs": {
            "description": "Real Time Gross Settlement",
            "min_amount":  200000,
            "max_amount":  10000000,
            "charges": {
                "200001_to_500000":     "₹25.00",
                "above_500000":         "₹50.00"
            },
            "timing": "Real-time settlement"
        },
        "imps": {
            "description": "Immediate Payment Service",
            "min_amount":  1,
            "max_amount":  500000,
            "charges": {
                "up_to_1000":          "₹2.50",
                "1001_to_25000":       "₹5.00",
                "25001_to_100000":     "₹15.00",
                "100001_to_200000":    "₹25.00"
            },
            "timing": "Instant 24x7"
        },
        "upi": {
            "description": "Unified Payment Interface",
            "charges": "FREE",
            "max_amount": 100000,
            "timing": "Instant"
        }
    }