# backend/app/ai/fraud_model.py

"""
FRAUD DETECTION MODEL
─────────────────────
Algorithm: Isolation Forest (Unsupervised Anomaly Detection)
Why Isolation Forest?
  - Perfect for fraud — fraudulent transactions are RARE (anomalies)
  - No labeled data needed to start
  - Works well on tabular transaction data
  - Industry standard for real-time fraud scoring

Features Used:
  - amount                : Transaction amount
  - hour_of_day           : Hour when transaction happened (0-23)
  - day_of_week           : Day (0=Monday, 6=Sunday)
  - is_weekend            : 1 if weekend, 0 if weekday
  - amount_zscore         : How unusual the amount is vs user's history
  - txn_frequency_1hr     : How many txns in last 1 hour
  - is_new_beneficiary    : First time sending to this account
  - amount_to_balance_ratio : Amount as % of total balance
  - is_odd_hour           : 1 if between 1AM-5AM
  - transfer_mode_encoded : Encoded transfer mode

Output:
  - fraud_score: 0.0 (safe) to 1.0 (highly suspicious)
  - is_fraud: True/False
  - risk_level: LOW / MEDIUM / HIGH / CRITICAL
"""

import numpy as np
import pandas as pd
import joblib
import os
from sklearn.ensemble        import IsolationForest
from sklearn.preprocessing   import StandardScaler
from sklearn.pipeline        import Pipeline
from datetime                import datetime
from decimal                 import Decimal
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "../../ml_models/fraud_model.pkl"
)
MODEL_PATH = os.path.abspath(MODEL_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE SYNTHETIC TRAINING DATA
# ─────────────────────────────────────────────────────────────────────────────

def generate_training_data(n_normal: int = 5000, n_fraud: int = 200) -> pd.DataFrame:
    """
    Generate synthetic transaction data for training.
    In production, this is replaced with real transaction history.

    Normal transactions:
    - Reasonable amounts (₹100 - ₹50,000)
    - Business hours (9AM-9PM)
    - Normal frequency

    Fraudulent transactions:
    - Very high amounts
    - Odd hours (1AM-4AM)
    - High frequency (many in short time)
    - New beneficiaries
    """
    np.random.seed(42)

    # ── Normal Transactions ───────────────────────────────────────────────────
    normal = pd.DataFrame({
        "amount":                np.random.lognormal(mean=8, sigma=1.5, size=n_normal),
        "hour_of_day":           np.random.choice(range(8, 22), size=n_normal),
        "day_of_week":           np.random.randint(0, 7, size=n_normal),
        "is_weekend":            np.random.choice([0, 1], size=n_normal, p=[0.7, 0.3]),
        "amount_zscore":         np.random.normal(0, 1, size=n_normal),
        "txn_frequency_1hr":     np.random.poisson(lam=1, size=n_normal),
        "is_new_beneficiary":    np.random.choice([0, 1], size=n_normal, p=[0.85, 0.15]),
        "amount_to_balance_ratio": np.random.uniform(0.01, 0.3, size=n_normal),
        "is_odd_hour":           np.zeros(n_normal),
        "transfer_mode_encoded": np.random.randint(0, 4, size=n_normal),
        "label":                 np.zeros(n_normal)   # 0 = normal
    })

    # ── Fraudulent Transactions ───────────────────────────────────────────────
    fraud = pd.DataFrame({
        "amount":                np.random.lognormal(mean=11, sigma=1, size=n_fraud),
        "hour_of_day":           np.random.choice(range(1, 5), size=n_fraud),
        "day_of_week":           np.random.randint(0, 7, size=n_fraud),
        "is_weekend":            np.random.choice([0, 1], size=n_fraud, p=[0.4, 0.6]),
        "amount_zscore":         np.random.normal(3, 1.5, size=n_fraud),
        "txn_frequency_1hr":     np.random.poisson(lam=8, size=n_fraud),
        "is_new_beneficiary":    np.random.choice([0, 1], size=n_fraud, p=[0.2, 0.8]),
        "amount_to_balance_ratio": np.random.uniform(0.5, 1.0, size=n_fraud),
        "is_odd_hour":           np.ones(n_fraud),
        "transfer_mode_encoded": np.random.randint(0, 4, size=n_fraud),
        "label":                 np.ones(n_fraud)    # 1 = fraud
    })

    df = pd.concat([normal, fraud], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN & SAVE MODEL
# ─────────────────────────────────────────────────────────────────────────────

def train_fraud_model():
    """
    Train Isolation Forest model and save to disk.
    Run this ONCE when setting up the project.
    """
    logger.info("🔄 Training Fraud Detection Model...")

    df = generate_training_data()
    feature_cols = [
        "amount", "hour_of_day", "day_of_week",
        "is_weekend", "amount_zscore", "txn_frequency_1hr",
        "is_new_beneficiary", "amount_to_balance_ratio",
        "is_odd_hour", "transfer_mode_encoded"
    ]
    X = df[feature_cols]

    # Pipeline: Scale → Isolation Forest
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  IsolationForest(
            n_estimators      = 200,
            contamination     = 0.04,   # ~4% fraud rate assumption
            random_state       = 42,
            n_jobs            = -1,
            bootstrap         = True
        ))
    ])

    pipeline.fit(X)

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info(f"✅ Fraud model saved to {MODEL_PATH}")

    return pipeline


def load_fraud_model():
    """Load trained model from disk, train if not exists"""
    if not os.path.exists(MODEL_PATH):
        logger.info("🔄 Model not found — training new model...")
        return train_fraud_model()
    return joblib.load(MODEL_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

TRANSFER_MODE_MAP = {"neft": 0, "rtgs": 1, "imps": 2, "upi": 3, "wallet": 4}

def extract_features(
    amount:             float,
    transfer_mode:      str,
    is_new_beneficiary: bool,
    user_avg_amount:    float,
    user_std_amount:    float,
    txn_count_1hr:      int,
    account_balance:    float,
    transaction_time:   datetime = None
) -> np.ndarray:
    """
    Extract and engineer features for fraud scoring.
    Called at every transaction to get a fraud score.
    """
    if transaction_time is None:
        transaction_time = datetime.utcnow()

    hour       = transaction_time.hour
    dow        = transaction_time.weekday()
    is_weekend = 1 if dow >= 5 else 0
    is_odd_hr  = 1 if 1 <= hour <= 5 else 0

    # Z-score: how unusual is this amount vs user history?
    if user_std_amount > 0:
        amount_zscore = (amount - user_avg_amount) / user_std_amount
    else:
        amount_zscore = 0.0

    # Ratio of amount to balance
    amount_to_balance = amount / max(account_balance, 1.0)
    amount_to_balance = min(amount_to_balance, 1.0)   # Cap at 1.0

    mode_encoded = TRANSFER_MODE_MAP.get(transfer_mode.lower(), 2)

    features = np.array([[
        amount,
        hour,
        dow,
        is_weekend,
        amount_zscore,
        txn_count_1hr,
        1 if is_new_beneficiary else 0,
        amount_to_balance,
        is_odd_hr,
        mode_encoded
    ]])

    return features


# ─────────────────────────────────────────────────────────────────────────────
# FRAUD SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

# Load model once when module is imported
_fraud_model = None

def get_fraud_model():
    global _fraud_model
    if _fraud_model is None:
        _fraud_model = load_fraud_model()
    return _fraud_model


def score_transaction(
    amount:             float,
    transfer_mode:      str,
    is_new_beneficiary: bool,
    user_avg_amount:    float,
    user_std_amount:    float,
    txn_count_1hr:      int,
    account_balance:    float,
    transaction_time:   datetime = None
) -> dict:
    """
    Score a transaction for fraud probability.

    Returns:
        fraud_score:  0.0 (safe) — 1.0 (definite fraud)
        is_fraud:     True/False
        risk_level:   LOW / MEDIUM / HIGH / CRITICAL
        reasons:      List of reasons why it's flagged
        action:       ALLOW / REVIEW / BLOCK
    """

    features = extract_features(
        amount, transfer_mode, is_new_beneficiary,
        user_avg_amount, user_std_amount,
        txn_count_1hr, account_balance, transaction_time
    )

    model = get_fraud_model()

    # Isolation Forest: -1 = anomaly, 1 = normal
    prediction    = model.predict(features)[0]
    anomaly_score = model.score_samples(features)[0]

    # Convert anomaly score to 0-1 fraud probability
    # score_samples returns negative values; more negative = more anomalous
    fraud_score = max(0.0, min(1.0, (-anomaly_score - 0.1) / 0.9))

    # ── Rule-Based Boosters ───────────────────────────────────────────────────
    # These rules BOOST the fraud score on top of ML score
    reasons = []
    rule_boost = 0.0

    if transaction_time:
        hour = transaction_time.hour
        if 1 <= hour <= 5:
            rule_boost += 0.20
            reasons.append("Transaction at odd hours (1AM-5AM)")

    if txn_count_1hr >= 5:
        rule_boost += 0.25
        reasons.append(f"High frequency: {txn_count_1hr} transactions in 1 hour")

    if is_new_beneficiary and amount > 50000:
        rule_boost += 0.20
        reasons.append("Large amount to new/unknown beneficiary")

    if account_balance > 0 and (amount / account_balance) > 0.8:
        rule_boost += 0.15
        reasons.append("Transaction amount > 80% of account balance")

    if user_std_amount > 0:
        zscore = abs(amount - user_avg_amount) / user_std_amount
        if zscore > 4:
            rule_boost += 0.15
            reasons.append(f"Unusually large amount (z-score: {zscore:.1f})")

    if amount > 500000:
        rule_boost += 0.10
        reasons.append("Very high transaction amount (> ₹5,00,000)")

    # Final score
    final_score = min(1.0, fraud_score + rule_boost)

    # ── Risk Classification ───────────────────────────────────────────────────
    if final_score < 0.3:
        risk_level = "LOW"
        action     = "ALLOW"
        is_fraud   = False
    elif final_score < 0.5:
        risk_level = "MEDIUM"
        action     = "ALLOW"
        is_fraud   = False
    elif final_score < 0.7:
        risk_level = "HIGH"
        action     = "REVIEW"
        is_fraud   = True
        if not reasons:
            reasons.append("Unusual transaction pattern detected")
    else:
        risk_level = "CRITICAL"
        action     = "BLOCK"
        is_fraud   = True
        if not reasons:
            reasons.append("High confidence fraud pattern detected")

    return {
        "fraud_score":  round(final_score, 4),
        "is_fraud":     is_fraud,
        "risk_level":   risk_level,
        "action":       action,
        "reasons":      reasons,
        "ml_score":     round(fraud_score, 4),
        "rule_boost":   round(rule_boost, 4)
    }