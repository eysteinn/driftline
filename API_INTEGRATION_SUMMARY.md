# Backend API Integration Summary

## Overview
This document summarizes the backend API integration work completed to connect the React frontend with the Go API server.

## Changes Made

### 1. Authentication & Authorization
- **JWT Implementation**: Added proper JWT token generation using `golang-jwt/jwt/v5`
  - Access tokens: 1 hour expiration
  - Refresh tokens: 7 days expiration
  - Tokens include `user_id`, `email`, `type`, `exp`, and `iat` claims

- **Authentication Middleware**: Created `middleware/auth.go` to validate JWT tokens on protected routes
  - Extracts and validates Bearer tokens from Authorization header
  - Sets user context for downstream handlers

### 2. CORS Configuration
- Added `gin-contrib/cors` middleware
- Configured to allow:
  - Origins: `http://localhost:3000`, `http://localhost:5173` (Vite dev server)
  - Credentials: enabled
  - Headers: Origin, Content-Type, Accept, Authorization
  - Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS

### 3. API Response Standardization
- Created `utils/response.go` with standardized response helpers:
  - `SuccessResponse`: Wraps data in `{ data: ... }` format
  - `ErrorResponse`: Returns `{ error: ..., message: ... }` format
  - `PaginatedResponse`: Includes pagination metadata

### 4. API Endpoints Implemented

#### Auth Endpoints (Public)
- `POST /api/v1/auth/register` - User registration with JWT tokens
- `POST /api/v1/auth/login` - User login with JWT tokens
- `POST /api/v1/auth/logout` - Logout (client-side JWT invalidation)

#### User Endpoints (Protected)
- `GET /api/v1/users/me` - Get current authenticated user
- `PATCH /api/v1/users/me` - Update current user profile

#### Mission Endpoints (Protected)
- `POST /api/v1/missions` - Create new drift forecast mission
- `GET /api/v1/missions` - List user's missions (paginated)
- `GET /api/v1/missions/:id` - Get specific mission details
- `DELETE /api/v1/missions/:id` - Delete mission
- `GET /api/v1/missions/:id/status` - Get mission status
- `GET /api/v1/missions/:id/results` - Get mission results (when completed)

### 5. Data Model Updates
Updated all Go models to use camelCase JSON tags for frontend compatibility:
- `User`: id, email, fullName, isActive, isVerified, role, createdAt, updatedAt
- `Mission`: id, userId, name, description, lastKnownLat, lastKnownLon, lastKnownTime, objectType, uncertaintyRadiusM, forecastHours, ensembleSize, status, jobId, errorMessage, createdAt, updatedAt, completedAt
- `MissionResult`: id, missionId, centroidLat, centroidLon, centroidTime, searchArea50Geom, searchArea90Geom, netcdfPath, geojsonPath, pdfReportPath, particleCount, strandedCount, computationTimeSeconds, createdAt

### 6. Security Improvements
- Removed temporary workarounds that selected first user from database
- All protected endpoints now validate JWT and check resource ownership
- Mission endpoints verify user owns the mission before allowing access

## API Contract

### Request Format
Frontend sends JSON with camelCase keys:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "fullName": "John Doe"
}
```

### Response Format
All responses follow standardized format:

**Success Response:**
```json
{
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "fullName": "John Doe",
      ...
    }
  }
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "message": "Error message"
}
```

**Paginated Response:**
```json
{
  "data": [...],
  "total": 10,
  "page": 1,
  "perPage": 50
}
```

## Environment Variables
Required environment variables for API server:
- `DATABASE_URL`: PostgreSQL connection string (add `?sslmode=disable` for local dev)
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret key for JWT signing (change in production!)
- `PORT`: Server port (default: 8000)

## Testing
All endpoints have been manually tested and verified to work correctly:
- ✅ User registration with JWT tokens
- ✅ User login with JWT tokens
- ✅ Protected endpoints require valid JWT
- ✅ Mission CRUD operations
- ✅ Proper authorization checks
- ✅ CamelCase JSON serialization

## Next Steps
1. Implement token refresh endpoint (`POST /api/v1/auth/refresh`)
2. Add WebSocket support for real-time mission status updates
3. Implement API key management endpoints
4. Add billing/subscription endpoints
5. Integrate with Redis queue for job processing
6. Add rate limiting middleware

## Notes
- API base URL: `http://localhost:8000/api/v1`
- All timestamps are in RFC3339 format
- UUIDs are used for all resource IDs
- Frontend expects camelCase, backend uses snake_case in database
