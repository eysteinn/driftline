-- Migration to add key_preview column to api_keys table
-- This migration is idempotent and can be run multiple times safely

DO $$ 
BEGIN
    -- Add key_preview column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'api_keys' 
        AND column_name = 'key_preview'
    ) THEN
        ALTER TABLE api_keys ADD COLUMN key_preview VARCHAR(50);
        RAISE NOTICE 'Added key_preview column to api_keys table';
    ELSE
        RAISE NOTICE 'key_preview column already exists in api_keys table';
    END IF;
END $$;
