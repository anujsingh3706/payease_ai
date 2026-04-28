# backend/app/models/user.py

from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Enum, Integer, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPPORT = "support"


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Personal Info
    full_name       = Column(String(100), nullable=False)
    email           = Column(String(150), unique=True, nullable=False, index=True)
    phone_number    = Column(String(15), unique=True, nullable=False, index=True)
    date_of_birth   = Column(DateTime, nullable=True)
    address         = Column(Text, nullable=True)
    city            = Column(String(50), nullable=True)
    state           = Column(String(50), nullable=True)
    pincode         = Column(String(10), nullable=True)

    # KYC Documents (store reference numbers only)
    aadhaar_number  = Column(String(12), unique=True, nullable=True)
    pan_number      = Column(String(10), unique=True, nullable=True)
    kyc_status      = Column(Enum(KYCStatus), default=KYCStatus.PENDING)

    # Auth
    hashed_password = Column(String(255), nullable=False)
    mpin_hash       = Column(String(255), nullable=True)   # 6-digit MPIN for transactions
    role            = Column(Enum(UserRole), default=UserRole.CUSTOMER)

    # Status Flags
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)       # Email verified
    is_locked       = Column(Boolean, default=False)       # Account locked
    failed_login_attempts = Column(Integer, default=0)

    # Security Tracking
    last_login      = Column(DateTime, nullable=True)
    last_login_ip   = Column(String(45), nullable=True)
    last_login_device = Column(String(200), nullable=True)

    # Timestamps
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    accounts        = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    wallet          = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions    = relationship("Transaction", back_populates="user")
    beneficiaries   = relationship("Beneficiary", back_populates="user", cascade="all, delete-orphan")
    loan_applications = relationship("LoanApplication", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"