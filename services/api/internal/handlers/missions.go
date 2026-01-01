package handlers

import (
	"net/http"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/gin-gonic/gin"
)

// CreateMission handles creating a new drift forecast mission
func CreateMission(c *gin.Context) {
	var req models.CreateMissionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// TODO: Get user ID from JWT token in authorization header
	// SECURITY WARNING: This is a temporary workaround for testing only!
	// In production, this MUST extract user ID from a validated JWT token
	// Using the first user from the database is NOT secure and allows unauthorized access
	var userID string
	err := database.DB.QueryRow("SELECT id FROM users LIMIT 1").Scan(&userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "No user found"})
		return
	}

	// Set defaults
	if req.EnsembleSize == 0 {
		req.EnsembleSize = 1000
	}

	// Insert mission into database
	var missionID string
	err = database.DB.QueryRow(
		`INSERT INTO missions (
			user_id, name, description, last_known_lat, last_known_lon, 
			last_known_time, object_type, uncertainty_radius_m, 
			forecast_hours, ensemble_size, status, created_at, updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
		RETURNING id`,
		userID, req.Name, req.Description, req.LastKnownLat, req.LastKnownLon,
		req.LastKnownTime, req.ObjectType, req.UncertaintyRadiusM,
		req.ForecastHours, req.EnsembleSize, "created", time.Now(), time.Now(),
	).Scan(&missionID)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create mission"})
		return
	}

	// TODO: Enqueue job to Redis for processing

	c.JSON(http.StatusCreated, gin.H{
		"message":    "Mission created successfully",
		"mission_id": missionID,
		"status":     "created",
	})
}

// ListMissions handles listing missions for the current user
func ListMissions(c *gin.Context) {
	// TODO: Get user ID from JWT token
	// SECURITY WARNING: This is a temporary workaround for testing only!
	// In production, this MUST extract user ID from a validated JWT token
	var userID string
	err := database.DB.QueryRow("SELECT id FROM users LIMIT 1").Scan(&userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "No user found"})
		return
	}

	rows, err := database.DB.Query(
		`SELECT id, user_id, name, description, last_known_lat, last_known_lon,
		        last_known_time, object_type, uncertainty_radius_m, forecast_hours,
		        ensemble_size, config, status, job_id, error_message,
		        created_at, updated_at, completed_at
		 FROM missions
		 WHERE user_id = $1
		 ORDER BY created_at DESC
		 LIMIT 50`,
		userID,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}
	defer rows.Close()

	var missions []models.Mission
	for rows.Next() {
		var m models.Mission
		err := rows.Scan(
			&m.ID, &m.UserID, &m.Name, &m.Description, &m.LastKnownLat, &m.LastKnownLon,
			&m.LastKnownTime, &m.ObjectType, &m.UncertaintyRadiusM, &m.ForecastHours,
			&m.EnsembleSize, &m.Config, &m.Status, &m.JobID, &m.ErrorMessage,
			&m.CreatedAt, &m.UpdatedAt, &m.CompletedAt,
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to scan mission"})
			return
		}
		missions = append(missions, m)
	}

	c.JSON(http.StatusOK, models.MissionListResponse{
		Missions: missions,
		Total:    len(missions),
		Page:     1,
		PageSize: 50,
	})
}

// GetMission handles getting a specific mission by ID
func GetMission(c *gin.Context) {
	missionID := c.Param("id")
	// TODO: Get user ID from JWT and verify ownership
	// SECURITY WARNING: Currently allows access to any mission without authorization
	// In production, must verify the mission belongs to the authenticated user

	var m models.Mission
	err := database.DB.QueryRow(
		`SELECT id, user_id, name, description, last_known_lat, last_known_lon,
		        last_known_time, object_type, uncertainty_radius_m, forecast_hours,
		        ensemble_size, config, status, job_id, error_message,
		        created_at, updated_at, completed_at
		 FROM missions
		 WHERE id = $1`,
		missionID,
	).Scan(
		&m.ID, &m.UserID, &m.Name, &m.Description, &m.LastKnownLat, &m.LastKnownLon,
		&m.LastKnownTime, &m.ObjectType, &m.UncertaintyRadiusM, &m.ForecastHours,
		&m.EnsembleSize, &m.Config, &m.Status, &m.JobID, &m.ErrorMessage,
		&m.CreatedAt, &m.UpdatedAt, &m.CompletedAt,
	)

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Mission not found"})
		return
	}

	c.JSON(http.StatusOK, m)
}
