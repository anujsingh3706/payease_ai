# backend/app/routers/payments.py

from fastapi        import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal        import Decimal

from app.database              import get_db
from app.models.user           import User
from app.schemas.account       import RazorpayOrderCreate, RazorpayPaymentVerify
from app.services.payment_service import PaymentService
from app.services.wallet_service  import WalletService
from app.utils.dependencies    import get_current_user

router = APIRouter(prefix="/api/v1/payments", tags=["Payments (Razorpay)"])


# ── Create Razorpay Order ─────────────────────────────────────────────────────

@router.post("/create-order")
async def create_payment_order(
    order_data: RazorpayOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1 of Razorpay payment:
    Creates an order and returns order_id to frontend.

    Frontend uses this order_id to open Razorpay checkout popup.
    """
    return PaymentService.create_order(order_data.amount)


# ── Verify Payment & Credit Wallet ───────────────────────────────────────────

@router.post("/verify")
async def verify_and_credit(
    payment_data: RazorpayPaymentVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2 of Razorpay payment:
    1. Verifies HMAC signature (prevents fraud)
    2. Credits wallet on success
    3. Records transaction in DB
    """
    # Verify signature
    is_valid = PaymentService.verify_payment(
        payment_data.razorpay_order_id,
        payment_data.razorpay_payment_id,
        payment_data.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed. Possible fraud attempt."
        )

    # Fetch actual amount from Razorpay
    payment_details = PaymentService.get_payment_details(
        payment_data.razorpay_payment_id
    )
    amount = Decimal(str(payment_details["amount"]))

    # Credit wallet
    return WalletService.add_money_to_wallet(
        db,
        current_user.id,
        amount,
        payment_data.razorpay_payment_id
    )


# ── Payment Info ──────────────────────────────────────────────────────────────

@router.get("/info/{payment_id}")
async def get_payment_info(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Fetch payment details from Razorpay"""
    return PaymentService.get_payment_details(payment_id)