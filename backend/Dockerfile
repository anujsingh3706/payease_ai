# backend/Dockerfile

# ── Base Image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System Dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Working Directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python Dependencies ───────────────────────────────────────────────
# Copy requirements first — Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy Application Code ─────────────────────────────────────────────────────
COPY . .

# ── Create ML models directory ────────────────────────────────────────────────
RUN mkdir -p ml_models

# ── Train ML Models at build time ─────────────────────────────────────────────
RUN python train_models.py

# ── Expose Port ───────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health Check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start Command ─────────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "30"]