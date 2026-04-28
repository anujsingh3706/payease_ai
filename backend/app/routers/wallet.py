# backend/app/routers/wallet.py

from fastapi        import APIRouter, Depends
from sqlalchemy.orm import Session
from decimal        import Decimal

from app.database            import get_db
from app.models.user         import User
from app.schemas.account     import WalletResponse, WalletTransferRequest
from app.services.wallet_service  import WalletService
from app.utils.dependencies  import get_current_user
import qrcode
import io
import base64

router = APIRouter(prefix="/api/v1/wallet", tags=["Wallet & UPI"])


# ── Get Wallet ────────────────────────────────────────────────────────────────

@router.get("/", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wallet details and balance"""
    return WalletService.get_wallet(db, current_user.id)


# ── UPI Transfer ──────────────────────────────────────────────────────────────

@router.post("/transfer")
async def upi_transfer(
    transfer_data: WalletTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send money via UPI (wallet to wallet).
    Format: phone_number@payease
    Requires MPIN. Instant. FREE.
    """
    return WalletService.wallet_transfer(db, current_user, transfer_data)


# ── Generate UPI QR Code ──────────────────────────────────────────────────────

@router.get("/qr-code")
async def get_qr_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate QR code for UPI payments"""
    wallet = WalletService.get_wallet(db, current_user.id)

    if not wallet.upi_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="UPI ID not set")

    # UPI deep link format (standard UPI spec)
    upi_link = (
        f"upi://pay?pa={wallet.upi_id}"
        f"&pn={current_user.full_name.replace(' ', '%20')}"
        f"&am=&cu=INR"
    )

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(upi_link)
    qr.make(fit=True)

    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return {
        "upi_id":    wallet.upi_id,
        "full_name": current_user.full_name,
        "upi_link":  upi_link,
        "qr_code":   f"data:image/png;base64,{img_base64}"
    }