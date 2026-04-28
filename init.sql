-- init.sql
-- Runs automatically when PostgreSQL container starts for first time

-- Create the database (already created by POSTGRES_DB env var)
-- This file is for any initial setup needed

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search (used in transaction search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Log startup
DO $$
BEGIN
    RAISE NOTICE '✅ PayEase AI Database initialized successfully';
END $$;