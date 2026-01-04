-- Add backtracking column to missions table
ALTER TABLE missions ADD COLUMN IF NOT EXISTS backtracking BOOLEAN DEFAULT FALSE;
