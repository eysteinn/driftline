package handlers

import (
	"database/sql"
	"net/http"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/middleware"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/eysteinn/driftline/services/api/internal/utils"
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
			utils.ErrorResponse(c, http.StatusConflict, "Email already registered")
			return
		}
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to create user")
		return
	}

	// Fetch the created user
	var user models.User
	err = database.DB.QueryRow(
		`SELECT id, email, hashed_password, full_name, is_active, is_verified, role, created_at, updated_at
		 FROM users WHERE id = $1`,
		userID,
	).Scan(&user.ID, &user.Email, &user.HashedPassword, &user.FullName, &user.IsActive, &user.IsVerified, &user.Role, &user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to retrieve user")
		return
	}

	// Generate JWT tokens
	accessToken, refreshToken, err := utils.GenerateTokenPair(user.ID, user.Email)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to generate tokens")
		return
	}

	utils.SuccessResponse(c, http.StatusCreated, gin.H{
		"accessToken":  accessToken,
		"refreshToken": refreshToken,
		"user":         user,
	})
}

// Login handles user authentication
func Login(c *gin.Context) {
	var req models.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
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
		utils.ErrorResponse(c, http.StatusUnauthorized, "Invalid email or password")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	// Check if user is active
	if !user.IsActive {
		utils.ErrorResponse(c, http.StatusForbidden, "Account is inactive")
		return
	}

	// Verify password
	err = bcrypt.CompareHashAndPassword([]byte(user.HashedPassword), []byte(req.Password))
	if err != nil {
		utils.ErrorResponse(c, http.StatusUnauthorized, "Invalid email or password")
		return
	}

	// Generate JWT tokens
	accessToken, refreshToken, err := utils.GenerateTokenPair(user.ID, user.Email)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to generate tokens")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"accessToken":  accessToken,
		"refreshToken": refreshToken,
		"user":         user,
	})
}

// Logout handles user logout (currently a no-op as JWT is stateless)
func Logout(c *gin.Context) {
	// In a stateless JWT system, logout is handled client-side
	// For stateful sessions, we would invalidate the token here
	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"message": "Logged out successfully",
	})
}

// GetCurrentUser returns the currently authenticated user
func GetCurrentUser(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var user models.User
	err := database.DB.QueryRow(
		`SELECT id, email, hashed_password, full_name, is_active, is_verified, role, created_at, updated_at
		 FROM users WHERE id = $1`,
		userID,
	).Scan(&user.ID, &user.Email, &user.HashedPassword, &user.FullName, &user.IsActive, &user.IsVerified, &user.Role, &user.CreatedAt, &user.UpdatedAt)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "User not found")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, user)
}

// UpdateCurrentUser updates the currently authenticated user
func UpdateCurrentUser(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var req struct {
		FullName string `json:"fullName"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	// Update user
	_, err := database.DB.Exec(
		`UPDATE users SET full_name = $1, updated_at = $2 WHERE id = $3`,
		req.FullName, time.Now(), userID,
	)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to update user")
		return
	}

	// Fetch updated user
	var user models.User
	err = database.DB.QueryRow(
		`SELECT id, email, hashed_password, full_name, is_active, is_verified, role, created_at, updated_at
		 FROM users WHERE id = $1`,
		userID,
	).Scan(&user.ID, &user.Email, &user.HashedPassword, &user.FullName, &user.IsActive, &user.IsVerified, &user.Role, &user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to retrieve user")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, user)
}
