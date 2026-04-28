# backend/app/routers/accounts.py

from fastapi  import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing   import List, Optional
from datetime import datetime

from app.database               import get_db
from app.models.user            import User
from app.models.wallet          import Beneficiary
from app.schemas.account        import (
    AccountResponse, WalletResponse,
    BeneficiaryCreate, BeneficiaryResponse,
    TransactionFilter
)
from app.services.account_service import AccountService
from app.utils.dependencies        import get_current_user

router = APIRouter(prefix="/api/v1/accounts", tags=["Accounts & Banking"])


# ── Get All Accounts ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[AccountResponse])
async def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank accounts of the logged-in user"""
    return AccountService.get_user_accounts(db, current_user.id)


# ── Balance Check ─────────────────────────────────────────────────────────────

@router.get("/balance")
async def check_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check account balance"""
    return AccountService.get_balance(db, current_user.id)


# ── Mini Statement (Passbook) ─────────────────────────────────────────────────

@router.get("/statement")
async def mini_statement(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mini statement / passbook view"""
    return AccountService.get_mini_statement(db, current_user.id, limit)


# ── Transaction History ───────────────────────────────────────────────────────

@router.get("/transactions")
async def get_transactions(
    page:              int            = Query(default=1,  ge=1),
    limit:             int            = Query(default=20, ge=1, le=100),
    transaction_type:  Optional[str]  = Query(default=None),
    status:            Optional[str]  = Query(default=None),
    from_date:         Optional[datetime] = Query(default=None),
    to_date:           Optional[datetime] = Query(default=None),
    min_amount:        Optional[float]    = Query(default=None),
    max_amount:        Optional[float]    = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated transaction history with filters"""
    filters = TransactionFilter(
        page=page, limit=limit,
        transaction_type=transaction_type,
        status=status,
        from_date=from_date, to_date=to_date,
        min_amount=min_amount, max_amount=max_amount
    )
    return AccountService.get_transactions(db, current_user.id, filters)


# ── Beneficiary Management ────────────────────────────────────────────────────

@router.get("/beneficiaries", response_model=List[BeneficiaryResponse])
async def get_beneficiaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved beneficiaries"""
    return db.query(Beneficiary).filter(
        Beneficiary.user_id == current_user.id
    ).all()


@router.post("/beneficiaries", response_model=BeneficiaryResponse, status_code=201)
async def add_beneficiary(
    beneficiary_data: BeneficiaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new beneficiary"""
    new_bene = Beneficiary(
        user_id          = current_user.id,
        **beneficiary_data.model_dump()
    )
    db.add(new_bene)
    db.commit()
    db.refresh(new_bene)
    return new_bene


@router.delete("/beneficiaries/{beneficiary_id}")
async def delete_beneficiary(
    beneficiary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a beneficiary"""
    bene = db.query(Beneficiary).filter(
        Beneficiary.id == beneficiary_id,
        Beneficiary.user_id == current_user.id
    ).first()

    if not bene:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    db.delete(bene)
    db.commit()
    return {"message": "Beneficiary removed successfully"}