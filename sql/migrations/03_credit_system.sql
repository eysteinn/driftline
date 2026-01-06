-- Credit System Migration
-- This migration adds tables and functionality for the credit-based monetization system

-- Table to track user credit balances
CREATE TABLE user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_credits_user ON user_credits(user_id);

-- Table to track credit transactions (purchases, deductions, refunds)
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL, -- 'purchase', 'deduction', 'refund', 'subscription_grant'
    amount INTEGER NOT NULL, -- positive for credits added, negative for deductions
    balance_after INTEGER NOT NULL,
    description TEXT,
    
    -- Related entities
    mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    package_id UUID,
    
    -- Payment/stripe related fields
    stripe_payment_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_created ON credit_transactions(created_at DESC);
CREATE INDEX idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX idx_credit_transactions_mission ON credit_transactions(mission_id);

-- Table to define available credit packages for purchase
CREATE TABLE credit_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credits INTEGER NOT NULL CHECK (credits > 0),
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_credit_packages_active ON credit_packages(is_active, sort_order);

-- Add credit cost column to missions table
ALTER TABLE missions ADD COLUMN credits_cost INTEGER DEFAULT 0;

-- Add trigger to update updated_at on user_credits
CREATE TRIGGER update_user_credits_updated_at BEFORE UPDATE ON user_credits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add trigger to update updated_at on credit_packages
CREATE TRIGGER update_credit_packages_updated_at BEFORE UPDATE ON credit_packages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default credit packages
INSERT INTO credit_packages (name, description, credits, price_cents, is_active, sort_order) VALUES
    ('Starter Pack', '100 credits - Perfect for trying out the service', 100, 999, TRUE, 1),
    ('Standard Pack', '500 credits - Great for regular users', 500, 3999, TRUE, 2),
    ('Professional Pack', '1500 credits - Best value for professionals', 1500, 9999, TRUE, 3),
    ('Enterprise Pack', '5000 credits - For heavy users', 5000, 29999, TRUE, 4);

-- Function to initialize credits for existing users (one-time)
-- Give existing users 100 free credits to start
INSERT INTO user_credits (user_id, balance)
SELECT id, 100 FROM users
WHERE NOT EXISTS (SELECT 1 FROM user_credits WHERE user_credits.user_id = users.id);

-- Function to automatically create user_credits entry for new users
CREATE OR REPLACE FUNCTION create_user_credits()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_credits (user_id, balance)
    VALUES (NEW.id, 100); -- New users get 100 free credits
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create user_credits when a new user is created
CREATE TRIGGER create_user_credits_on_signup
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_credits();
