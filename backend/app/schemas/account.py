# backend/app/schemas/account.py

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
import re


# ── Account Response ──────────────────────────────────────────────────────────

class AccountResponse(BaseModel):
    id:              UUID
    account_number:  str
    account_type:    str
    account_status:  str
    balance:         Decimal
    minimum_balance: Decimal
    daily_limit:     Decimal
    interest_rate:   Decimal
    branch_name:     str
    ifsc_code:       str
    is_primary:      bool
    upi_enabled:     bool
    opened_at:       datetime

    class Config:
        from_attributes = True


# ── Wallet Response ───────────────────────────────────────────────────────────

class WalletResponse(BaseModel):
    id:             UUID
    balance:        Decimal
    daily_limit:    Decimal
    monthly_limit:  Decimal
    today_spent:    Decimal
    month_spent:    Decimal
    is_active:      bool
    upi_id:         Optional[str]

    class Config:
        from_attributes = True


# ── Fund Transfer ─────────────────────────────────────────────────────────────

class FundTransferRequest(BaseModel):
    to_account_number: str     = Field(..., min_length=14, max_length=16)
    amount:            Decimal = Field(..., gt=0, le=1000000)
    mpin:              str     = Field(..., min_length=6, max_length=6)
    description:       Optional[str] = Field(None, max_length=255)
    transfer_mode:     str     = Field(default="imps")   # neft, rtgs, imps

    @validator("to_account_number")
    def validate_account(cls, v):
        if not v.isdigit():
            raise ValueError("Account number must be digits only")
        return v

    @validator("mpin")
    def validate_mpin(cls, v):
        if not v.isdigit():
            raise ValueError("MPIN must be 6 digits")
        return v

    @validator("transfer_mode")
    def validate_mode(cls, v):
        allowed = ["neft", "rtgs", "imps", "upi"]
        if v.lower() not in allowed:
            raise ValueError(f"Mode must be one of {allowed}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "to_account_number": "2024123456789",
                "amount": 5000.00,
                "mpin": "123456",
                "description": "Rent payment",
                "transfer_mode": "imps"
            }
        }


# ── UPI Transfer ──────────────────────────────────────────────────────────────

class UPITransferRequest(BaseModel):
    to_upi_id: str     = Field(..., min_length=5, max_length=100)
    amount:    Decimal = Field(..., gt=0, le=100000)
    mpin:      str     = Field(..., min_length=6, max_length=6)
    note:      Optional[str] = Field(None, max_length=100)

    @validator("to_upi_id")
    def validate_upi(cls, v):
        if "@" not in v:
            raise ValueError("Invalid UPI ID format (should contain @)")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "to_upi_id": "9876543210@payease",
                "amount": 500.00,
                "mpin": "123456",
                "note": "Dinner split"
            }
        }


# ── Wallet TopUp ──────────────────────────────────────────────────────────────

class WalletTopUpRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, le=10000)

    class Config:
        json_schema_extra = {"example": {"amount": 1000.00}}


# ── Wallet Transfer ───────────────────────────────────────────────────────────

class WalletTransferRequest(BaseModel):
    to_upi_id: str     = Field(..., min_length=5)
    amount:    Decimal = Field(..., gt=0, le=10000)
    mpin:      str     = Field(..., min_length=6, max_length=6)
    note:      Optional[str] = None

    @validator("mpin")
    def validate_mpin(cls, v):
        if not v.isdigit():
            raise ValueError("MPIN must be 6 digits")
        return v


# ── Transaction Response ──────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    id:                  UUID
    transaction_ref:     str
    amount:              Decimal
    net_amount:          Decimal
    charges:             Decimal
    transaction_type:    str
    transaction_mode:    Optional[str]
    transaction_status:  str
    description:         Optional[str]
    category:            Optional[str]
    is_flagged:          bool
    fraud_score:         Optional[Decimal]
    initiated_at:        datetime
    completed_at:        Optional[datetime]
    to_account_number:   Optional[str]
    to_upi_id:           Optional[str]

    class Config:
        from_attributes = True


# ── Transaction Filter ────────────────────────────────────────────────────────

class TransactionFilter(BaseModel):
    page:          int     = Field(default=1, ge=1)
    limit:         int     = Field(default=20, ge=1, le=100)
    transaction_type: Optional[str] = None
    status:        Optional[str]    = None
    from_date:     Optional[datetime] = None
    to_date:       Optional[datetime] = None
    min_amount:    Optional[Decimal]  = None
    max_amount:    Optional[Decimal]  = None


# ── Beneficiary ───────────────────────────────────────────────────────────────

class BeneficiaryCreate(BaseModel):
    nickname:         str = Field(..., min_length=2, max_length=50)
    beneficiary_name: str = Field(..., min_length=3, max_length=100)
    account_number:   Optional[str] = None
    ifsc_code:        Optional[str] = None
    bank_name:        Optional[str] = None
    upi_id:           Optional[str] = None
    phone_number:     Optional[str] = None

    @validator("ifsc_code")
    def validate_ifsc(cls, v):
        if v and not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v.upper()):
            raise ValueError("Invalid IFSC code format")
        return v.upper() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "Mom",
                "beneficiary_name": "Sunita Sharma",
                "account_number": "2024987654321",
                "ifsc_code": "SBIN0001234",
                "bank_name": "State Bank of India"
            }
        }


class BeneficiaryResponse(BaseModel):
    id:               UUID
    nickname:         str
    beneficiary_name: str
    account_number:   Optional[str]
    ifsc_code:        Optional[str]
    bank_name:        Optional[str]
    upi_id:           Optional[str]
    phone_number:     Optional[str]
    is_verified:      bool
    added_at:         datetime

    class Config:
        from_attributes = True


# ── Razorpay ──────────────────────────────────────────────────────────────────

class RazorpayOrderCreate(BaseModel):
    amount:  Decimal = Field(..., gt=0, le=500000)
    purpose: str     = Field(default="wallet_topup")

    class Config:
        json_schema_extra = {"example": {"amount": 1000.00, "purpose": "wallet_topup"}}


class RazorpayPaymentVerify(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str

    class Config:
        json_schema_extra = {
            "example": {
                "razorpay_order_id":   "order_xxxx",
                "razorpay_payment_id": "pay_xxxx",
                "razorpay_signature":  "signature_string"
            }
        }