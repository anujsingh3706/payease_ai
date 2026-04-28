# backend/app/schemas/user.py

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


# ── Registration ─────────────────────────────────────────────

class UserRegister(BaseModel):
    full_name:    str       = Field(..., min_length=3, max_length=100)
    email:        EmailStr
    phone_number: str       = Field(..., min_length=10, max_length=15)
    password:     str       = Field(..., min_length=8, max_length=50)
    date_of_birth: Optional[datetime] = None
    address:      Optional[str] = None
    city:         Optional[str] = None
    state:        Optional[str] = None
    pincode:      Optional[str] = None

    @validator("phone_number")
    def validate_phone(cls, v):
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Enter valid Indian mobile number (10 digits starting with 6-9)")
        return v

    @validator("password")
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must have at least 1 uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must have at least 1 lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must have at least 1 digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must have at least 1 special character")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Rahul Sharma",
                "email": "rahul@example.com",
                "phone_number": "9876543210",
                "password": "Rahul@1234",
                "city": "Mumbai",
                "state": "Maharashtra"
            }
        }


# ── Login ────────────────────────────────────────────────────

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "rahul@example.com",
                "password": "Rahul@1234"
            }
        }


# ── Token Response ───────────────────────────────────────────

class Token(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user_id:       UUID
    full_name:     str
    email:         str
    role:          str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email:   Optional[str] = None
    role:    Optional[str] = None


# ── Profile Response ─────────────────────────────────────────

class UserProfile(BaseModel):
    id:           UUID
    full_name:    str
    email:        str
    phone_number: str
    city:         Optional[str]
    state:        Optional[str]
    kyc_status:   str
    is_active:    bool
    is_verified:  bool
    created_at:   datetime

    class Config:
        from_attributes = True


# ── Update Profile ───────────────────────────────────────────

class UserUpdate(BaseModel):
    full_name:      Optional[str] = None
    address:        Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    pincode:        Optional[str] = None
    date_of_birth:  Optional[datetime] = None


# ── KYC Update ───────────────────────────────────────────────

class KYCUpdate(BaseModel):
    aadhaar_number: str = Field(..., min_length=12, max_length=12)
    pan_number:     str = Field(..., min_length=10, max_length=10)

    @validator("aadhaar_number")
    def validate_aadhaar(cls, v):
        if not v.isdigit():
            raise ValueError("Aadhaar must be 12 digits")
        return v

    @validator("pan_number")
    def validate_pan(cls, v):
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.upper()):
            raise ValueError("Invalid PAN format (e.g. ABCDE1234F)")
        return v.upper()


# ── MPIN ─────────────────────────────────────────────────────

class SetMPIN(BaseModel):
    mpin: str = Field(..., min_length=6, max_length=6)

    @validator("mpin")
    def validate_mpin(cls, v):
        if not v.isdigit():
            raise ValueError("MPIN must be 6 digits")
        return v


class VerifyMPIN(BaseModel):
    mpin: str = Field(..., min_length=6, max_length=6)


# ── Password Change ──────────────────────────────────────────

class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v