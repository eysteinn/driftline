#!/bin/bash
# Script to apply database migration for timestep_contours column

set -e

echo "Applying migration: Add timestep_contours column to mission_results table..."

# Check if we're in the right directory
if [ ! -f "sql/migrations/02_add_timestep_contours.sql" ]; then
    echo "Error: Migration file not found. Please run this script from the project root."
    exit 1
fi

# Apply migration
docker compose -f docker-compose.dev.yml exec -T postgres psql -U driftline_user -d driftline < sql/migrations/02_add_timestep_contours.sql

echo "Migration applied successfully!"
