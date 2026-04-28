# backend/app/config_prod.py
# Production-specific settings

import os

# Override for production
PRODUCTION_OVERRIDES = {
    "DEBUG":                         False,
    "ACCESS_TOKEN_EXPIRE_MINUTES":   30,
    "REFRESH_TOKEN_EXPIRE_DAYS":     7,
}

def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv("RENDER", False) or os.getenv("ENV", "dev") == "production"