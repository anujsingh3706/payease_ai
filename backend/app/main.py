# backend/app/main.py

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import logging
import time

from app.config import settings
from app.database import create_tables

# ── Import Core Routers ───────────────────────────────────────────────────────
from app.routers.auth         import router as auth_router
from app.routers.accounts     import router as accounts_router
from app.routers.transactions import router as transactions_router
from app.routers.wallet       import router as wallet_router
from app.routers.payments     import router as payments_router
from app.routers.dashboard    import router as dashboard_router

# ── Import AI Routers ─────────────────────────────────────────────────────────
from app.routers.ai.chatbot        import router as chatbot_router
from app.routers.ai.fraud          import router as fraud_router
from app.routers.ai.credit_score   import router as credit_router
from app.routers.ai.loan_predictor import router as loan_router
from app.routers.ai.spend_analyser import router as spend_router


# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## 🏦 PayEase AI — Smart Digital Banking System

    ### Features:
    - **Authentication** — Register, Login, JWT, MPIN
    - **Banking** — Accounts, Transfers, Passbook
    - **Wallet** — Digital wallet with UPI
    - **Payments** — Razorpay integration
    - **AI Modules**:
        - 🔴 Fraud Detection
        - 🤖 AI Chatbot (Groq LLaMA3)
        - 📊 Spend Analyser
        - 💳 Credit Score Predictor
        - 🏠 Loan Eligibility Predictor
        - 🔐 Login Anomaly Detection
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ── Rate Limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Timing Middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time   = time.time()
    response     = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response


# ── Validation Error Handler ──────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field":   " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type":    error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors}
    )


# ── Startup Event ─────────────────────────────────────────────────────────────
# ADD inside startup_event() in main.py

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 PayEase AI Backend Starting...")
    create_tables()

    # Train models if not present (important for Render deploy)
    import os
    models_dir = os.path.join(os.path.dirname(__file__), "../ml_models")
    model_files = ["fraud_model.pkl", "credit_model.pkl", "loan_model.pkl"]
    missing = [f for f in model_files if not os.path.exists(os.path.join(models_dir, f))]

    if missing:
        logger.info(f"🔄 Training missing models: {missing}")
        try:
            from app.ai.fraud_model  import train_fraud_model
            from app.ai.credit_model import train_credit_model
            from app.ai.loan_model   import train_loan_model
            if "fraud_model.pkl"  in missing: train_fraud_model()
            if "credit_model.pkl" in missing: train_credit_model()
            if "loan_model.pkl"   in missing: train_loan_model()
        except Exception as e:
            logger.warning(f"⚠️ Model training warning: {e}")

    logger.info(f"✅ App ready | Docs: /docs")


# ── Shutdown Event ────────────────────────────────────────────────────────────
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 PayEase AI Backend Shutting Down...")


# ── Include Core Routers ──────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(wallet_router)
app.include_router(payments_router)
app.include_router(dashboard_router)

# ── Include AI Routers ────────────────────────────────────────────────────────
app.include_router(chatbot_router)
app.include_router(fraud_router)
app.include_router(credit_router)
app.include_router(loan_router)
app.include_router(spend_router)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "🟢 Running",
        "docs":    "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status":  "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }