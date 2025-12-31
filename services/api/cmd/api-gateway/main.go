package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
)

func main() {
	// Get configuration from environment
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// Initialize Gin router
	router := gin.Default()

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "healthy",
			"service": "driftline-api",
		})
	})

	// API version 1 routes
	v1 := router.Group("/v1")
	{
		// Auth routes
		v1.POST("/auth/register", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Not implemented yet"})
		})
		v1.POST("/auth/login", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Not implemented yet"})
		})

		// Mission routes
		v1.POST("/missions", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Not implemented yet"})
		})
		v1.GET("/missions", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Not implemented yet"})
		})
		v1.GET("/missions/:id", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Not implemented yet"})
		})
	}

	// Start server
	log.Printf("Starting Driftline API server on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
