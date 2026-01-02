# API Keys Implementation

This document describes the API keys functionality implementation for the Driftline platform.

## Overview

Users can now create, manage, and delete API keys with variable lifetimes through the web UI. The implementation includes:

- Backend API handlers for CRUD operations
- Frontend UI with lifetime selection
- Automatic cleanup of expired keys
- Secure key storage with SHA256 hashing

## Features

### 1. Variable Lifetime Support

Users can create API keys with the following lifetime options:

- **Never expires**: Infinite lifetime (null expiration date)
- **7 days**: Short-term testing keys
- **30 days**: Monthly rotation
- **90 days**: Quarterly rotation
- **365 days**: Annual rotation
- **Custom**: User-specified number of days

### 2. Secure Key Storage

- API keys are generated using cryptographically secure random bytes (32 bytes)
- Keys are base64 URL-encoded for easy transmission
- Only SHA256 hashes are stored in the database (not the actual keys)
- Keys are shown to users only once during creation

### 3. Automatic Cleanup

- A background goroutine runs every hour to clean up expired keys
- Runs immediately on API server startup
- Deletes all keys where `expires_at < NOW()`

### 4. User Interface

The API Keys page (`/api-keys`) provides:

- Table view of all user's API keys with:
  - Name
  - Key preview (first 4 and last 4 characters)
  - Status (Active/Expired)
  - Expiration date
  - Last used timestamp
  - Creation date
  - Delete action
- Create dialog with:
  - Name input
  - Expiration dropdown (never, 7d, 30d, 90d, 1y, custom)
  - Custom days input (when "Custom" is selected)
- One-time key display after creation with copy button

## Implementation Details

### Backend (Go)

#### Files Created/Modified

1. **`services/api/internal/models/apikey.go`** (new)
   - `ApiKey` struct with all fields including `ExpiresAt`
   - `CreateApiKeyRequest` struct with `ExpiresInDays` field
   - `CreateApiKeyResponse` struct for returning the key once

2. **`services/api/internal/handlers/apikeys.go`** (new)
   - `ListApiKeys()` - Get all API keys for authenticated user
   - `CreateApiKey()` - Create new API key with optional expiration
   - `DeleteApiKey()` - Delete an API key
   - `CleanupExpiredApiKeys()` - Remove expired keys from database
   - Helper functions: `generateApiKey()`, `hashApiKey()`, `createKeyPreview()`

3. **`services/api/cmd/api-gateway/main.go`** (modified)
   - Added API key routes under `/api/v1/users/me/api-keys`
   - Started cleanup goroutine with 1-hour ticker

#### API Endpoints

```
GET    /api/v1/users/me/api-keys      - List all API keys
POST   /api/v1/users/me/api-keys      - Create new API key
DELETE /api/v1/users/me/api-keys/:id  - Delete API key
```

#### Request/Response Examples

**Create API Key (30 days expiration):**
```json
POST /api/v1/users/me/api-keys
{
  "name": "Production Server",
  "expiresInDays": 30
}
```

Response:
```json
{
  "data": {
    "key": "dGhpc19pc19hX3NhbXBsZV9rZXlfZm9yX2RlbW8=",
    "apiKey": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "userId": "user-id-here",
      "name": "Production Server",
      "isActive": true,
      "createdAt": "2026-01-02T18:00:00Z",
      "expiresAt": "2026-02-01T18:00:00Z",
      "keyPreview": "dGhp...bW8="
    }
  }
}
```

**Create API Key (never expires):**
```json
POST /api/v1/users/me/api-keys
{
  "name": "Development Key",
  "expiresInDays": null
}
```

### Frontend (React/TypeScript)

#### Files Modified

1. **`frontend/src/pages/ApiKeysPage.tsx`**
   - Added `expiresInDays` and `customDays` state variables
   - Added expiration dropdown with options
   - Added custom days input field
   - Added `isExpired()` and `formatExpiration()` helper functions
   - Updated table to show expiration date
   - Updated status chip to show "Expired" for expired keys

2. **`frontend/src/services/api.ts`**
   - Updated `createApiKey()` method signature to accept `expiresInDays` parameter

### Database Schema

The `api_keys` table already existed with the required fields:

```sql
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
```

## Security Considerations

1. **Key Generation**: Uses `crypto/rand` for cryptographically secure random number generation
2. **Key Storage**: Only SHA256 hashes are stored, never the actual keys
3. **Key Display**: Keys are shown only once during creation
4. **Key Transmission**: Keys use base64 URL encoding for safe transmission
5. **User Isolation**: All operations are scoped to the authenticated user
6. **Cascade Delete**: API keys are automatically deleted when a user is deleted

## Testing

### Manual Testing

1. **Build Tests**:
   ```bash
   cd services/api && go build ./cmd/api-gateway/
   cd frontend && npm run build
   ```

2. **Lint Tests**:
   ```bash
   cd services/api && go vet ./...
   cd frontend && npm run lint
   ```

3. **Structure Test**:
   ```bash
   python3 test_api_keys.py
   ```

### Integration Testing (requires running services)

1. Start the development environment:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. Navigate to `http://localhost:5173/api-keys` (after logging in)

3. Test creating keys with different lifetimes

4. Verify expiration dates are displayed correctly

5. Test deleting keys

## Future Enhancements

Potential improvements for the future:

1. **API Key Authentication**: Implement middleware to authenticate requests using API keys (currently only JWT is supported)
2. **Scopes**: Implement scope-based permissions for API keys
3. **Usage Tracking**: Track and display API key usage statistics
4. **Rate Limiting**: Implement per-key rate limiting
5. **Key Rotation**: Add ability to rotate keys (create new, deprecate old)
6. **Audit Log**: Track API key usage in audit logs
7. **Notifications**: Send email notifications before key expiration
8. **Key Regeneration**: Allow regenerating keys while keeping the same ID

## Troubleshooting

### Keys not appearing after creation

- Check browser console for API errors
- Verify backend is running and accessible
- Check authentication token is valid

### Cleanup not running

- Check API server logs for cleanup messages
- Verify database connection is active
- Check for any error messages in logs

### Expired keys not being removed

- Cleanup runs hourly, so there may be up to 1-hour delay
- Manual cleanup can be triggered by restarting the API server
- Check database directly: `SELECT * FROM api_keys WHERE expires_at < NOW()`
