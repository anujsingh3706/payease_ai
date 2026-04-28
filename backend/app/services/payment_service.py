# backend/app/services/payment_service.py

import razorpay
import hmac
import hashlib
from fastapi   import HTTPException, status
from decimal   import Decimal
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class PaymentService:

    @staticmethod
    def create_order(amount: Decimal, currency: str = "INR") -> dict:
        """
        Create a Razorpay order.
        Amount must be in PAISE (multiply by 100).
        Example: ₹100 → 10000 paise
        """
        try:
            amount_paise = int(float(amount) * 100)

            order = razorpay_client.order.create({
                "amount":   amount_paise,
                "currency": currency,
                "payment_capture": 1    # Auto-capture payment
            })

            logger.info(f"✅ Razorpay order created: {order['id']}")

            return {
                "order_id":   order["id"],
                "amount":     float(amount),
                "amount_paise": amount_paise,
                "currency":   currency,
                "key_id":     settings.RAZORPAY_KEY_ID,   # Send to frontend
                "status":     order["status"]
            }

        except Exception as e:
            logger.error(f"❌ Razorpay order creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment gateway error. Please try again."
            )

    @staticmethod
    def verify_payment(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Verify Razorpay payment signature.
        This is CRITICAL — prevents fake payment notifications.

        Algorithm:
        signature = HMAC-SHA256(order_id + "|" + payment_id, secret_key)
        """
        try:
            params_dict = {
                "razorpay_order_id":   razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature":  razorpay_signature
            }

            razorpay_client.utility.verify_payment_signature(params_dict)
            logger.info(f"✅ Payment verified: {razorpay_payment_id}")
            return True

        except razorpay.errors.SignatureVerificationError:
            logger.warning(f"❌ Invalid payment signature: {razorpay_payment_id}")
            return False

    @staticmethod
    def get_payment_details(payment_id: str) -> dict:
        """Fetch payment details from Razorpay"""
        try:
            payment = razorpay_client.payment.fetch(payment_id)
            return {
                "payment_id": payment["id"],
                "amount":     payment["amount"] / 100,
                "currency":   payment["currency"],
                "status":     payment["status"],
                "method":     payment.get("method"),
                "email":      payment.get("email"),
                "contact":    payment.get("contact")
            }
        except Exception as e:
            logger.error(f"Failed to fetch payment: {e}")
            raise HTTPException(status_code=404, detail="Payment not found")