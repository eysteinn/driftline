-- Driftline Database Initialization Script
-- PostgreSQL 16+

-- Enable required extensions
-- Note: gen_random_uuid() is built-in to PostgreSQL 13+ and doesn't require an extension
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Users and Authentication Tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    scopes JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

-- Missions Tables
CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    description TEXT,
    
    -- Input parameters
    last_known_lat FLOAT NOT NULL,
    last_known_lon FLOAT NOT NULL,
    last_known_time TIMESTAMP NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    uncertainty_radius_m FLOAT,
    forecast_hours INTEGER NOT NULL,
    ensemble_size INTEGER DEFAULT 1000,
    
    -- Configuration
    config JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'created',
    job_id UUID,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_missions_user ON missions(user_id);
CREATE INDEX idx_missions_status ON missions(status);
CREATE INDEX idx_missions_created ON missions(created_at DESC);
CREATE INDEX idx_missions_job_id ON missions(job_id);

-- Mission Results Tables
CREATE TABLE mission_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
    
    -- Computed positions
    centroid_lat FLOAT,
    centroid_lon FLOAT,
    centroid_time TIMESTAMP,
    
    -- Search areas (stored as GeoJSON)
    search_area_50_geom JSONB,
    search_area_90_geom JSONB,
    search_area_95_geom JSONB,
    
    -- File paths (S3 URIs)
    netcdf_path VARCHAR(500),
    geojson_path VARCHAR(500),
    heatmap_path VARCHAR(500),
    pdf_report_path VARCHAR(500),
    
    -- Metadata
    particle_count INTEGER,
    stranded_count INTEGER,
    computation_time_seconds FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mission_results_mission ON mission_results(mission_id);

-- Billing and Subscriptions Tables
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    usage_type VARCHAR(50) NOT NULL,
    quantity INTEGER DEFAULT 1,
    amount_cents INTEGER,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_usage_records_user ON usage_records(user_id);
CREATE INDEX idx_usage_records_recorded ON usage_records(recorded_at DESC);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    stripe_invoice_id VARCHAR(255),
    amount_cents INTEGER,
    status VARCHAR(50),
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invoices_user ON invoices(user_id);
CREATE INDEX idx_invoices_stripe ON invoices(stripe_invoice_id);

-- Audit Log Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_missions_updated_at BEFORE UPDATE ON missions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
