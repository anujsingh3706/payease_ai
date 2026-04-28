# backend/app/routers/ai/chatbot.py

from fastapi        import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing         import List

from app.database            import get_db
from app.models.user         import User
from app.schemas.chatbot     import ChatRequest, ChatResponse, ChatMessage
from app.ai.groq_chatbot     import get_ai_response, classify_intent
from app.utils.dependencies  import get_current_user

router = APIRouter(prefix="/api/v1/ai/chat", tags=["🤖 AI Chatbot"])


# ── Main Chat Endpoint ────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with PayEase AI Banking Assistant.

    The AI has access to your:
    - Account balance
    - Recent transactions
    - Wallet info
    - Loan applications

    Powered by LLaMA3-70B via Groq (ultra-fast inference).

    Send conversation history for multi-turn conversations.
    """

    # Classify intent (fast, no API call)
    intent = classify_intent(chat_request.message)

    # Convert message history to dict format for Groq
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in chat_request.history
    ]

    # Get AI response
    result = get_ai_response(
        db           = db,
        user         = current_user,
        user_message = chat_request.message,
        conversation_history = history_dicts
    )

    return ChatResponse(
        reply        = result["reply"],
        intent       = intent,
        tokens_used  = result.get("tokens_used"),
        model        = result.get("model"),
        timestamp    = result["timestamp"]
    )


# ── Quick Banking FAQ ─────────────────────────────────────────────────────────

@router.get("/quick-help")
async def quick_help():
    """
    Get list of things you can ask the AI chatbot.
    No auth required — public endpoint.
    """
    return {
        "suggestions": [
            "What is my current balance?",
            "Show me my last 5 transactions",
            "What are the NEFT charges?",
            "How does UPI work?",
            "Am I eligible for a personal loan?",
            "What is CIBIL score and how to improve it?",
            "How to add a beneficiary?",
            "Explain RTGS vs NEFT vs IMPS",
            "What is the daily transfer limit?",
            "How to block my account if lost/stolen?",
            "What is KYC and why is it needed?",
            "How is EMI calculated?",
            "What happens if my balance goes below minimum?",
            "How to set up MPIN?",
            "Explain 2FA security"
        ],
        "powered_by": "LLaMA3-70B via Groq",
        "response_time": "< 1 second"
    }


# ── Banking Knowledge Base ────────────────────────────────────────────────────

@router.get("/banking-terms")
async def banking_terms():
    """Get quick definitions of banking terms"""
    return {
        "terms": {
            "NEFT":  "National Electronic Fund Transfer — batch transfers, ₹2-₹25 charges",
            "RTGS":  "Real Time Gross Settlement — min ₹2L, instant large transfers",
            "IMPS":  "Immediate Payment Service — instant 24x7, max ₹5L",
            "UPI":   "Unified Payment Interface — instant FREE transfers via VPA",
            "MPIN":  "Mobile PIN — 6-digit PIN for authorizing transactions",
            "KYC":   "Know Your Customer — identity verification (Aadhaar + PAN)",
            "CIBIL": "Credit score 300-900 — above 750 is excellent",
            "NPA":   "Non-Performing Asset — loan not repaid for 90+ days",
            "EMI":   "Equated Monthly Installment — monthly loan repayment amount",
            "CBS":   "Core Banking Solution — central banking software (Finacle, BaNCS)",
            "SWIFT": "Society for Worldwide Interbank Financial Telecommunication",
            "IFSC":  "Indian Financial System Code — 11-char bank branch identifier",
            "MICR":  "Magnetic Ink Character Recognition — on cheques",
            "DD":    "Demand Draft — guaranteed payment instrument",
            "TDS":   "Tax Deducted at Source — deducted on interest income",
            "NACH":  "National Automated Clearing House — auto-debit for EMIs"
        }
    }