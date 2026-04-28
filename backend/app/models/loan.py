# backend/app/models/loan.py

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


class LoanType(str, enum.Enum):
    PERSONAL    = "personal"
    HOME        = "home"
    VEHICLE     = "vehicle"
    EDUCATION   = "education"
    BUSINESS    = "business"


class LoanStatus(str, enum.Enum):
    APPLIED     = "applied"
    PROCESSING  = "processing"
    APPROVED    = "approved"
    REJECTED    = "rejected"
    DISBURSED   = "disbursed"
    CLOSED      = "closed"


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    application_no  = Column(String(20), unique=True, nullable=False)

    loan_type       = Column(Enum(LoanType), nullable=False)
    amount_requested = Column(Numeric(12, 2), nullable=False)
    tenure_months   = Column(Integer, nullable=False)
    purpose         = Column(Text, nullable=True)

    # Applicant Financial Info
    monthly_income  = Column(Numeric(10, 2), nullable=False)
    existing_emis   = Column(Numeric(10, 2), default=0.00)
    employment_type = Column(String(50))      # Salaried, Self-employed, Business
    employer_name   = Column(String(100), nullable=True)
    years_employed  = Column(Numeric(4, 1), default=0.0)
    cibil_score     = Column(Integer, nullable=True)

    # AI Prediction Result
    ai_prediction   = Column(String(20), nullable=True)    # approved / rejected
    ai_confidence   = Column(Numeric(5, 4), nullable=True) # 0.0 to 1.0
    ai_reasons      = Column(JSONB, nullable=True)          # SHAP explanations

    # Bank Decision
    loan_status     = Column(Enum(LoanStatus), default=LoanStatus.APPLIED)
    interest_rate   = Column(Numeric(5, 2), nullable=True)
    approved_amount = Column(Numeric(12, 2), nullable=True)
    emi_amount      = Column(Numeric(10, 2), nullable=True)

    applied_at      = Column(DateTime(timezone=True), server_default=func.now())
    decision_at     = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="loan_applications")