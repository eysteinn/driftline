package handlers

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/middleware"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/eysteinn/driftline/services/api/internal/utils"
	"github.com/gin-gonic/gin"
)

// GetCreditBalance returns the current credit balance for the authenticated user
func GetCreditBalance(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var balance int
	err := database.DB.QueryRow(
		`SELECT balance FROM user_credits WHERE user_id = $1`,
		userID,
	).Scan(&balance)

	if err == sql.ErrNoRows {
		// User doesn't have a credit record yet, create one with initial balance
		_, err = database.DB.Exec(
			`INSERT INTO user_credits (user_id, balance) VALUES ($1, $2)`,
			userID, 100, // Give new users 100 free credits
		)
		if err != nil {
			log.Printf("Failed to create user_credits for user %s: %v", userID, err)
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to initialize credits")
			return
		}
		balance = 100
	} else if err != nil {
		log.Printf("Database error fetching credit balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, models.CreditBalanceResponse{
		Balance: balance,
	})
}

// GetCreditTransactions returns the transaction history for the authenticated user
func GetCreditTransactions(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	// Get pagination parameters
	page := 1
	pageSize := 50

	rows, err := database.DB.Query(
		`SELECT id, user_id, transaction_type, amount, balance_after, description,
		        mission_id, package_id, stripe_payment_id, stripe_subscription_id,
		        metadata, created_at
		 FROM credit_transactions
		 WHERE user_id = $1
		 ORDER BY created_at DESC
		 LIMIT $2 OFFSET $3`,
		userID, pageSize, (page-1)*pageSize,
	)
	if err != nil {
		log.Printf("Database error fetching transactions: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}
	defer rows.Close()

	var transactions []models.CreditTransaction
	for rows.Next() {
		var t models.CreditTransaction
		err := rows.Scan(
			&t.ID, &t.UserID, &t.TransactionType, &t.Amount, &t.BalanceAfter,
			&t.Description, &t.MissionID, &t.PackageID, &t.StripePaymentID,
			&t.StripeSubscriptionID, &t.Metadata, &t.CreatedAt,
		)
		if err != nil {
			log.Printf("Failed to scan transaction: %v", err)
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to scan transaction")
			return
		}
		transactions = append(transactions, t)
	}

	if transactions == nil {
		transactions = []models.CreditTransaction{}
	}

	utils.PaginatedResponse(c, transactions, len(transactions), page, pageSize)
}

// ListCreditPackages returns available credit packages for purchase
func ListCreditPackages(c *gin.Context) {
	rows, err := database.DB.Query(
		`SELECT id, name, description, credits, price_cents, is_active, sort_order, created_at, updated_at
		 FROM credit_packages
		 WHERE is_active = TRUE
		 ORDER BY sort_order ASC`,
	)
	if err != nil {
		log.Printf("Database error fetching credit packages: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}
	defer rows.Close()

	var packages []models.CreditPackage
	for rows.Next() {
		var p models.CreditPackage
		err := rows.Scan(
			&p.ID, &p.Name, &p.Description, &p.Credits, &p.PriceCents,
			&p.IsActive, &p.SortOrder, &p.CreatedAt, &p.UpdatedAt,
		)
		if err != nil {
			log.Printf("Failed to scan credit package: %v", err)
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to scan package")
			return
		}
		packages = append(packages, p)
	}

	if packages == nil {
		packages = []models.CreditPackage{}
	}

	utils.SuccessResponse(c, http.StatusOK, packages)
}

// PurchaseCredits handles credit package purchases
func PurchaseCredits(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var req models.PurchaseCreditsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	// Get the credit package
	var pkg models.CreditPackage
	err := database.DB.QueryRow(
		`SELECT id, name, description, credits, price_cents, is_active
		 FROM credit_packages WHERE id = $1`,
		req.PackageID,
	).Scan(&pkg.ID, &pkg.Name, &pkg.Description, &pkg.Credits, &pkg.PriceCents, &pkg.IsActive)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Credit package not found")
		return
	} else if err != nil {
		log.Printf("Database error fetching package: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	if !pkg.IsActive {
		utils.ErrorResponse(c, http.StatusBadRequest, "Credit package is not available")
		return
	}

	// TODO: Integrate with Stripe payment processing
	// For now, we'll simulate a successful payment and add credits directly
	// In production, this would:
	// 1. Create a Stripe payment intent
	// 2. Process the payment
	// 3. Only add credits after successful payment

	// Start a transaction
	tx, err := database.DB.Begin()
	if err != nil {
		log.Printf("Failed to start transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
		return
	}
	defer tx.Rollback()

	// Get current balance with row lock
	var currentBalance int
	err = tx.QueryRow(
		`SELECT balance FROM user_credits WHERE user_id = $1 FOR UPDATE`,
		userID,
	).Scan(&currentBalance)

	if err == sql.ErrNoRows {
		// Create credits record if it doesn't exist
		_, err = tx.Exec(
			`INSERT INTO user_credits (user_id, balance) VALUES ($1, $2)`,
			userID, 0,
		)
		if err != nil {
			log.Printf("Failed to create user_credits: %v", err)
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
			return
		}
		currentBalance = 0
	} else if err != nil {
		log.Printf("Failed to get current balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
		return
	}

	// Update balance
	newBalance := currentBalance + pkg.Credits
	_, err = tx.Exec(
		`UPDATE user_credits SET balance = $1 WHERE user_id = $2`,
		newBalance, userID,
	)
	if err != nil {
		log.Printf("Failed to update balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
		return
	}

	// Record transaction
	description := fmt.Sprintf("Purchased %s (%d credits)", pkg.Name, pkg.Credits)
	_, err = tx.Exec(
		`INSERT INTO credit_transactions 
		 (user_id, transaction_type, amount, balance_after, description, package_id)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		userID, "purchase", pkg.Credits, newBalance, description, pkg.ID,
	)
	if err != nil {
		log.Printf("Failed to record transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
		return
	}

	// Commit transaction
	if err = tx.Commit(); err != nil {
		log.Printf("Failed to commit transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to process purchase")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"success":      true,
		"creditsAdded": pkg.Credits,
		"newBalance":   newBalance,
		"message":      description,
	})
}

// AddCredits handles adding credits (for subscriptions or admin operations)
func AddCredits(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var req models.AddCreditsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	// Start a transaction
	tx, err := database.DB.Begin()
	if err != nil {
		log.Printf("Failed to start transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
		return
	}
	defer tx.Rollback()

	// Get current balance with row lock
	var currentBalance int
	err = tx.QueryRow(
		`SELECT balance FROM user_credits WHERE user_id = $1 FOR UPDATE`,
		userID,
	).Scan(&currentBalance)

	if err == sql.ErrNoRows {
		// Create credits record if it doesn't exist
		_, err = tx.Exec(
			`INSERT INTO user_credits (user_id, balance) VALUES ($1, $2)`,
			userID, 0,
		)
		if err != nil {
			log.Printf("Failed to create user_credits: %v", err)
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
			return
		}
		currentBalance = 0
	} else if err != nil {
		log.Printf("Failed to get current balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
		return
	}

	// Update balance
	newBalance := currentBalance + req.Amount
	_, err = tx.Exec(
		`UPDATE user_credits SET balance = $1 WHERE user_id = $2`,
		newBalance, userID,
	)
	if err != nil {
		log.Printf("Failed to update balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
		return
	}

	// Record transaction
	_, err = tx.Exec(
		`INSERT INTO credit_transactions 
		 (user_id, transaction_type, amount, balance_after, description)
		 VALUES ($1, $2, $3, $4, $5)`,
		userID, "subscription_grant", req.Amount, newBalance, req.Description,
	)
	if err != nil {
		log.Printf("Failed to record transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
		return
	}

	// Commit transaction
	if err = tx.Commit(); err != nil {
		log.Printf("Failed to commit transaction: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to add credits")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"success":      true,
		"creditsAdded": req.Amount,
		"newBalance":   newBalance,
	})
}

// DeductCredits deducts credits from a user's balance
// Returns the new balance or an error if insufficient credits
func DeductCredits(userID string, amount int, description string, missionID *string) (int, error) {
	// Start a transaction
	tx, err := database.DB.Begin()
	if err != nil {
		return 0, fmt.Errorf("failed to start transaction: %w", err)
	}
	defer tx.Rollback()

	// Get current balance with row lock
	var currentBalance int
	err = tx.QueryRow(
		`SELECT balance FROM user_credits WHERE user_id = $1 FOR UPDATE`,
		userID,
	).Scan(&currentBalance)

	if err == sql.ErrNoRows {
		return 0, fmt.Errorf("user credit record not found")
	} else if err != nil {
		return 0, fmt.Errorf("failed to get current balance: %w", err)
	}

	// Check if user has sufficient credits
	if currentBalance < amount {
		return 0, fmt.Errorf("insufficient credits: have %d, need %d", currentBalance, amount)
	}

	// Update balance
	newBalance := currentBalance - amount
	_, err = tx.Exec(
		`UPDATE user_credits SET balance = $1 WHERE user_id = $2`,
		newBalance, userID,
	)
	if err != nil {
		return 0, fmt.Errorf("failed to update balance: %w", err)
	}

	// Record transaction (negative amount for deduction)
	_, err = tx.Exec(
		`INSERT INTO credit_transactions 
		 (user_id, transaction_type, amount, balance_after, description, mission_id)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		userID, "deduction", -amount, newBalance, description, missionID,
	)
	if err != nil {
		return 0, fmt.Errorf("failed to record transaction: %w", err)
	}

	// Commit transaction
	if err = tx.Commit(); err != nil {
		return 0, fmt.Errorf("failed to commit transaction: %w", err)
	}

	return newBalance, nil
}
