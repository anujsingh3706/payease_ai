# backend/app/routers/auth.py
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.schemas.user import (
    UserRegister, UserLogin, Token,
    UserProfile, UserUpdate, KYCUpdate,
    SetMPIN, VerifyMPIN, ChangePassword
)
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user
from app.utils.password_handler import hash_mpin, verify_mpin, hash_password, verify_password
from app.models.user import User, KYCStatus

router  = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    Automatically creates:
    - Savings Account
    - Wallet with UPI ID
    """
    return AuthService.register_user(db, user_data)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login and receive JWT tokens.
    - Max 5 failed attempts → account locked
    - Tracks login IP and device
    """
    return AuthService.login_user(db, login_data, request)


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True)
):
    """Get new access token using refresh token"""
    return AuthService.refresh_access_token(refresh_token)


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/profile")
async def update_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}


# ── KYC ───────────────────────────────────────────────────────────────────────

@router.post("/kyc")
async def submit_kyc(
    kyc_data: KYCUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit KYC documents"""
    # Check if already verified
    if current_user.kyc_status == KYCStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC already verified"
        )

    # Check for duplicate Aadhaar
    existing = db.query(User).filter(
        User.aadhaar_number == kyc_data.aadhaar_number,
        User.id != current_user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aadhaar already linked to another account"
        )

    current_user.aadhaar_number = kyc_data.aadhaar_number
    current_user.pan_number     = kyc_data.pan_number
    current_user.kyc_status     = KYCStatus.VERIFIED   # Auto-verify for now
    db.commit()

    return {"message": "KYC submitted and verified successfully"}


# ── MPIN ──────────────────────────────────────────────────────────────────────

@router.post("/mpin/set")
async def set_mpin(
    mpin_data: SetMPIN,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set transaction MPIN (6-digit)"""
    current_user.mpin_hash = hash_mpin(mpin_data.mpin)
    db.commit()
    return {"message": "MPIN set successfully"}


@router.post("/mpin/verify")
async def verify_mpin_route(
    mpin_data: VerifyMPIN,
    current_user: User = Depends(get_current_user)
):
    """Verify MPIN before transaction"""
    if not current_user.mpin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MPIN not set. Please set MPIN first."
        )
    if not verify_mpin(mpin_data.mpin, current_user.mpin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MPIN"
        )
    return {"message": "MPIN verified", "verified": True}


# ── Change Password ───────────────────────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    pwd_data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change account password"""
    if not verify_password(pwd_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.hashed_password = hash_password(pwd_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

# ── OAuth2 Token Endpoint (for Swagger Authorize button) ─────────────────────
# This fixes the 422 error when using Swagger's Authorize popup
# Swagger sends "username" field — this endpoint maps it to "email"

@router.post("/token", include_in_schema=False)
async def oauth2_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request:   Request = None,
    db:        Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint.
    Swagger UI uses 'username' field — we map it to 'email' here.
    This endpoint is hidden from docs (include_in_schema=False).
    """
    from app.schemas.user import UserLogin

    # Map OAuth2 'username' field → our 'email' field
    login_data = UserLogin(
        email    = form_data.username,   # Swagger sends username, we use as email
        password = form_data.password
    )

    # Reuse existing login service
    class FakeRequest:
        client     = type("c", (), {"host": "swagger-ui"})()
        headers    = {"User-Agent": "Swagger UI"}

    token = AuthService.login_user(db, login_data, FakeRequest())

    # OAuth2 requires "access_token" and "token_type" fields
    return {
        "access_token": token.access_token,
        "token_type":   "bearer"
    }