package main

import (
	"log"
	"os"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/cache"
	"github.com/eysteinn/driftline/services/data-service/internal/handlers"
	"github.com/eysteinn/driftline/services/data-service/internal/services"
	"github.com/eysteinn/driftline/services/data-service/internal/storage"
	"github.com/gin-gonic/gin"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// Initialize cache service
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/1"
	}
	
	cacheService, err := cache.NewService(redisURL, 24*time.Hour)
	if err != nil {
		log.Printf("Warning: Failed to initialize cache service: %v", err)
		log.Printf("Continuing without cache...")
		cacheService = nil
	} else {
		defer cacheService.Close()
		log.Printf("Cache service initialized successfully")
	}

	// Initialize storage service
	s3Endpoint := os.Getenv("S3_ENDPOINT")
	s3AccessKey := os.Getenv("S3_ACCESS_KEY")
	s3SecretKey := os.Getenv("S3_SECRET_KEY")
	
	if s3Endpoint == "" {
		s3Endpoint = "http://localhost:9000"
	}
	if s3AccessKey == "" {
		s3AccessKey = "minioadmin"
	}
	if s3SecretKey == "" {
		s3SecretKey = "minioadmin"
	}
	
	storageService, err := storage.NewService(s3Endpoint, s3AccessKey, s3SecretKey)
	if err != nil {
		log.Printf("Warning: Failed to initialize storage service: %v", err)
		log.Printf("Continuing without storage...")
		storageService = nil
	} else {
		log.Printf("Storage service initialized successfully")
	}

	// Initialize data service
	var dataService *services.DataService
	if cacheService != nil && storageService != nil {
		dataService = services.NewDataService(cacheService, storageService)
		log.Printf("Data service initialized successfully")
	} else {
		log.Printf("Warning: Running without full data service capabilities")
	}

	// Initialize handlers
	var dataHandler *handlers.DataHandler
	if dataService != nil {
		dataHandler = handlers.NewDataHandler(dataService)
	}

	// Set up router
	router := gin.Default()

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "healthy",
			"service": "driftline-data-service",
			"cache":   cacheService != nil,
			"storage": storageService != nil,
		})
	})

	// API v1 endpoints
	v1 := router.Group("/v1")
	{
		if dataHandler != nil {
			v1.GET("/data/ocean-currents", dataHandler.GetOceanCurrents)
			v1.GET("/data/wind", dataHandler.GetWind)
			v1.GET("/data/waves", dataHandler.GetWaves)
		} else {
			// Fallback handlers if services are not available
			v1.GET("/data/ocean-currents", func(c *gin.Context) {
				c.JSON(503, gin.H{"error": "Service unavailable - cache or storage not initialized"})
			})
			v1.GET("/data/wind", func(c *gin.Context) {
				c.JSON(503, gin.H{"error": "Service unavailable - cache or storage not initialized"})
			})
			v1.GET("/data/waves", func(c *gin.Context) {
				c.JSON(503, gin.H{"error": "Service unavailable - cache or storage not initialized"})
			})
		}
	}

	log.Printf("Starting Data Service on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
