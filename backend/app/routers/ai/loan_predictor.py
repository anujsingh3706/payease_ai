# backend/app/routers/ai/loan_predictor.py

from fastapi        import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy     import func
from pydantic       import BaseModel, Field
from typing         import Optional
from datetime       import datetime
from decimal        import Decimal
from uuid           import UUID

from app.database            import get_db
from app.models.user         import User
from app.models.loan         import LoanApplication, LoanType, LoanStatus
from app.models.account      import Account
from app.ai.loan_model       import predict_loan_eligibility, calculate_emi, get_interest_rate
from app.utils.dependencies  import get_current_user
from app.utils.account_generator import generate_loan_application_no

router = APIRouter(prefix="/api/v1/ai/loan", tags=["🏠 Loan Predictor"])


# ── Request Schema ────────────────────────────────────────────────────────────

class LoanPredictRequest(BaseModel):
    loan_type:       str   = Field(default="personal")
    loan_amount:     float = Field(..., gt=10000, le=10000000)
    tenure_months:   int   = Field(..., ge=6, le=360)
    monthly_income:  float = Field(..., gt=0)
    existing_emis:   float = Field(default=0.0, ge=0)
    employment_type: str   = Field(default="salaried")
    years_employed:  float = Field(default=2.0, ge=0)
    cibil_score:     int   = Field(default=700, ge=300, le=900)
    employer_name:   Optional[str] = None
    purpose:         Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "loan_type":      "personal",
                "loan_amount":    500000,
                "tenure_months":  48,
                "monthly_income": 75000,
                "existing_emis":  5000,
                "employment_type": "salaried",
                "years_employed":  3.5,
                "cibil_score":    730
            }
        }


class LoanApplicationRequest(LoanPredictRequest):
    """Same as predict but also saves the application"""
    pass


# ── Predict Loan Eligibility ──────────────────────────────────────────────────

@router.post("/predict")
async def predict_loan(
    request: LoanPredictRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Predict loan eligibility using AI (Random Forest + SHAP).

    Returns:
    - Approved / Rejected prediction
    - Confidence percentage
    - EMI amount & interest rate
    - SHAP explanation (why approved/rejected)
    - Specific rejection reasons
    - Improvement suggestions

    Loan Types: personal, home, vehicle, education, business
    """
    result = predict_loan_eligibility(
        monthly_income  = request.monthly_income,
        loan_amount     = request.loan_amount,
        tenure_months   = request.tenure_months,
        existing_emis   = request.existing_emis,
        employment_type = request.employment_type,
        years_employed  = request.years_employed,
        cibil_score     = request.cibil_score,
        loan_type       = request.loan_type
    )
    return result


# ── Apply for Loan (Saves Application) ───────────────────────────────────────

@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_for_loan(
    request: LoanApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply for a loan.
    1. Runs AI eligibility check
    2. Saves application with AI prediction
    3. Returns application number + prediction
    """

    # Run AI prediction
    ai_result = predict_loan_eligibility(
        monthly_income  = request.monthly_income,
        loan_amount     = request.loan_amount,
        tenure_months   = request.tenure_months,
        existing_emis   = request.existing_emis,
        employment_type = request.employment_type,
        years_employed  = request.years_employed,
        cibil_score     = request.cibil_score,
        loan_type       = request.loan_type
    )

    # Map loan type
    loan_type_map = {
        "personal": LoanType.PERSONAL, "home":     LoanType.HOME,
        "vehicle":  LoanType.VEHICLE,  "education": LoanType.EDUCATION,
        "business": LoanType.BUSINESS
    }

    application = LoanApplication(
        user_id          = current_user.id,
        application_no   = generate_loan_application_no(),
        loan_type        = loan_type_map.get(request.loan_type, LoanType.PERSONAL),
        amount_requested = Decimal(str(request.loan_amount)),
        tenure_months    = request.tenure_months,
        purpose          = request.purpose,
        monthly_income   = Decimal(str(request.monthly_income)),
        existing_emis    = Decimal(str(request.existing_emis)),
        employment_type  = request.employment_type,
        employer_name    = request.employer_name,
        years_employed   = Decimal(str(request.years_employed)),
        cibil_score      = request.cibil_score,
        # AI results
        ai_prediction    = ai_result["prediction"],
        ai_confidence    = Decimal(str(ai_result["confidence"] / 100)),
        ai_reasons       = {
            "rejection_reasons": ai_result["rejection_reasons"],
            "approval_factors":  ai_result["approval_factors"]
        },
        # Pre-fill if approved
        loan_status      = LoanStatus.APPLIED,
        interest_rate    = Decimal(str(ai_result["interest_rate"])),
        emi_amount       = Decimal(str(ai_result["emi_amount"]))
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "application_no":  application.application_no,
        "loan_type":       request.loan_type,
        "amount":          request.loan_amount,
        "ai_prediction":   ai_result["prediction"],
        "confidence":      ai_result["confidence"],
        "emi_amount":      ai_result["emi_amount"],
        "interest_rate":   ai_result["interest_rate"],
        "status":          "Application submitted successfully",
        "next_steps": (
            "Our team will review your application within 2-3 business days."
            if not ai_result["is_eligible"] else
            "Congratulations! Your application looks strong. Expect approval within 24 hours."
        ),
        **{k: v for k, v in ai_result.items()
           if k in ["rejection_reasons", "approval_factors", "recommendation"]}
    }


# ── Get My Loan Applications ──────────────────────────────────────────────────

@router.get("/applications")
async def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all loan applications for the current user"""
    apps = db.query(LoanApplication).filter(
        LoanApplication.user_id == current_user.id
    ).order_by(LoanApplication.applied_at.desc()).all()

    return {
        "total": len(apps),
        "applications": [
            {
                "application_no":  a.application_no,
                "loan_type":       a.loan_type.value,
                "amount":          float(a.amount_requested),
                "tenure_months":   a.tenure_months,
                "status":          a.loan_status.value,
                "ai_prediction":   a.ai_prediction,
                "ai_confidence":   float(a.ai_confidence) * 100 if a.ai_confidence else None,
                "emi_amount":      float(a.emi_amount) if a.emi_amount else None,
                "interest_rate":   float(a.interest_rate) if a.interest_rate else None,
                "applied_at":      a.applied_at.isoformat()
            }
            for a in apps
        ]
    }


# ── EMI Calculator (Public) ───────────────────────────────────────────────────

@router.get("/emi-calculator")
async def emi_calculator(
    principal:      float = 500000,
    rate_annual:    float = 12.0,
    tenure_months:  int   = 48
):
    """
    Pure EMI calculator — no auth required.
    Formula: EMI = P × r × (1+r)^n / ((1+r)^n - 1)
    """
    emi            = calculate_emi(principal, rate_annual, tenure_months)
    total_payment  = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "principal":       principal,
        "rate_annual":     rate_annual,
        "tenure_months":   tenure_months,
        "emi_amount":      round(emi, 2),
        "total_payment":   round(total_payment, 2),
        "total_interest":  round(total_interest, 2),
        "interest_percent": round((total_interest / principal) * 100, 1),
        "formula":         "EMI = P × r × (1+r)^n / ((1+r)^n - 1)"
    }