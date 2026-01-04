package models

import (
	"time"
)

// UserCredit represents a user's credit balance
type UserCredit struct {
	ID        string    `json:"id" db:"id"`
	UserID    string    `json:"userId" db:"user_id"`
	Balance   int       `json:"balance" db:"balance"`
	CreatedAt time.Time `json:"createdAt" db:"created_at"`
	UpdatedAt time.Time `json:"updatedAt" db:"updated_at"`
}

// CreditTransaction represents a credit transaction (purchase, deduction, refund)
type CreditTransaction struct {
	ID                   string     `json:"id" db:"id"`
	UserID               string     `json:"userId" db:"user_id"`
	TransactionType      string     `json:"transactionType" db:"transaction_type"`
	Amount               int        `json:"amount" db:"amount"`
	BalanceAfter         int        `json:"balanceAfter" db:"balance_after"`
	Description          string     `json:"description" db:"description"`
	MissionID            *string    `json:"missionId,omitempty" db:"mission_id"`
	PackageID            *string    `json:"packageId,omitempty" db:"package_id"`
	StripePaymentID      *string    `json:"stripePaymentId,omitempty" db:"stripe_payment_id"`
	StripeSubscriptionID *string    `json:"stripeSubscriptionId,omitempty" db:"stripe_subscription_id"`
	Metadata             *string    `json:"metadata,omitempty" db:"metadata"`
	CreatedAt            time.Time  `json:"createdAt" db:"created_at"`
}

// CreditPackage represents a purchasable credit package
type CreditPackage struct {
	ID          string    `json:"id" db:"id"`
	Name        string    `json:"name" db:"name"`
	Description string    `json:"description" db:"description"`
	Credits     int       `json:"credits" db:"credits"`
	PriceCents  int       `json:"priceCents" db:"price_cents"`
	IsActive    bool      `json:"isActive" db:"is_active"`
	SortOrder   int       `json:"sortOrder" db:"sort_order"`
	CreatedAt   time.Time `json:"createdAt" db:"created_at"`
	UpdatedAt   time.Time `json:"updatedAt" db:"updated_at"`
}

// PurchaseCreditsRequest represents a request to purchase credits
type PurchaseCreditsRequest struct {
	PackageID       string  `json:"packageId" binding:"required"`
	PaymentMethodID *string `json:"paymentMethodId"`
}

// AddCreditsRequest represents a request to add credits (admin/subscription)
type AddCreditsRequest struct {
	Amount      int    `json:"amount" binding:"required,min=1"`
	Description string `json:"description" binding:"required"`
}

// CreditBalanceResponse represents the response for credit balance
type CreditBalanceResponse struct {
	Balance int `json:"balance"`
}

// TransactionListResponse represents a paginated list of transactions
type TransactionListResponse struct {
	Transactions []CreditTransaction `json:"transactions"`
	Total        int                 `json:"total"`
	Page         int                 `json:"page"`
	PageSize     int                 `json:"pageSize"`
}
