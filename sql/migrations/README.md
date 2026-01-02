# Database Migration: Add key_preview Column

## Issue

If you're seeing 500 Internal Server Error when accessing `/api-keys` or trying to create API keys, it's because your database was created with the old schema that doesn't include the `key_preview` column.

## Solution

Run the following command to apply the migration:

```bash
make db-migrate
```

Or manually:

```bash
./migrate.sh
```

Or if you prefer to do it manually via psql:

```bash
docker compose -f docker-compose.dev.yml exec -T postgres psql -U driftline_user -d driftline < sql/migrations/01_add_key_preview.sql
```

## What This Does

This migration adds the `key_preview` column to the `api_keys` table. This column stores a preview of the API key (first and last 4 characters) for display purposes, since we only store the SHA256 hash of the actual key for security.

## Verification

After running the migration, you can verify it was applied successfully:

```bash
docker compose -f docker-compose.dev.yml exec postgres psql -U driftline_user -d driftline -c "\d api_keys"
```

You should see `key_preview` in the list of columns.

## Note

The migration is idempotent, meaning you can run it multiple times safely. It will only add the column if it doesn't already exist.
