# backend/app/schemas/transaction.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class MiniStatement(BaseModel):
    """Last N transactions — passbook view"""
    transactions:   List[dict]
    total_credit:   Decimal
    total_debit:    Decimal
    opening_balance: Decimal
    closing_balance: Decimal


class SpendSummary(BaseModel):
    """Monthly spend summary by category"""
    month:      str
    year:       int
    categories: dict        # {"food": 2500, "travel": 1200, ...}
    total_spent: Decimal
    total_received: Decimal


class DashboardStats(BaseModel):
    """User dashboard overview"""
    account_balance: Decimal
    wallet_balance:  Decimal
    this_month_spent: Decimal
    this_month_received: Decimal
    total_transactions: int
    pending_transactions: int
    flagged_transactions: int
    recent_transactions: List[dict]
    credit_score:       Optional[int]
    upi_id:             Optional[str]