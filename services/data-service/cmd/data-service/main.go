package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	router := gin.Default()

	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "healthy",
			"service": "driftline-data-service",
		})
	})

	// Data endpoints
	v1 := router.Group("/v1")
	{
		v1.GET("/data/ocean-currents", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Ocean currents data endpoint - not implemented yet"})
		})
		v1.GET("/data/wind", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Wind data endpoint - not implemented yet"})
		})
		v1.GET("/data/waves", func(c *gin.Context) {
			c.JSON(501, gin.H{"message": "Wave data endpoint - not implemented yet"})
		})
	}

	log.Printf("Starting Data Service on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
