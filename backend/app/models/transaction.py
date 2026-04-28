# backend/app/models/transaction.py

from sqlalchemy import (
    Column, String, Numeric, DateTime,
    Enum, ForeignKey, Boolean, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class TransactionType(str, enum.Enum):
    CREDIT         = "credit"
    DEBIT          = "debit"
    TRANSFER       = "transfer"
    WALLET_TOPUP   = "wallet_topup"
    WALLET_WITHDRAW = "wallet_withdraw"
    PAYMENT        = "payment"
    REFUND         = "refund"


class TransactionStatus(str, enum.Enum):
    PENDING    = "pending"
    SUCCESS    = "success"
    FAILED     = "failed"
    REVERSED   = "reversed"
    FLAGGED    = "flagged"          # Flagged by fraud detection


class TransactionMode(str, enum.Enum):
    NEFT  = "neft"
    RTGS  = "rtgs"
    IMPS  = "imps"
    UPI   = "upi"
    WALLET = "wallet"
    CARD  = "card"


class Transaction(Base):
    __tablename__ = "transactions"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_ref     = Column(String(20), unique=True, nullable=False, index=True)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Account Info
    from_account_id     = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    to_account_id       = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    to_account_number   = Column(String(16), nullable=True)
    to_upi_id           = Column(String(100), nullable=True)

    # Amount Info
    amount              = Column(Numeric(15, 2), nullable=False)
    charges             = Column(Numeric(8, 2), default=0.00)
    net_amount          = Column(Numeric(15, 2), nullable=False)

    # Transaction Details
    transaction_type    = Column(Enum(TransactionType), nullable=False)
    transaction_mode    = Column(Enum(TransactionMode), nullable=True)
    transaction_status  = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    description         = Column(String(255), nullable=True)
    category            = Column(String(50), nullable=True)      # Auto-categorised by AI

    # Razorpay Integration
    razorpay_order_id   = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)

    # Fraud Detection
    is_flagged          = Column(Boolean, default=False)
    fraud_score         = Column(Numeric(5, 4), default=0.0)    # 0 to 1
    fraud_reason        = Column(String(255), nullable=True)

    # Metadata (store device, IP etc.)
    transaction_metadata            = Column(JSONB, nullable=True)

    # Timestamps
    initiated_at        = Column(DateTime(timezone=True), server_default=func.now())
    completed_at        = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user            = relationship("User", back_populates="transactions")
    from_account    = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_sent")
    to_account      = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_received")

    def __repr__(self):
        return f"<Transaction {self.transaction_ref} ₹{self.amount}>"