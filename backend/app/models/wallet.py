# backend/app/models/wallet.py

from sqlalchemy import Column, Numeric, Boolean, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Wallet(Base):
    __tablename__ = "wallets"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    balance         = Column(Numeric(10, 2), default=0.00)
    daily_limit     = Column(Numeric(8, 2), default=10000.00)    # ₹10,000 per day
    monthly_limit   = Column(Numeric(10, 2), default=100000.00)  # ₹1 Lakh per month
    today_spent     = Column(Numeric(10, 2), default=0.00)
    month_spent     = Column(Numeric(10, 2), default=0.00)

    is_active       = Column(Boolean, default=True)
    is_blocked      = Column(Boolean, default=False)

    upi_id          = Column(String(100), unique=True, nullable=True)  # e.g., user@payease

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="wallet")


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    nickname        = Column(String(50), nullable=False)
    account_number  = Column(String(16), nullable=True)
    ifsc_code       = Column(String(11), nullable=True)
    bank_name       = Column(String(100), nullable=True)
    upi_id          = Column(String(100), nullable=True)
    phone_number    = Column(String(15), nullable=True)
    beneficiary_name = Column(String(100), nullable=False)

    is_verified     = Column(Boolean, default=False)
    added_at        = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="beneficiaries")