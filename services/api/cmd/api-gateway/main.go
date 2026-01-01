package main

import (
	"log"
	"os"

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

	// Initialize Gin router
	router := gin.Default()

	// Configure CORS
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowOrigins = []string{"http://localhost:3000", "http://localhost:5173"}
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
		}
	}

	// Start server
	log.Printf("Starting Driftline API server on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
