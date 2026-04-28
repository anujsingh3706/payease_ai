# backend/app/models/account.py

from sqlalchemy import (
    Column, String, Numeric, Boolean,
    DateTime, Enum, ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class AccountType(str, enum.Enum):
    SAVINGS  = "savings"
    CURRENT  = "current"
    SALARY   = "salary"


class AccountStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    FROZEN   = "frozen"
    CLOSED   = "closed"


class Account(Base):
    __tablename__ = "accounts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Account Details
    account_number  = Column(String(16), unique=True, nullable=False, index=True)
    account_type    = Column(Enum(AccountType), default=AccountType.SAVINGS)
    account_status  = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE)

    # Financial
    balance         = Column(Numeric(15, 2), default=0.00, nullable=False)
    minimum_balance = Column(Numeric(10, 2), default=1000.00)
    daily_limit     = Column(Numeric(10, 2), default=100000.00)   # ₹1 Lakh default
    interest_rate   = Column(Numeric(5, 2), default=4.00)         # % per annum

    # Branch Info
    branch_name     = Column(String(100), default="Main Branch")
    ifsc_code       = Column(String(11), default="PAYS0001234")
    micr_code       = Column(String(9), nullable=True)

    # Flags
    is_primary      = Column(Boolean, default=True)
    upi_enabled     = Column(Boolean, default=True)

    # Timestamps
    opened_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user            = relationship("User", back_populates="accounts")
    transactions_sent     = relationship(
        "Transaction",
        foreign_keys="Transaction.from_account_id",
        back_populates="from_account"
    )
    transactions_received = relationship(
        "Transaction",
        foreign_keys="Transaction.to_account_id",
        back_populates="to_account"
    )

    def __repr__(self):
        return f"<Account {self.account_number}>"