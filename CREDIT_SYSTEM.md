# Credit System Documentation

## Overview

The Driftline platform uses a credit-based monetization system where users purchase credits to run drift forecast missions. This system enables flexible monetization through one-time purchases and subscriptions.

## Features

- **Credit Balance Management**: Each user has a credit balance tracked in the database
- **Transaction History**: All credit events (purchases, deductions, refunds) are logged for auditing
- **Credit Packages**: Pre-defined credit packages available for purchase
- **Mission Cost Calculation**: Dynamic pricing based on mission parameters
- **Insufficient Credit Protection**: Missions cannot be created without sufficient credits

## Credit Pricing Model

### Mission Cost Calculation

The cost of a mission is calculated based on:
- **Base cost**: 10 credits
- **Forecast duration**: +1 credit per 24 hours (rounded up)
- **Particle count**: +1 credit per 1000 particles above the base 1000

**Formula:**
```
cost = 10 + ceil(forecast_hours / 24) + floor((ensemble_size - 1000) / 1000)
```

**Examples:**
- 24-hour forecast, 1000 particles: 11 credits
- 48-hour forecast, 1000 particles: 12 credits
- 24-hour forecast, 5000 particles: 15 credits
- 168-hour forecast, 10000 particles: 26 credits

### Credit Packages

Default packages available for purchase:

| Package | Credits | Price | Description |
|---------|---------|-------|-------------|
| Starter Pack | 100 | $9.99 | Perfect for trying out the service |
| Standard Pack | 500 | $39.99 | Great for regular users |
| Professional Pack | 1500 | $99.99 | Best value for professionals |
| Enterprise Pack | 5000 | $299.99 | For heavy users |

## API Endpoints

### Get Credit Balance

Get the current credit balance for the authenticated user.

**Endpoint:** `GET /api/v1/credits/balance`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "data": {
    "balance": 100
  }
}
```

### List Credit Packages

Get available credit packages for purchase.

**Endpoint:** `GET /api/v1/credits/packages`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Starter Pack",
      "description": "100 credits - Perfect for trying out the service",
      "credits": 100,
      "priceCents": 999,
      "isActive": true,
      "sortOrder": 1,
      "createdAt": "2026-01-04T17:27:48.266237Z",
      "updatedAt": "2026-01-04T17:27:48.266237Z"
    }
  ]
}
```

### Purchase Credits

Purchase a credit package.

**Endpoint:** `POST /api/v1/credits/purchase`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "packageId": "uuid"
}
```

**Response:**
```json
{
  "data": {
    "success": true,
    "creditsAdded": 100,
    "newBalance": 200,
    "message": "Purchased Starter Pack (100 credits)"
  }
}
```

**Note:** Currently, this endpoint simulates successful purchases. In production, this should be integrated with Stripe payment processing.

### Add Credits (Subscription/Admin)

Manually add credits to a user account (for subscriptions or admin operations).

**Endpoint:** `POST /api/v1/credits/add`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": 500,
  "description": "Monthly subscription credit grant"
}
```

**Response:**
```json
{
  "data": {
    "success": true,
    "creditsAdded": 500,
    "newBalance": 700
  }
}
```

### Get Transaction History

Get the transaction history for the authenticated user.

**Endpoint:** `GET /api/v1/credits/transactions`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "userId": "uuid",
      "transactionType": "deduction",
      "amount": -12,
      "balanceAfter": 188,
      "description": "Mission: Test Mission (48 forecast hours, 1000 particles)",
      "missionId": "uuid",
      "createdAt": "2026-01-04T17:32:55.533759Z"
    },
    {
      "id": "uuid",
      "userId": "uuid",
      "transactionType": "purchase",
      "amount": 100,
      "balanceAfter": 200,
      "description": "Purchased Starter Pack (100 credits)",
      "packageId": "uuid",
      "createdAt": "2026-01-04T17:32:55.50763Z"
    }
  ],
  "page": 1,
  "perPage": 50,
  "total": 2
}
```

### Create Mission (With Credit Deduction)

When creating a mission, the system will:
1. Calculate the credit cost based on mission parameters
2. Check if the user has sufficient credits
3. Create the mission if credits are available
4. Deduct the credits and record the transaction
5. Reject the mission if credits are insufficient

**Endpoint:** `POST /api/v1/missions`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Test Mission",
  "description": "Test description",
  "lastKnownLat": 60.0,
  "lastKnownLon": -30.0,
  "lastKnownTime": "2026-01-04T12:00:00Z",
  "objectType": "1",
  "forecastHours": 48,
  "ensembleSize": 1000
}
```

**Success Response:**
```json
{
  "data": {
    "id": "uuid",
    "userId": "uuid",
    "name": "Test Mission",
    "creditsCost": 12,
    "status": "queued",
    ...
  }
}
```

**Insufficient Credits Response (402 Payment Required):**
```json
{
  "error": "Insufficient credits. You have 5 credits, but this mission requires 12 credits. Please purchase more credits."
}
```

## Database Schema

### user_credits

Tracks user credit balances.

```sql
CREATE TABLE user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### credit_transactions

Records all credit transactions for auditing and history.

```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    package_id UUID,
    stripe_payment_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Transaction Types:**
- `purchase`: Credits purchased via one-time payment
- `deduction`: Credits deducted for mission execution
- `refund`: Credits refunded (e.g., failed mission)
- `subscription_grant`: Credits added via subscription

### credit_packages

Defines available credit packages for purchase.

```sql
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
```

### missions (Modified)

Added `credits_cost` column to track the cost of each mission.

```sql
ALTER TABLE missions ADD COLUMN credits_cost INTEGER DEFAULT 0;
```

## Onboarding

### New User Credits

New users automatically receive **100 free credits** upon registration to try the service. This is handled by a database trigger that creates a `user_credits` record when a new user is created.

## Subscription Integration

The system is designed to support subscription-based credit grants:

1. When a user subscribes, use the `/api/v1/credits/add` endpoint to grant monthly credits
2. Store subscription details in the `subscriptions` table
3. Record each monthly grant as a `subscription_grant` transaction
4. Link transactions to Stripe subscription IDs for reconciliation

## Payment Integration (TODO)

The purchase endpoint currently simulates successful payments. For production:

1. **Integrate Stripe Payment Intents**:
   - Create payment intent before processing purchase
   - Confirm payment with provided payment method
   - Only add credits after successful payment

2. **Add Webhook Handler**:
   - Handle `payment_intent.succeeded` events
   - Handle `invoice.payment_succeeded` for subscriptions
   - Add credits when payments are confirmed

3. **Refund Handling**:
   - Implement credit refund logic for failed missions
   - Handle Stripe refund webhooks
   - Record refund transactions

## Testing

The credit system has been tested with the following scenarios:

1. ✅ New user registration with 100 free credits
2. ✅ Credit balance retrieval
3. ✅ Credit package listing
4. ✅ Credit purchase
5. ✅ Transaction history retrieval
6. ✅ Mission creation with sufficient credits
7. ✅ Credit deduction for missions
8. ✅ Mission rejection with insufficient credits
9. ✅ Accurate credit cost calculation

## Security Considerations

- Credit balances are protected by database constraints (cannot be negative)
- All credit operations use database transactions for consistency
- Credit deductions use row-level locks to prevent race conditions
- Transaction history provides audit trail for all credit events
- Authentication required for all credit endpoints

## Future Enhancements

1. **Stripe Integration**: Complete payment processing integration
2. **Credit Expiration**: Optional expiration dates for credits
3. **Promotional Credits**: Special non-expiring promotional credit system
4. **Volume Discounts**: Dynamic pricing based on purchase volume
5. **Referral System**: Credits for referring new users
6. **Credit Gifting**: Allow users to gift credits to others
7. **Usage Analytics**: Dashboard showing credit usage patterns
