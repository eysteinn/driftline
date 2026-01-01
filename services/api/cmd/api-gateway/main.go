package main

import (
	"log"
	"os"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/handlers"
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

	// Initialize Gin router
	router := gin.Default()

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "healthy",
			"service": "driftline-api",
		})
	})

	// API version 1 routes
	v1 := router.Group("/v1")
	{
		// Auth routes
		v1.POST("/auth/register", handlers.Register)
		v1.POST("/auth/login", handlers.Login)

		// Mission routes
		v1.POST("/missions", handlers.CreateMission)
		v1.GET("/missions", handlers.ListMissions)
		v1.GET("/missions/:id", handlers.GetMission)
	}

	// Start server
	log.Printf("Starting Driftline API server on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
