# backend/app/ai/groq_chatbot.py

from groq import Groq
from sqlalchemy.orm import Session
from datetime import datetime
from decimal  import Decimal
from typing   import List, Dict, Optional
import logging
import json

from app.config  import settings
from app.models.user        import User
from app.models.account     import Account, AccountStatus
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.wallet      import Wallet
from app.models.loan        import LoanApplication

logger = logging.getLogger(__name__)

# ── Initialize Groq Client ────────────────────────────────────────────────────
groq_client = Groq(api_key=settings.GROQ_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — This is what makes the chatbot a banking expert
# ─────────────────────────────────────────────────────────────────────────────

BANKING_SYSTEM_PROMPT = """
You are PayEase AI Assistant — a smart, professional, and friendly banking assistant 
for PayEase Digital Bank (India). You have access to the user's real account data 
provided below in the context.

## YOUR CAPABILITIES:
- Answer questions about the user's account balance, transactions, wallet
- Explain banking concepts (NEFT, RTGS, IMPS, UPI, CIBIL, KYC etc.)
- Help users understand their spending patterns
- Guide users on how to use PayEase features
- Answer RBI guidelines and banking regulations questions
- Explain loan eligibility, EMI calculations
- Provide financial advice (general, not specific investment advice)

## RULES YOU MUST FOLLOW:
1. NEVER ask for or reveal full account numbers, passwords, or OTPs
2. Always be helpful, polite, and professional
3. If user asks to DO a transaction (send money), explain they must use the app
4. Give answers in simple language — users may not be banking experts
5. For sensitive security issues, always recommend contacting support
6. All monetary amounts should be in Indian Rupees (₹)
7. Keep responses concise but complete — use bullet points when listing multiple items
8. If you don't know something, say so honestly

## BANKING KNOWLEDGE:
- NEFT: National Electronic Fund Transfer — batch processing, charges ₹2-₹25
- RTGS: Real Time Gross Settlement — min ₹2 lakh, instant, charges ₹25-₹50
- IMPS: Immediate Payment Service — instant 24x7, charges ₹2.50-₹25
- UPI: Unified Payment Interface — instant, FREE, max ₹1 lakh per txn
- MPIN: Mobile PIN — 6-digit PIN for transaction authorization
- KYC: Know Your Customer — Aadhaar + PAN verification required
- CIBIL Score: Credit score 300-900, above 750 is good for loans
- RBI Guidelines: Max wallet limit ₹2 lakh for KYC-verified users

## CURRENT DATE: {current_date}

## USER ACCOUNT DATA (use this to answer account-specific questions):
{user_context}
"""


# ─────────────────────────────────────────────────────────────────────────────
# FETCH USER CONTEXT — Real-time data from DB
# ─────────────────────────────────────────────────────────────────────────────

def get_user_banking_context(db: Session, user: User) -> str:
    """
    Builds a structured context string from the user's real banking data.
    This is injected into the system prompt so the AI knows their account info.
    """

    # Get primary account
    account = db.query(Account).filter(
        Account.user_id    == user.id,
        Account.is_primary == True
    ).first()

    # Get wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()

    # Get last 5 transactions
    recent_txns = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_status == TransactionStatus.SUCCESS
    ).order_by(Transaction.initiated_at.desc()).limit(5).all()

    # This month's spending
    from sqlalchemy import func
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

    month_spent = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_type.in_([
            TransactionType.TRANSFER,
            TransactionType.PAYMENT,
            TransactionType.DEBIT
        ]),
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= month_start
    ).scalar() or 0

    # Active loans
    active_loans = db.query(LoanApplication).filter(
        LoanApplication.user_id == user.id
    ).order_by(LoanApplication.applied_at.desc()).limit(3).all()

    # Build context
    context = f"""
USER PROFILE:
- Name: {user.full_name}
- Phone: {user.phone_number}
- KYC Status: {user.kyc_status.value}
- Member Since: {user.created_at.strftime('%B %Y') if user.created_at else 'N/A'}

BANK ACCOUNT:
- Account Number: XXXX{account.account_number[-4:] if account else 'N/A'}  
- Account Type: {account.account_type.value.title() if account else 'N/A'}
- Balance: ₹{float(account.balance):,.2f} if account else 'N/A'
- Account Status: {account.account_status.value if account else 'N/A'}
- Daily Limit: ₹{float(account.daily_limit):,.2f} if account else 'N/A'

WALLET:
- Wallet Balance: ₹{float(wallet.balance):,.2f} if wallet else '₹0.00'
- UPI ID: {wallet.upi_id if wallet else 'Not set'}
- Daily Limit: ₹{float(wallet.daily_limit):,.2f} if wallet else 'N/A'

THIS MONTH:
- Total Spent: ₹{float(month_spent):,.2f}

RECENT TRANSACTIONS (last 5):
"""

    if recent_txns:
        for t in recent_txns:
            context += (
                f"  - {t.initiated_at.strftime('%d %b')} | "
                f"{t.transaction_type.value.upper()} | "
                f"₹{float(t.amount):,.2f} | "
                f"{t.description or 'No description'} | "
                f"{'⚠️ FLAGGED' if t.is_flagged else '✅'}\n"
            )
    else:
        context += "  - No transactions yet\n"

    if active_loans:
        context += "\nLOAN APPLICATIONS:\n"
        for loan in active_loans:
            context += (
                f"  - {loan.loan_type.value.title()} Loan | "
                f"₹{float(loan.amount_requested):,.2f} | "
                f"Status: {loan.loan_status.value.upper()}\n"
            )

    return context


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHATBOT FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_ai_response(
    db: Session,
    user: User,
    user_message: str,
    conversation_history: List[Dict]
) -> Dict:
    """
    Main function to get AI response from Groq.

    Args:
        db: Database session
        user: Current logged-in user
        user_message: What the user typed
        conversation_history: List of previous messages [{role, content}]

    Returns:
        dict with response, tokens used, model info
    """

    # Get real-time user banking context
    user_context = get_user_banking_context(db, user)

    # Build system prompt with user data injected
    system_prompt = BANKING_SYSTEM_PROMPT.format(
        current_date=datetime.utcnow().strftime("%d %B %Y"),
        user_context=user_context
    )

    # Build messages array — include history for multi-turn conversation
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 10 messages to stay within context limit)
    if conversation_history:
        messages.extend(conversation_history[-10:])

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        # Call Groq API
        response = groq_client.chat.completions.create(
            model       = settings.GROQ_MODEL,
            messages    = messages,
            max_tokens  = 1024,
            temperature = 0.3,      # Lower = more factual, less creative
            top_p       = 0.9,
            stream      = False
        )

        ai_reply = response.choices[0].message.content
        tokens   = response.usage

        logger.info(
            f"✅ Groq response | User: {user.email} | "
            f"Tokens: {tokens.total_tokens}"
        )

        return {
            "reply":             ai_reply,
            "tokens_used":       tokens.total_tokens,
            "prompt_tokens":     tokens.prompt_tokens,
            "completion_tokens": tokens.completion_tokens,
            "model":             settings.GROQ_MODEL,
            "timestamp":         datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Groq API error: {e}")
        return {
            "reply": (
                "I'm sorry, I'm having trouble connecting right now. "
                "Please try again in a moment or contact our support team."
            ),
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ─────────────────────────────────────────────────────────────────────────────
# QUICK INTENT CLASSIFIER — Rule-based pre-filter
# ─────────────────────────────────────────────────────────────────────────────

def classify_intent(message: str) -> str:
    """
    Quickly classify user message intent before sending to LLM.
    Helps route simple queries without using API tokens.
    """
    msg = message.lower().strip()

    # Balance check keywords
    if any(w in msg for w in ["balance", "kitna hai", "how much", "bakiya"]):
        return "balance_inquiry"

    # Transaction history
    if any(w in msg for w in ["transaction", "history", "statement", "passbook", "last"]):
        return "transaction_history"

    # Transfer related
    if any(w in msg for w in ["transfer", "send", "bhejo", "payment", "pay"]):
        return "transfer_query"

    # Loan related
    if any(w in msg for w in ["loan", "emi", "credit", "borrow", "interest"]):
        return "loan_query"

    # UPI related
    if any(w in msg for w in ["upi", "qr", "scan", "phonepe", "gpay"]):
        return "upi_query"

    # Security/fraud
    if any(w in msg for w in ["fraud", "block", "suspicious", "hack", "stolen"]):
        return "security_query"

    return "general_query"