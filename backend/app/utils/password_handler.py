# backend/app/utils/password_handler.py

from passlib.context import CryptContext

# Use bcrypt for password hashing — industry standard
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_mpin(mpin: str) -> str:
    """Hash a 6-digit MPIN"""
    return pwd_context.hash(mpin)


def verify_mpin(plain_mpin: str, hashed_mpin: str) -> bool:
    """Verify MPIN"""
    return pwd_context.verify(plain_mpin, hashed_mpin)