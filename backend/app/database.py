# backend/app/database.py

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,          # Test connection before using
    pool_size=10,                # Max 10 connections in pool
    max_overflow=20,             # 20 extra connections allowed
    pool_recycle=3600,           # Recycle connections every 1 hour
    echo=settings.DEBUG          # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session.
    Used with FastAPI's Depends() system.
    Automatically closes session after request.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all tables defined in models"""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ All database tables created successfully")


def drop_tables():
    """Drop all tables — USE ONLY IN DEVELOPMENT"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("⚠️ All database tables dropped")