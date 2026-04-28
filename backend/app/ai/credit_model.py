# backend/app/ai/credit_model.py

"""
CREDIT SCORE PREDICTOR
──────────────────────
Algorithm  : XGBoost Regressor
Output     : Credit Score 300–900 (CIBIL-style)
Explainability: SHAP values — tells user WHY they got this score

Features Used:
  - payment_history_score   : % of on-time payments (0-100)
  - credit_utilization      : % of credit limit used (0-100)
  - account_age_months      : How old the account is
  - num_active_loans        : Number of currently active loans
  - num_missed_payments     : Total missed payments (last 12 months)
  - total_balance           : Current total balance in account
  - monthly_income          : Declared monthly income
  - monthly_expenses        : Monthly expense outflow
  - num_credit_inquiries    : Hard inquiries in last 6 months
  - transaction_frequency   : Avg transactions per month
  - savings_rate            : (income - expenses) / income
  - loan_repayment_ratio    : EMI / income ratio
"""

import numpy  as np
import pandas as pd
import joblib
import os
import shap
from xgboost             import XGBRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline    import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics     import mean_absolute_error, r2_score
import logging

logger     = logging.getLogger(__name__)
MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../ml_models/credit_model.pkl")
)


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC TRAINING DATA
# ─────────────────────────────────────────────────────────────────────────────

def generate_credit_training_data(n: int = 8000) -> pd.DataFrame:
    """
    Generate realistic synthetic credit data.
    Score formula mirrors how CIBIL actually calculates:
    - Payment history    → 35% weight
    - Credit utilization → 30% weight
    - Account age        → 15% weight
    - Credit mix / loans → 10% weight
    - Inquiries          → 10% weight
    """
    np.random.seed(42)

    payment_history     = np.random.uniform(40, 100, n)
    credit_utilization  = np.random.uniform(5,  95,  n)
    account_age_months  = np.random.randint(1,  240, n)
    num_active_loans    = np.random.randint(0,  6,   n)
    num_missed_payments = np.random.randint(0,  12,  n)
    monthly_income      = np.random.uniform(15000, 200000, n)
    monthly_expenses    = monthly_income * np.random.uniform(0.3, 0.9, n)
    total_balance       = np.random.uniform(1000, 2000000, n)
    num_credit_inquiries = np.random.randint(0, 10, n)
    transaction_freq    = np.random.randint(2, 60, n)

    savings_rate        = (monthly_income - monthly_expenses) / monthly_income
    loan_repayment_ratio = np.minimum(
        num_active_loans * 5000 / monthly_income, 1.0
    )

    # Score formula (weighted)
    base_score = (
          payment_history    * 3.50     # 35% weight, max 350
        + (100 - credit_utilization) * 2.70  # 30% weight (lower util = better)
        + np.minimum(account_age_months / 240, 1) * 135  # 15% weight
        + np.maximum(0, 5 - num_active_loans) * 10       # 10% weight
        + np.maximum(0, 6 - num_credit_inquiries) * 10   # 10% weight
    )

    # Penalties
    penalty = (
          num_missed_payments * 15
        + np.maximum(0, credit_utilization - 70) * 2
        + np.maximum(0, loan_repayment_ratio - 0.4) * 50
    )

    # Bonus
    bonus = (
          savings_rate * 30
        + np.minimum(transaction_freq / 60, 1) * 20
    )

    raw_score = base_score - penalty + bonus + np.random.normal(0, 10, n)
    # Clip to CIBIL range 300-900
    credit_score = np.clip(raw_score + 300, 300, 900).astype(int)

    return pd.DataFrame({
        "payment_history_score": payment_history,
        "credit_utilization":    credit_utilization,
        "account_age_months":    account_age_months,
        "num_active_loans":      num_active_loans,
        "num_missed_payments":   num_missed_payments,
        "total_balance":         total_balance,
        "monthly_income":        monthly_income,
        "monthly_expenses":      monthly_expenses,
        "num_credit_inquiries":  num_credit_inquiries,
        "transaction_frequency": transaction_freq,
        "savings_rate":          savings_rate,
        "loan_repayment_ratio":  loan_repayment_ratio,
        "credit_score":          credit_score
    })


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN MODEL
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_COLS = [
    "payment_history_score", "credit_utilization",
    "account_age_months",    "num_active_loans",
    "num_missed_payments",   "total_balance",
    "monthly_income",        "monthly_expenses",
    "num_credit_inquiries",  "transaction_frequency",
    "savings_rate",          "loan_repayment_ratio"
]


def train_credit_model():
    logger.info("🔄 Training Credit Score Model (XGBoost)...")

    df = generate_credit_training_data()
    X  = df[FEATURE_COLS]
    y  = df["credit_score"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators      = 300,
        max_depth         = 6,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        random_state      = 42,
        n_jobs            = -1,
        eval_metric       = "mae"
    )
    model.fit(
        X_train, y_train,
        eval_set            = [(X_test, y_test)],
        verbose             = False
    )

    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    r2    = r2_score(y_test, preds)
    logger.info(f"📊 Credit Model | MAE: {mae:.2f} | R²: {r2:.4f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_cols": FEATURE_COLS}, MODEL_PATH)
    logger.info(f"✅ Credit model saved → {MODEL_PATH}")
    return model


def load_credit_model():
    if not os.path.exists(MODEL_PATH):
        return train_credit_model(), FEATURE_COLS
    saved = joblib.load(MODEL_PATH)
    return saved["model"], saved["feature_cols"]


# ─────────────────────────────────────────────────────────────────────────────
# PREDICT CREDIT SCORE WITH SHAP EXPLANATION
# ─────────────────────────────────────────────────────────────────────────────

_credit_model  = None
_credit_cols   = None


def get_credit_model():
    global _credit_model, _credit_cols
    if _credit_model is None:
        _credit_model, _credit_cols = load_credit_model()
    return _credit_model, _credit_cols


def predict_credit_score(features: dict) -> dict:
    """
    Predict credit score and return SHAP-based explanation.

    Args:
        features: dict with all FEATURE_COLS keys

    Returns:
        score, grade, explanation, improvement_tips
    """
    model, cols = get_credit_model()

    df = pd.DataFrame([features])[cols]

    raw_score  = model.predict(df)[0]
    score      = int(np.clip(raw_score, 300, 900))

    # ── Score Grade ───────────────────────────────────────────────────────────
    if score >= 800:
        grade       = "EXCELLENT"
        color       = "green"
        description = "Outstanding credit profile. Eligible for best loan rates."
    elif score >= 750:
        grade       = "VERY GOOD"
        color       = "lightgreen"
        description = "Strong credit profile. Most loans approved easily."
    elif score >= 700:
        grade       = "GOOD"
        color       = "yellow"
        description = "Decent credit. Most loans approved with standard rates."
    elif score >= 650:
        grade       = "FAIR"
        color       = "orange"
        description = "Average credit. Some loans may be rejected or have higher rates."
    elif score >= 600:
        grade       = "POOR"
        color       = "red"
        description = "Low credit score. Loan approvals difficult."
    else:
        grade       = "VERY POOR"
        color       = "darkred"
        description = "Very low credit score. Work on improving before applying."

    # ── SHAP Explanation ──────────────────────────────────────────────────────
    try:
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(df)
        shap_dict   = dict(zip(cols, shap_values[0]))

        # Top 3 positive factors (boosting score)
        positive = sorted(
            [(k, v) for k, v in shap_dict.items() if v > 0],
            key=lambda x: x[1], reverse=True
        )[:3]

        # Top 3 negative factors (hurting score)
        negative = sorted(
            [(k, v) for k, v in shap_dict.items() if v < 0],
            key=lambda x: x[1]
        )[:3]

    except Exception:
        positive = []
        negative = []

    # ── Human-readable factor names ───────────────────────────────────────────
    factor_labels = {
        "payment_history_score":  "Payment History",
        "credit_utilization":     "Credit Utilization",
        "account_age_months":     "Account Age",
        "num_active_loans":       "Active Loans",
        "num_missed_payments":    "Missed Payments",
        "total_balance":          "Account Balance",
        "monthly_income":         "Monthly Income",
        "monthly_expenses":       "Monthly Expenses",
        "num_credit_inquiries":   "Credit Inquiries",
        "transaction_frequency":  "Transaction Activity",
        "savings_rate":           "Savings Rate",
        "loan_repayment_ratio":   "Loan Repayment Ratio"
    }

    # ── Improvement Tips ──────────────────────────────────────────────────────
    tips = []
    if features.get("num_missed_payments", 0) > 0:
        tips.append("✅ Pay all EMIs and credit card bills on time — this is the #1 factor.")
    if features.get("credit_utilization", 0) > 30:
        tips.append("✅ Keep credit utilization below 30% of your limit.")
    if features.get("num_credit_inquiries", 0) > 3:
        tips.append("✅ Avoid applying for multiple loans/cards in a short period.")
    if features.get("savings_rate", 1) < 0.2:
        tips.append("✅ Increase your savings rate — aim for at least 20% of income.")
    if features.get("account_age_months", 0) < 12:
        tips.append("✅ Keep your oldest account active — account age builds credit history.")
    if not tips:
        tips.append("✅ Keep maintaining your excellent credit habits!")

    return {
        "credit_score": score,
        "grade":        grade,
        "color":        color,
        "description":  description,
        "score_range":  {"min": 300, "max": 900},
        "positive_factors": [
            {
                "factor": factor_labels.get(k, k),
                "impact": round(v, 2)
            }
            for k, v in positive
        ],
        "negative_factors": [
            {
                "factor": factor_labels.get(k, k),
                "impact": round(abs(v), 2)
            }
            for k, v in negative
        ],
        "improvement_tips": tips
    }