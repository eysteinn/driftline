package handlers

import (
	"database/sql"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
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

	// Calculate credit cost based on mission parameters
	// Base cost: 10 credits
	// Additional cost: 1 credit per 24 hours of forecast
	// Additional cost: 1 credit per 1000 particles beyond 1000
	creditsCost := 10
	creditsCost += (req.ForecastHours + 23) / 24 // Round up hours to days
	if req.EnsembleSize > 1000 {
		creditsCost += (req.EnsembleSize - 1000) / 1000
	}

	// Check if user has sufficient credits
	var currentBalance int
	err := database.DB.QueryRow(
		`SELECT balance FROM user_credits WHERE user_id = $1`,
		userID,
	).Scan(&currentBalance)

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusPaymentRequired, 
			fmt.Sprintf("Insufficient credits. This mission requires %d credits. Please purchase credits to continue.", creditsCost))
		return
	} else if err != nil {
		log.Printf("Failed to check credit balance: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to check credit balance")
		return
	}

	if currentBalance < creditsCost {
		utils.ErrorResponse(c, http.StatusPaymentRequired,
			fmt.Sprintf("Insufficient credits. You have %d credits, but this mission requires %d credits. Please purchase more credits.", currentBalance, creditsCost))
		return
	}

	// Insert mission into database
	var mission models.Mission
	err = database.DB.QueryRow(
		`INSERT INTO missions (
			user_id, name, description, last_known_lat, last_known_lon, 
			last_known_time, object_type, uncertainty_radius_m, 
			forecast_hours, ensemble_size, credits_cost, status, created_at, updated_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
		RETURNING id, user_id, name, description, last_known_lat, last_known_lon,
		          last_known_time, object_type, uncertainty_radius_m, forecast_hours,
		          ensemble_size, config, status, job_id, error_message,
		          created_at, updated_at, completed_at`,
		userID, req.Name, req.Description, req.LastKnownLat, req.LastKnownLon,
		req.LastKnownTime, req.ObjectType, req.UncertaintyRadiusM,
		req.ForecastHours, req.EnsembleSize, creditsCost, "created", time.Now(), time.Now(),
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

	// Deduct credits for the mission
	missionIDStr := mission.ID
	description := fmt.Sprintf("Mission: %s (%d forecast hours, %d particles)", mission.Name, req.ForecastHours, req.EnsembleSize)
	newBalance, err := DeductCredits(userID, creditsCost, description, &missionIDStr)
	if err != nil {
		// Failed to deduct credits - delete the mission and return error
		log.Printf("Failed to deduct credits for mission %s: %v", mission.ID, err)
		database.DB.Exec(`DELETE FROM missions WHERE id = $1`, mission.ID)
		utils.ErrorResponse(c, http.StatusPaymentRequired, fmt.Sprintf("Failed to deduct credits: %v", err))
		return
	}

	log.Printf("Deducted %d credits for mission %s. New balance: %d", creditsCost, mission.ID, newBalance)

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
		// Failed to enqueue the job - return error response
		log.Printf("Failed to enqueue drift job for mission %s: %v", mission.ID, err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to enqueue job for processing")
		return
	}

	// Update mission status to "queued"
	_, err = database.DB.Exec(
		`UPDATE missions SET status = $1, updated_at = $2 WHERE id = $3`,
		"queued", time.Now(), mission.ID,
	)
	if err != nil {
		// Log the error but don't fail - the job is already queued and worker will update status
		log.Printf("Failed to update mission %s status to queued: %v", mission.ID, err)
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
		        ensemble_size, credits_cost, config, status, job_id, error_message,
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
			&m.EnsembleSize, &m.CreditsCost, &m.Config, &m.Status, &m.JobID, &m.ErrorMessage,
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
		        ensemble_size, credits_cost, config, status, job_id, error_message,
		        created_at, updated_at, completed_at
		 FROM missions
		 WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	).Scan(
		&m.ID, &m.UserID, &m.Name, &m.Description, &m.LastKnownLat, &m.LastKnownLon,
		&m.LastKnownTime, &m.ObjectType, &m.UncertaintyRadiusM, &m.ForecastHours,
		&m.EnsembleSize, &m.CreditsCost, &m.Config, &m.Status, &m.JobID, &m.ErrorMessage,
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

	// Get results - try with timestep_contours first, fallback if column doesn't exist
	var result models.MissionResult
	err = database.DB.QueryRow(
		`SELECT id, mission_id, centroid_lat, centroid_lon, centroid_time,
		        search_area_50_geom, search_area_90_geom, timestep_contours, netcdf_path,
		        geojson_path, pdf_report_path, particle_count, stranded_count,
		        computation_time_seconds, created_at
		 FROM mission_results WHERE mission_id = $1`,
		missionID,
	).Scan(
		&result.ID, &result.MissionID, &result.CentroidLat, &result.CentroidLon,
		&result.CentroidTime, &result.SearchArea50Geom, &result.SearchArea90Geom,
		&result.TimestepContours, &result.NetcdfPath, &result.GeojsonPath, &result.PdfReportPath,
		&result.ParticleCount, &result.StrandedCount, &result.ComputationTimeSeconds,
		&result.CreatedAt,
	)

	// If query fails due to missing column, try without timestep_contours for backward compatibility
	if err != nil && err != sql.ErrNoRows && strings.Contains(err.Error(), "column") {
		log.Printf("Falling back to query without timestep_contours column: %v", err)
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
		// TimestepContours will be nil, which is fine for backward compatibility
	}

	if err == sql.ErrNoRows {
		utils.ErrorResponse(c, http.StatusNotFound, "Results not found")
		return
	} else if err != nil {
		log.Printf("Database error fetching results: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	utils.SuccessResponse(c, http.StatusOK, result)
}

// DownloadMissionResults handles downloading mission result files
func DownloadMissionResults(c *gin.Context) {
	missionID := c.Param("id")
	format := c.Query("format")

	log.Printf("Download request: mission_id=%s, format=%s", missionID, format)

	// Validate format parameter
	validFormats := map[string]bool{
		"netcdf":  true,
		"geojson": true,
		"pdf":     true,
	}
	if !validFormats[format] {
		log.Printf("Invalid format: %s", format)
		utils.ErrorResponse(c, http.StatusBadRequest, "Invalid format. Must be one of: netcdf, geojson, pdf")
		return
	}

	// Get user ID from JWT and verify ownership
	userID, ok := middleware.GetUserID(c)
	if !ok {
		log.Printf("User not authenticated")
		utils.ErrorResponse(c, http.StatusUnauthorized, "User not authenticated")
		return
	}

	log.Printf("Checking mission ownership: mission_id=%s, user_id=%s", missionID, userID)

	// Verify mission ownership
	var missionStatus string
	err := database.DB.QueryRow(
		`SELECT status FROM missions WHERE id = $1 AND user_id = $2`,
		missionID, userID,
	).Scan(&missionStatus)

	if err == sql.ErrNoRows {
		log.Printf("Mission not found or not owned by user")
		utils.ErrorResponse(c, http.StatusNotFound, "Mission not found")
		return
	} else if err != nil {
		log.Printf("Database error checking mission: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	log.Printf("Mission status: %s", missionStatus)

	// Check if mission is completed
	if missionStatus != "completed" {
		log.Printf("Mission not completed yet")
		utils.ErrorResponse(c, http.StatusBadRequest, "Mission is not completed yet")
		return
	}

	// Get the file path from results
	var filePath *string
	var query string

	switch format {
	case "netcdf":
		query = `SELECT netcdf_path FROM mission_results WHERE mission_id = $1`
	case "geojson":
		query = `SELECT geojson_path FROM mission_results WHERE mission_id = $1`
	case "pdf":
		query = `SELECT pdf_report_path FROM mission_results WHERE mission_id = $1`
	}

	log.Printf("Executing query: %s with mission_id=%s", query, missionID)
	err = database.DB.QueryRow(query, missionID).Scan(&filePath)

	if err == sql.ErrNoRows {
		log.Printf("No results found in mission_results table")
		utils.ErrorResponse(c, http.StatusNotFound, "Results not found")
		return
	} else if err != nil {
		log.Printf("Database error querying results: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Database error")
		return
	}

	log.Printf("File path retrieved: %v", filePath)

	if filePath == nil || *filePath == "" {
		log.Printf("%s file path is empty", format)
		utils.ErrorResponse(c, http.StatusNotFound, fmt.Sprintf("%s file not available", format))
		return
	}

	// Download from S3 and stream to client
	err = streamFromS3(c, *filePath, format, missionID)
	if err != nil {
		log.Printf("Failed to stream file from S3: %v", err)
		utils.ErrorResponse(c, http.StatusInternalServerError, "Failed to download file")
		return
	}
}

// streamFromS3 downloads a file from S3 and streams it to the client
func streamFromS3(c *gin.Context, s3Path string, format string, missionID string) error {
	// Parse S3 path (s3://bucket/key)
	if len(s3Path) < 5 || s3Path[:5] != "s3://" {
		return fmt.Errorf("invalid S3 path: %s", s3Path)
	}

	pathParts := strings.SplitN(s3Path[5:], "/", 2)
	if len(pathParts) != 2 {
		return fmt.Errorf("invalid S3 path format: %s", s3Path)
	}

	bucket := pathParts[0]
	key := pathParts[1]

	// Initialize S3 client
	s3Endpoint := os.Getenv("S3_ENDPOINT")
	s3AccessKey := os.Getenv("S3_ACCESS_KEY")
	s3SecretKey := os.Getenv("S3_SECRET_KEY")

	if s3Endpoint == "" || s3AccessKey == "" || s3SecretKey == "" {
		return fmt.Errorf("S3 configuration not set")
	}

	// Configure AWS session
	sess, err := session.NewSession(&aws.Config{
		Endpoint:         aws.String(s3Endpoint),
		Region:           aws.String("us-east-1"),
		Credentials:      credentials.NewStaticCredentials(s3AccessKey, s3SecretKey, ""),
		S3ForcePathStyle: aws.Bool(true),
	})
	if err != nil {
		return fmt.Errorf("failed to create AWS session: %w", err)
	}

	s3Client := s3.New(sess)

	// Get object from S3
	result, err := s3Client.GetObject(&s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("failed to get object from S3: %w", err)
	}
	defer result.Body.Close()

	// Set appropriate headers
	var contentType string
	var filename string

	switch format {
	case "netcdf":
		contentType = "application/x-netcdf"
		filename = fmt.Sprintf("mission-%s-results.nc", missionID)
	case "geojson":
		contentType = "application/geo+json"
		filename = fmt.Sprintf("mission-%s-trajectories.geojson", missionID)
	case "pdf":
		contentType = "application/pdf"
		filename = fmt.Sprintf("mission-%s-report.pdf", missionID)
	default:
		contentType = "application/octet-stream"
		filename = fmt.Sprintf("mission-%s-results", missionID)
	}

	c.Header("Content-Type", contentType)
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))

	// Stream the file
	_, err = io.Copy(c.Writer, result.Body)
	return err
}
