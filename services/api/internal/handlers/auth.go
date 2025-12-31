package handlers

import (
	"database/sql"
	"net/http"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
)

// Register handles user registration
func Register(c *gin.Context) {
	var req models.CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Hash the password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
		return
	}

	// Insert user into database
	var userID string
	err = database.DB.QueryRow(
		`INSERT INTO users (email, hashed_password, full_name, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5)
		 RETURNING id`,
		req.Email, string(hashedPassword), req.FullName, time.Now(), time.Now(),
	).Scan(&userID)

	if err != nil {
		// TODO: Use proper error type checking with pq package
		// This is a temporary solution checking error message string
		if err.Error() == "pq: duplicate key value violates unique constraint \"users_email_key\"" {
			c.JSON(http.StatusConflict, gin.H{"error": "Email already registered"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": "User created successfully",
		"user_id": userID,
	})
}

// Login handles user authentication
func Login(c *gin.Context) {
	var req models.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Query user from database
	var user models.User
	err := database.DB.QueryRow(
		`SELECT id, email, hashed_password, full_name, is_active, is_verified, role, created_at, updated_at
		 FROM users WHERE email = $1`,
		req.Email,
	).Scan(&user.ID, &user.Email, &user.HashedPassword, &user.FullName, &user.IsActive, &user.IsVerified, &user.Role, &user.CreatedAt, &user.UpdatedAt)

	if err == sql.ErrNoRows {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}

	// Check if user is active
	if !user.IsActive {
		c.JSON(http.StatusForbidden, gin.H{"error": "Account is inactive"})
		return
	}

	// Verify password
	err = bcrypt.CompareHashAndPassword([]byte(user.HashedPassword), []byte(req.Password))
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
		return
	}

	// TODO: Generate JWT token with proper signing and expiration
	// This is a placeholder for initial testing - MUST be replaced with real JWT implementation
	// For production: use github.com/golang-jwt/jwt or similar library
	token := "placeholder-jwt-token"

	c.JSON(http.StatusOK, models.LoginResponse{
		Token: token,
		User:  user,
	})
}
