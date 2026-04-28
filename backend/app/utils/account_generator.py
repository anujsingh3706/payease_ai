# backend/app/utils/account_generator.py

import random
import string
from datetime import datetime


def generate_account_number() -> str:
    """
    Generate a unique 16-digit account number
    Format: PAYS + YEAR(4) + RANDOM(8)
    Example: 2024 + 12345678 = 202412345678 → padded to 16
    """
    year    = str(datetime.now().year)
    random_part = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    return f"{year}{random_part}"


def generate_transaction_ref() -> str:
    """
    Generate unique transaction reference
    Format: TXN + TIMESTAMP + RANDOM(4)
    Example: TXN202412151430001234
    """
    timestamp   = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"TXN{timestamp}{random_part}"


def generate_upi_id(phone_number: str) -> str:
    """
    Generate UPI ID for user
    Format: phone@payease
    Example: 9876543210@payease
    """
    return f"{phone_number}@payease"


def generate_loan_application_no() -> str:
    """
    Generate loan application number
    Format: LOAN + YEAR + RANDOM(6)
    """
    year = str(datetime.now().year)
    random_part = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"LOAN{year}{random_part}"