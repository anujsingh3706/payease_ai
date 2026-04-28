# backend/app/ai/loan_model.py

"""
LOAN ELIGIBILITY PREDICTOR
──────────────────────────
Algorithm     : Random Forest Classifier
Explainability: SHAP values (why approved/rejected)
Output        : eligible (bool) + confidence + reasons + EMI

Features:
  - monthly_income      : Applicant's monthly income
  - loan_amount         : Requested loan amount
  - tenure_months       : Loan tenure in months
  - existing_emis       : Current monthly EMI obligations
  - employment_type_enc : 0=Salaried, 1=Self-Employed, 2=Business
  - years_employed      : Years in current employment
  - cibil_score         : Credit score (300-900)
  - loan_to_income_ratio: loan_amount / (monthly_income * 12)
  - emi_to_income_ratio : (proposed_emi + existing_emis) / income
  - debt_to_income      : total_debt / annual_income
"""

import numpy  as np
import pandas as pd
import joblib
import os
from sklearn.ensemble       import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics        import classification_report, accuracy_score
import shap
import logging

logger     = logging.getLogger(__name__)
MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../ml_models/loan_model.pkl")
)

FEATURE_COLS = [
    "monthly_income", "loan_amount", "tenure_months",
    "existing_emis",  "employment_type_enc", "years_employed",
    "cibil_score",    "loan_to_income_ratio",
    "emi_to_income_ratio", "debt_to_income"
]

EMPLOYMENT_MAP = {"salaried": 0, "self-employed": 1, "business": 2, "other": 3}


# ── EMI Calculator ─────────────────────────────────────────────────────────────

def calculate_emi(principal: float, rate_annual: float, tenure_months: int) -> float:
    """
    EMI = P × r × (1+r)^n / ((1+r)^n - 1)
    where r = monthly interest rate, n = tenure in months
    """
    if tenure_months <= 0:
        return 0.0
    r = rate_annual / (12 * 100)
    if r == 0:
        return principal / tenure_months
    emi = principal * r * (1 + r)**tenure_months / ((1 + r)**tenure_months - 1)
    return round(emi, 2)


def get_interest_rate(loan_type: str, cibil_score: int) -> float:
    """Return applicable interest rate based on loan type and CIBIL score"""
    base_rates = {
        "personal": 12.0, "home": 8.5, "vehicle": 9.5,
        "education": 8.0, "business": 13.5
    }
    base = base_rates.get(loan_type, 12.0)
    # Better CIBIL = lower rate
    if cibil_score >= 800:  reduction = 2.0
    elif cibil_score >= 750: reduction = 1.5
    elif cibil_score >= 700: reduction = 1.0
    elif cibil_score >= 650: reduction = 0.5
    else:                    reduction = 0.0
    return max(7.0, base - reduction)


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING DATA
# ─────────────────────────────────────────────────────────────────────────────

def generate_loan_training_data(n: int = 10000) -> pd.DataFrame:
    np.random.seed(42)

    monthly_income   = np.random.uniform(15000, 300000, n)
    loan_amount      = np.random.uniform(50000, 5000000, n)
    tenure_months    = np.random.choice([12, 24, 36, 48, 60, 84, 120, 180, 240], n)
    existing_emis    = np.random.uniform(0, monthly_income * 0.4, n)
    employment_type  = np.random.randint(0, 4, n)
    years_employed   = np.random.uniform(0, 30, n)
    cibil_score      = np.random.randint(300, 900, n)

    # Derived features
    annual_income         = monthly_income * 12
    loan_to_income_ratio  = loan_amount / annual_income
    interest_rate         = 12.0
    r                     = interest_rate / (12 * 100)
    emi                   = loan_amount * r * (1+r)**tenure_months / ((1+r)**tenure_months - 1)
    emi_to_income_ratio   = (emi + existing_emis) / monthly_income
    debt_to_income        = (existing_emis * 12) / annual_income

    # Approval logic
    approved = (
        (cibil_score >= 650)                 &
        (emi_to_income_ratio <= 0.55)        &
        (loan_to_income_ratio <= 6)          &
        (years_employed >= 1)                &
        (monthly_income >= 20000)
    ).astype(int)

    # Add noise
    noise_mask = np.random.random(n) < 0.05
    approved[noise_mask] = 1 - approved[noise_mask]

    return pd.DataFrame({
        "monthly_income":       monthly_income,
        "loan_amount":          loan_amount,
        "tenure_months":        tenure_months,
        "existing_emis":        existing_emis,
        "employment_type_enc":  employment_type,
        "years_employed":       years_employed,
        "cibil_score":          cibil_score,
        "loan_to_income_ratio": loan_to_income_ratio,
        "emi_to_income_ratio":  emi_to_income_ratio,
        "debt_to_income":       debt_to_income,
        "approved":             approved
    })


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN & SAVE
# ─────────────────────────────────────────────────────────────────────────────

def train_loan_model():
    logger.info("🔄 Training Loan Eligibility Model (Random Forest)...")

    df = generate_loan_training_data()
    X  = df[FEATURE_COLS]
    y  = df["approved"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators  = 200,
        max_depth     = 10,
        min_samples_split = 5,
        class_weight  = "balanced",
        random_state  = 42,
        n_jobs        = -1
    )
    model.fit(X_train, y_train)

    preds  = model.predict(X_test)
    acc    = accuracy_score(y_test, preds)
    logger.info(f"📊 Loan Model Accuracy: {acc:.4f}")
    logger.info("\n" + classification_report(y_test, preds, target_names=["Rejected", "Approved"]))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_cols": FEATURE_COLS}, MODEL_PATH)
    logger.info(f"✅ Loan model saved → {MODEL_PATH}")
    return model


def load_loan_model():
    if not os.path.exists(MODEL_PATH):
        return train_loan_model(), FEATURE_COLS
    saved = joblib.load(MODEL_PATH)
    return saved["model"], saved["feature_cols"]


_loan_model = None
_loan_cols  = None


def get_loan_model():
    global _loan_model, _loan_cols
    if _loan_model is None:
        _loan_model, _loan_cols = load_loan_model()
    return _loan_model, _loan_cols


# ─────────────────────────────────────────────────────────────────────────────
# PREDICT LOAN ELIGIBILITY
# ─────────────────────────────────────────────────────────────────────────────

def predict_loan_eligibility(
    monthly_income:   float,
    loan_amount:      float,
    tenure_months:    int,
    existing_emis:    float,
    employment_type:  str,
    years_employed:   float,
    cibil_score:      int,
    loan_type:        str = "personal"
) -> dict:
    """
    Predict if applicant is eligible for a loan.
    Returns prediction + SHAP explanation + EMI details.
    """
    model, cols = get_loan_model()

    interest_rate        = get_interest_rate(loan_type, cibil_score)
    emi                  = calculate_emi(loan_amount, interest_rate, tenure_months)
    annual_income        = monthly_income * 12
    loan_to_income_ratio = loan_amount / max(annual_income, 1)
    emi_to_income_ratio  = (emi + existing_emis) / max(monthly_income, 1)
    debt_to_income       = (existing_emis * 12) / max(annual_income, 1)
    emp_encoded          = EMPLOYMENT_MAP.get(employment_type.lower(), 3)

    features = pd.DataFrame([{
        "monthly_income":       monthly_income,
        "loan_amount":          loan_amount,
        "tenure_months":        tenure_months,
        "existing_emis":        existing_emis,
        "employment_type_enc":  emp_encoded,
        "years_employed":       years_employed,
        "cibil_score":          cibil_score,
        "loan_to_income_ratio": loan_to_income_ratio,
        "emi_to_income_ratio":  emi_to_income_ratio,
        "debt_to_income":       debt_to_income
    }])

    prediction   = model.predict(features)[0]
    proba        = model.predict_proba(features)[0]
    confidence   = float(proba[prediction])
    is_eligible  = bool(prediction == 1)

    # ── SHAP Explanation ──────────────────────────────────────────────────────
    rejection_reasons  = []
    approval_factors   = []

    try:
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(features)
        # For binary: shap_values[1] = contribution toward "approved"
        sv = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
        shap_dict = dict(zip(cols, sv))

        factor_labels = {
            "cibil_score":          "Credit Score (CIBIL)",
            "emi_to_income_ratio":  "EMI-to-Income Ratio",
            "loan_to_income_ratio": "Loan-to-Income Ratio",
            "monthly_income":       "Monthly Income",
            "years_employed":       "Employment Stability",
            "existing_emis":        "Existing Loan Obligations",
            "employment_type_enc":  "Employment Type",
            "tenure_months":        "Loan Tenure",
            "debt_to_income":       "Debt-to-Income Ratio",
            "loan_amount":          "Requested Loan Amount"
        }

        for k, v in sorted(shap_dict.items(), key=lambda x: x[1]):
            label = factor_labels.get(k, k)
            if v < -0.05:
                rejection_reasons.append({"factor": label, "impact": round(abs(v), 3)})
            elif v > 0.05:
                approval_factors.append({"factor": label, "impact": round(v, 3)})

    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")

    # ── Rule-based rejection reasons (clear language) ─────────────────────────
    plain_reasons = []
    if cibil_score < 650:
        plain_reasons.append(f"Credit score {cibil_score} is below minimum required (650)")
    if emi_to_income_ratio > 0.55:
        plain_reasons.append(
            f"Total EMI burden ({emi_to_income_ratio*100:.1f}% of income) exceeds 55% limit"
        )
    if loan_to_income_ratio > 6:
        plain_reasons.append(
            f"Loan amount is {loan_to_income_ratio:.1f}x annual income (max 6x allowed)"
        )
    if years_employed < 1:
        plain_reasons.append("Minimum 1 year of employment history required")
    if monthly_income < 20000:
        plain_reasons.append(f"Minimum income ₹20,000/month required (yours: ₹{monthly_income:,.0f})")

    # ── Total interest payable ────────────────────────────────────────────────
    total_payment  = emi * tenure_months
    total_interest = total_payment - loan_amount

    return {
        "is_eligible":          is_eligible,
        "prediction":           "APPROVED" if is_eligible else "REJECTED",
        "confidence":           round(confidence * 100, 1),
        "interest_rate":        interest_rate,
        "emi_amount":           round(emi, 2),
        "total_payment":        round(total_payment, 2),
        "total_interest":       round(total_interest, 2),
        "loan_to_income_ratio": round(loan_to_income_ratio, 2),
        "emi_to_income_ratio":  round(emi_to_income_ratio * 100, 1),
        "rejection_reasons":    plain_reasons,
        "approval_factors":     approval_factors[:3],
        "shap_rejection_reasons": rejection_reasons[:3],
        "recommendation": (
            "You are eligible! Apply now to get the best rates."
            if is_eligible else
            "Work on the above factors to improve your eligibility."
        )
    }