#!/bin/bash
# Script to apply database migration for key_preview column

set -e

echo "Applying migration: Add key_preview column to api_keys table..."

# Check if we're in the right directory
if [ ! -f "sql/migrations/01_add_key_preview.sql" ]; then
    echo "Error: Migration file not found. Please run this script from the project root."
    exit 1
fi

# Apply migration
docker compose -f docker-compose.dev.yml exec -T postgres psql -U driftline_user -d driftline < sql/migrations/01_add_key_preview.sql

echo "Migration applied successfully!"
