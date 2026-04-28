# backend/app/services/auth_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from datetime import datetime
from uuid import UUID

from app.models.user import User
from app.models.account import Account, AccountType
from app.models.wallet import Wallet
from app.schemas.user import UserRegister, UserLogin, Token
from app.utils.password_handler import hash_password, verify_password, hash_mpin, verify_mpin
from app.utils.jwt_handler import create_access_token, create_refresh_token, verify_token_type
from app.utils.account_generator import generate_account_number, generate_upi_id
import logging

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> dict:
        """
        Register a new user with:
        - Duplicate check (email, phone)
        - Password hashing
        - Auto account creation (Savings)
        - Auto wallet creation
        - Auto UPI ID generation
        """

        # ── Check duplicates ───────────────────────────────────────
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already registered"
            )

        # ── Create User ─────────────────────────────────────────────
        new_user = User(
            full_name       = user_data.full_name,
            email           = user_data.email,
            phone_number    = user_data.phone_number,
            hashed_password = hash_password(user_data.password),
            date_of_birth   = user_data.date_of_birth,
            address         = user_data.address,
            city            = user_data.city,
            state           = user_data.state,
            pincode         = user_data.pincode
        )
        db.add(new_user)
        db.flush()  # Get the user ID without full commit

        # ── Auto Create Savings Account ─────────────────────────────
        savings_account = Account(
            user_id         = new_user.id,
            account_number  = generate_account_number(),
            account_type    = AccountType.SAVINGS,
            balance         = 0.00,
            minimum_balance = 1000.00
        )
        db.add(savings_account)

        # ── Auto Create Wallet ──────────────────────────────────────
        wallet = Wallet(
            user_id = new_user.id,
            balance = 0.00,
            upi_id  = generate_upi_id(user_data.phone_number)
        )
        db.add(wallet)

        db.commit()
        db.refresh(new_user)

        logger.info(f"✅ New user registered: {new_user.email}")

        return {
            "message": "Registration successful",
            "user_id": str(new_user.id),
            "email": new_user.email,
            "account_number": savings_account.account_number,
            "upi_id": wallet.upi_id
        }

    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def login_user(db: Session, login_data: UserLogin, request: Request) -> Token:
        """
        Login with:
        - Account lock check
        - Failed attempt tracking (max 5)
        - Last login tracking
        - JWT access + refresh token generation
        """

        user = db.query(User).filter(User.email == login_data.email).first()

        # Generic error — don't reveal if email exists
        credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

        if not user:
            raise credentials_error

        # Check if account is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed attempts. Contact support."
            )

        # Check if active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.is_locked = True
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account locked after 5 failed attempts"
                )
            db.commit()
            raise credentials_error

        # ── Successful Login ────────────────────────────────────────
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        user.last_login_ip = request.client.host if request.client else "unknown"
        user.last_login_device = request.headers.get("User-Agent", "unknown")[:200]
        db.commit()

        # Generate tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }

        access_token  = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info(f"✅ User logged in: {user.email}")

        return Token(
            access_token  = access_token,
            refresh_token = refresh_token,
            token_type    = "bearer",
            user_id       = user.id,
            full_name     = user.full_name,
            email         = user.email,
            role          = user.role.value
        )

    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Generate new access token using refresh token"""
        payload = verify_token_type(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        new_access_token = create_access_token({
            "sub":   payload["sub"],
            "email": payload["email"],
            "role":  payload["role"]
        })

        return {"access_token": new_access_token, "token_type": "bearer"}