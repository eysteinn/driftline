package models

import (
	"time"
)

// ApiKey represents an API key in the system
type ApiKey struct {
	ID          string     `json:"id" db:"id"`
	UserID      string     `json:"userId" db:"user_id"`
	KeyHash     string     `json:"-" db:"key_hash"`
	Name        string     `json:"name" db:"name"`
	Scopes      []byte     `json:"scopes" db:"scopes"`
	IsActive    bool       `json:"isActive" db:"is_active"`
	LastUsedAt  *time.Time `json:"lastUsedAt,omitempty" db:"last_used_at"`
	CreatedAt   time.Time  `json:"createdAt" db:"created_at"`
	ExpiresAt   *time.Time `json:"expiresAt,omitempty" db:"expires_at"`
	KeyPreview  string     `json:"keyPreview" db:"-"`
}

// CreateApiKeyRequest represents a request to create an API key
type CreateApiKeyRequest struct {
	Name           string   `json:"name" binding:"required"`
	Scopes         []string `json:"scopes"`
	ExpiresInDays  *int     `json:"expiresInDays"` // null means never expires
}

// CreateApiKeyResponse represents the response when creating an API key
type CreateApiKeyResponse struct {
	Key    string `json:"key"`
	ApiKey ApiKey `json:"apiKey"`
}
