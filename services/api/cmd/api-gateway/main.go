package main

import (
	"log"
	"os"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/handlers"
	"github.com/eysteinn/driftline/services/api/internal/middleware"
	"github.com/eysteinn/driftline/services/api/internal/queue"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	// Get configuration from environment
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// Connect to database
	if err := database.Connect(); err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer database.Close()

	// Connect to Redis
	if err := queue.Connect(); err != nil {
		log.Fatal("Failed to connect to Redis:", err)
	}
	defer queue.Close()

	// Start background job to cleanup expired API keys
	go func() {
		ticker := time.NewTicker(1 * time.Hour)
		defer ticker.Stop()

		// Run cleanup immediately on startup
		if err := handlers.CleanupExpiredApiKeys(); err != nil {
			log.Printf("Failed to cleanup expired API keys: %v", err)
		}

		// Then run periodically
		for range ticker.C {
			if err := handlers.CleanupExpiredApiKeys(); err != nil {
				log.Printf("Failed to cleanup expired API keys: %v", err)
			}
		}
	}()

	// Initialize Gin router
	router := gin.Default()

	// Configure CORS - Allow all origins in development
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowAllOrigins = true
	// For production, use specific origins instead:
	// corsConfig.AllowOrigins = []string{
	// 	"http://localhost:3000",
	// 	"http://localhost:5173",
	// 	"http://localhost",
	// 	"http://127.0.0.1:3000",
	// 	"http://127.0.0.1:5173",
	// 	"http://127.0.0.1",
	// }
	corsConfig.AllowCredentials = true
	corsConfig.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	corsConfig.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
	router.Use(cors.New(corsConfig))

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "healthy",
			"service": "driftline-api",
		})
	})

	// API version 1 routes
	v1 := router.Group("/api/v1")
	{
		// Public auth routes
		auth := v1.Group("/auth")
		{
			auth.POST("/register", handlers.Register)
			auth.POST("/login", handlers.Login)
			auth.POST("/logout", handlers.Logout)
		}

		// Protected user routes
		users := v1.Group("/users")
		users.Use(middleware.AuthMiddleware())
		{
			users.GET("/me", handlers.GetCurrentUser)
			users.PATCH("/me", handlers.UpdateCurrentUser)

			// API key routes under /users/me/api-keys
			users.GET("/me/api-keys", handlers.ListApiKeys)
			users.POST("/me/api-keys", handlers.CreateApiKey)
			users.DELETE("/me/api-keys/:id", handlers.DeleteApiKey)
		}

		// Protected mission routes
		missions := v1.Group("/missions")
		missions.Use(middleware.AuthMiddleware())
		{
			missions.POST("", handlers.CreateMission)
			missions.GET("", handlers.ListMissions)
			missions.GET("/:id", handlers.GetMission)
			missions.DELETE("/:id", handlers.DeleteMission)
			missions.GET("/:id/status", handlers.GetMissionStatus)
			missions.GET("/:id/results", handlers.GetMissionResults)
			missions.GET("/:id/results/download", handlers.DownloadMissionResults)
		}

		// Protected credit routes
		credits := v1.Group("/credits")
		credits.Use(middleware.AuthMiddleware())
		{
			credits.GET("/balance", handlers.GetCreditBalance)
			credits.GET("/transactions", handlers.GetCreditTransactions)
			credits.GET("/packages", handlers.ListCreditPackages)
			credits.POST("/purchase", handlers.PurchaseCredits)
			credits.POST("/add", handlers.AddCredits)
		}
	}

	// Start server
	log.Printf("Starting Driftline API server on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
