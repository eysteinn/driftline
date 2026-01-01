package models

import (
	"time"
)

// User represents a user in the system
type User struct {
	ID             string    `json:"id" db:"id"`
	Email          string    `json:"email" db:"email"`
	HashedPassword string    `json:"-" db:"hashed_password"`
	FullName       string    `json:"full_name" db:"full_name"`
	IsActive       bool      `json:"is_active" db:"is_active"`
	IsVerified     bool      `json:"is_verified" db:"is_verified"`
	Role           string    `json:"role" db:"role"`
	CreatedAt      time.Time `json:"created_at" db:"created_at"`
	UpdatedAt      time.Time `json:"updated_at" db:"updated_at"`
}

// CreateUserRequest represents a user registration request
type CreateUserRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required,min=8"`
	FullName string `json:"full_name"`
}

// LoginRequest represents a login request
type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// LoginResponse represents a login response with JWT token
type LoginResponse struct {
	Token string `json:"token"`
	User  User   `json:"user"`
}
