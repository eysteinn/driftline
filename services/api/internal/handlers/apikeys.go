package handlers

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/middleware"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/eysteinn/driftline/services/api/internal/utils"
	"github.com/gin-gonic/gin"
)

// generateApiKey generates a secure random API key
func generateApiKey() (string, error) {
	b := make([]byte, 32)
	_, err := rand.Read(b)
	if err != nil {
		return "", err
	}
	return base64.URLEncoding.EncodeToString(b), nil
}

// hashApiKey creates a SHA256 hash of the API key
func hashApiKey(key string) string {
	hash := sha256.Sum256([]byte(key))
	return fmt.Sprintf("%x", hash)
}

// createKeyPreview creates a preview string showing first and last 4 chars
func createKeyPreview(key string) string {
	if len(key) < 12 {
		return key
	}
	return key[:4] + "..." + key[len(key)-4:]
}

// ListApiKeys returns all API keys for the authenticated user
func ListApiKeys(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	rows, err := database.DB.Query(
		`SELECT id, user_id, key_hash, key_preview, name, scopes, is_active, last_used_at, created_at, expires_at
		 FROM api_keys
		 WHERE user_id = $1
		 ORDER BY created_at DESC`,
		userID,
	)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to fetch API keys")
		return
	}
	defer rows.Close()

	var apiKeys []models.ApiKey
	for rows.Next() {
		var key models.ApiKey
		var scopesJSON []byte
		err := rows.Scan(
			&key.ID, &key.UserID, &key.KeyHash, &key.KeyPreview, &key.Name, &scopesJSON,
			&key.IsActive, &key.LastUsedAt, &key.CreatedAt, &key.ExpiresAt,
		)
		if err != nil {
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to scan API key")
			return
		}

		apiKeys = append(apiKeys, key)
	}

	if apiKeys == nil {
		apiKeys = []models.ApiKey{}
	}

	utils.SuccessResponse(c, http.StatusOK, apiKeys)
}

// CreateApiKey creates a new API key for the authenticated user
func CreateApiKey(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var req models.CreateApiKeyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	// Generate a new API key
	apiKey, err := generateApiKey()
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to generate API key")
		return
	}

	// Create preview and hash for storage
	keyPreview := createKeyPreview(apiKey)
	keyHash := hashApiKey(apiKey)

	// Calculate expiration date if specified
	var expiresAt *time.Time
	if req.ExpiresInDays != nil {
		if *req.ExpiresInDays <= 0 {
			utils.ErrorResponse(c, http.StatusBadRequest, "ExpiresInDays must be positive or nil for no expiration")
			return
		}
		expiry := time.Now().AddDate(0, 0, *req.ExpiresInDays)
		expiresAt = &expiry
	}

	// Convert scopes to JSONB
	var scopesJSON []byte
	if req.Scopes != nil && len(req.Scopes) > 0 {
		scopesJSON, err = json.Marshal(req.Scopes)
		if err != nil {
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to encode scopes")
			return
		}
	}

	// Insert into database
	var keyID string
	var createdAt time.Time
	err = database.DB.QueryRow(
		`INSERT INTO api_keys (user_id, key_hash, key_preview, name, scopes, created_at, expires_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7)
		 RETURNING id, created_at`,
		userID, keyHash, keyPreview, req.Name, scopesJSON, time.Now(), expiresAt,
	).Scan(&keyID, &createdAt)

	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to create API key")
		return
	}

	// Return the API key (only time it will be shown)
	response := models.CreateApiKeyResponse{
		Key: apiKey,
		ApiKey: models.ApiKey{
			ID:         keyID,
			UserID:     userID,
			Name:       req.Name,
			KeyPreview: keyPreview,
			IsActive:   true,
			CreatedAt:  createdAt,
			ExpiresAt:  expiresAt,
		},
	}

	utils.SuccessResponse(c, http.StatusCreated, response)
}

// DeleteApiKey deletes an API key
func DeleteApiKey(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	keyID := c.Param("id")

	// Verify the key belongs to the user and delete it
	result, err := database.DB.Exec(
		`DELETE FROM api_keys WHERE id = $1 AND user_id = $2`,
		keyID, userID,
	)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to delete API key")
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to verify deletion")
		return
	}

	if rowsAffected == 0 {
		utils.ErrorResponse(c, http.StatusNotFound, "API key not found")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"message": "API key deleted successfully",
	})
}

// CleanupExpiredApiKeys removes expired API keys from the database
// This function should be called periodically (e.g., via a cron job)
func CleanupExpiredApiKeys() error {
	result, err := database.DB.Exec(
		`DELETE FROM api_keys WHERE expires_at IS NOT NULL AND expires_at < NOW()`,
	)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected > 0 {
		fmt.Printf("Cleaned up %d expired API keys\n", rowsAffected)
	}

	return nil
}
