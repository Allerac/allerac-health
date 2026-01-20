-- Allerac Health - Database Schema
-- This script runs automatically on PostgreSQL initialization

-- Extension for UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULL if using OAuth
    name VARCHAR(255),
    avatar_url TEXT,
    oauth_provider VARCHAR(50),  -- 'google', 'github', NULL for email/password
    oauth_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for OAuth lookup
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);

-- Garmin credentials table (sensitive data encrypted)
CREATE TABLE IF NOT EXISTS garmin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email_encrypted BYTEA NOT NULL,
    password_encrypted BYTEA,  -- Used only for initial login
    oauth1_token_encrypted BYTEA,  -- Garmin OAuth1 token
    oauth2_token_encrypted BYTEA,  -- Garmin OAuth2 token
    is_connected BOOLEAN DEFAULT FALSE,
    mfa_pending BOOLEAN DEFAULT FALSE,  -- Waiting for MFA code
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    sync_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Sync jobs table (history)
CREATE TABLE IF NOT EXISTS sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, mfa_required
    job_type VARCHAR(50) NOT NULL DEFAULT 'full',  -- full, incremental, manual
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    records_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,  -- Extra job data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for job lookup by user and status
CREATE INDEX IF NOT EXISTS idx_sync_jobs_user_status ON sync_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_created ON sync_jobs(created_at DESC);

-- Pending MFA sessions table
CREATE TABLE IF NOT EXISTS mfa_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    garmin_email VARCHAR(255) NOT NULL,
    session_data BYTEA,  -- Encrypted Garmin session data
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    timezone VARCHAR(100) DEFAULT 'UTC',
    sync_interval_minutes INTEGER DEFAULT 60,  -- Sync interval in minutes
    notifications_enabled BOOLEAN DEFAULT TRUE,
    fetch_selection JSONB DEFAULT '["daily_avg", "sleep", "steps", "heartrate", "stress", "hrv"]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_garmin_credentials_updated_at
    BEFORE UPDATE ON garmin_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Table comments
COMMENT ON TABLE users IS 'System users';
COMMENT ON TABLE garmin_credentials IS 'Encrypted Garmin credentials per user';
COMMENT ON TABLE sync_jobs IS 'Sync job history';
COMMENT ON TABLE mfa_sessions IS 'Temporary sessions for Garmin MFA';
COMMENT ON TABLE user_settings IS 'User custom settings';
