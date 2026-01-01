package handlers

import (
	"database/sql"
	"net/http"
	"strconv"
	"time"

	"github.com/eysteinn/driftline/services/api/internal/database"
	"github.com/eysteinn/driftline/services/api/internal/middleware"
	"github.com/eysteinn/driftline/services/api/internal/models"
	"github.com/eysteinn/driftline/services/api/internal/queue"
	"github.com/eysteinn/driftline/services/api/internal/utils"
	"github.com/gin-gonic/gin"
)

// CreateMission handles creating a new drift forecast mission
func CreateMission(c *gin.Context) {
	var req models.CreateMissionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.ErrorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	// Get user ID from JWT token
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	// Set defaults
	if req.EnsembleSize == 0 {
		req.EnsembleSize = 1000
	}

	// Insert mission into database
	var mission models.Mission
	err := database.DB.QueryRow(
		`INSERT INTO missions (
			user_id, name, description, last_known_lat, last_known_lon, 
			last_known_time, object_type, uncertainty_radius_m, 
			forecast_hours, ensemble_size, status, created_at, updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
		RETURNING id, user_id, name, description, last_known_lat, last_known_lon,
		          last_known_time, object_type, uncertainty_radius_m, forecast_hours,
		          ensemble_size, config, status, job_id, error_message,
		          created_at, updated_at, completed_at`,
		userID, req.Name, req.Description, req.LastKnownLat, req.LastKnownLon,
		req.LastKnownTime, req.ObjectType, req.UncertaintyRadiusM,
		req.ForecastHours, req.EnsembleSize, "created", time.Now(), time.Now(),
	).Scan(
		&mission.ID, &mission.UserID, &mission.Name, &mission.Description, &mission.LastKnownLat, &mission.LastKnownLon,
		&mission.LastKnownTime, &mission.ObjectType, &mission.UncertaintyRadiusM, &mission.ForecastHours,
		&mission.EnsembleSize, &mission.Config, &mission.Status, &mission.JobID, &mission.ErrorMessage,
		&mission.CreatedAt, &mission.UpdatedAt, &mission.CompletedAt,
	)

	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to create mission")
		return
	}

	// Enqueue job to Redis for processing
	objectTypeInt := 1 // Default to Person-in-water
	if req.ObjectType != "" {
		// Try to parse as integer
		if val, err := strconv.Atoi(req.ObjectType); err == nil {
			objectTypeInt = val
		}
	}

	jobParams := queue.DriftJobParams{
		Latitude:      req.LastKnownLat,
		Longitude:     req.LastKnownLon,
		StartTime:     req.LastKnownTime.Format(time.RFC3339),
		DurationHours: req.ForecastHours,
		NumParticles:  req.EnsembleSize,
		ObjectType:    objectTypeInt,
	}

	if err := queue.EnqueueDriftJob(mission.ID, jobParams); err != nil {
		// Log the error but don't fail the mission creation
		// The mission is already in the database with status "created"
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to enqueue job for processing")
		return
	}

	// Update mission status to "queued"
	_, err = database.DB.Exec(
		`UPDATE missions SET status = $1, updated_at = $2 WHERE id = $3`,
		"queued", time.Now(), mission.ID,
	)
	if err != nil {
		// Log the error but don't fail - the job is already queued
		// The worker will update the status when it picks up the job
	} else {
		mission.Status = "queued"
		mission.UpdatedAt = time.Now()
	}

	utils.SuccessResponse(c, http.StatusCreated, mission)
}

// ListMissions handles listing missions for the current user
func ListMissions(c *gin.Context) {
	// Get user ID from JWT token
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
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
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
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
			utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to scan mission")
			return
		}
		missions = append(missions, m)
	}

	utils.PaginatedResponse(c, missions, len(missions), 1, 50)
}

// GetMission handles getting a specific mission by ID
func GetMission(c *gin.Context) {
	missionID := c.Param("id")
	
	// Get user ID from JWT and verify ownership
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var m models.Mission
	err := database.DB.QueryRow(
		`SELECT id, user_id, name, description, last_known_lat, last_known_lon,
		        last_known_time, object_type, uncertainty_radius_m, forecast_hours,
		        ensemble_size, config, status, job_id, error_message,
		        created_at, updated_at, completed_at
		 FROM missions
		 WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	).Scan(
		&m.ID, &m.UserID, &m.Name, &m.Description, &m.LastKnownLat, &m.LastKnownLon,
		&m.LastKnownTime, &m.ObjectType, &m.UncertaintyRadiusM, &m.ForecastHours,
		&m.EnsembleSize, &m.Config, &m.Status, &m.JobID, &m.ErrorMessage,
		&m.CreatedAt, &m.UpdatedAt, &m.CompletedAt,
	)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Mission not found")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, m)
}

// DeleteMission handles deleting a mission
func DeleteMission(c *gin.Context) {
	missionID := c.Param("id")
	
	// Get user ID from JWT and verify ownership
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	result, err := database.DB.Exec(
		`DELETE FROM missions WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	)
	if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to delete mission")
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil || rowsAffected == 0 {
		utils.ErrorResponse(c, http.StatusNotFound, "Mission not found")
		return
	}

	c.JSON(http.StatusNoContent, nil)
}

// GetMissionStatus handles getting the status of a mission
func GetMissionStatus(c *gin.Context) {
	missionID := c.Param("id")
	
	// Get user ID from JWT and verify ownership
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	var status string
	err := database.DB.QueryRow(
		`SELECT status FROM missions WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	).Scan(&status)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Mission not found")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, gin.H{
		"status": status,
	})
}

// GetMissionResults handles getting the results of a completed mission
func GetMissionResults(c *gin.Context) {
	missionID := c.Param("id")
	
	// Get user ID from JWT and verify ownership
	userID, ok := middleware.GetUserID(c)
	if !ok {
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	// First verify mission ownership
	var missionStatus string
	err := database.DB.QueryRow(
		`SELECT status FROM missions WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	).Scan(&missionStatus)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Mission not found")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	// Check if mission is completed
	if missionStatus != "completed" {
		utils.ErrorResponse(c, http.StatusBadRequest, "Mission is not completed yet")
		return
	}

	// Get results
	var result models.MissionResult
	err = database.DB.QueryRow(
		`SELECT id, mission_id, centroid_lat, centroid_lon, centroid_time,
		        search_area_50_geom, search_area_90_geom, netcdf_path,
		        geojson_path, pdf_report_path, particle_count, stranded_count,
		        computation_time_seconds, created_at
		 FROM mission_results WHERE mission_id = $1`,
		missionID,
	).Scan(
		&result.ID, &result.MissionID, &result.CentroidLat, &result.CentroidLon,
		&result.CentroidTime, &result.SearchArea50Geom, &result.SearchArea90Geom,
		&result.NetcdfPath, &result.GeojsonPath, &result.PdfReportPath,
		&result.ParticleCount, &result.StrandedCount, &result.ComputationTimeSeconds,
		&result.CreatedAt,
	)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Results not found")
		return
	} else if err != nil {
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, result)
}
