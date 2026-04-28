# backend/train_models.py
# Run: python train_models.py

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("  PayEase AI — Training All ML Models")
    logger.info("=" * 60)

    # 1 — Fraud Detection
    logger.info("\n[1/3] Training Fraud Detection Model (Isolation Forest)...")
    try:
        from app.ai.fraud_model import train_fraud_model
        train_fraud_model()
        logger.info("✅ Fraud Detection Model — DONE")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")

    # 2 — Credit Score
    logger.info("\n[2/3] Training Credit Score Model (XGBoost)...")
    try:
        from app.ai.credit_model import train_credit_model
        train_credit_model()
        logger.info("✅ Credit Score Model — DONE")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")

    # 3 — Loan Eligibility
    logger.info("\n[3/3] Training Loan Eligibility Model (Random Forest)...")
    try:
        from app.ai.loan_model import train_loan_model
        train_loan_model()
        logger.info("✅ Loan Eligibility Model — DONE")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("  ✅ All 3 models trained and saved to ml_models/")
    logger.info("  Files: fraud_model.pkl | credit_model.pkl | loan_model.pkl")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()