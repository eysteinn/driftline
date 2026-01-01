package models

import (
	"time"
)

// Mission represents a drift forecast mission
type Mission struct {
	ID                 string    `json:"id" db:"id"`
	UserID             string    `json:"user_id" db:"user_id"`
	Name               string    `json:"name" db:"name"`
	Description        string    `json:"description" db:"description"`
	LastKnownLat       float64   `json:"last_known_lat" db:"last_known_lat"`
	LastKnownLon       float64   `json:"last_known_lon" db:"last_known_lon"`
	LastKnownTime      time.Time `json:"last_known_time" db:"last_known_time"`
	ObjectType         string    `json:"object_type" db:"object_type"`
	UncertaintyRadiusM *float64  `json:"uncertainty_radius_m" db:"uncertainty_radius_m"`
	ForecastHours      int       `json:"forecast_hours" db:"forecast_hours"`
	EnsembleSize       int       `json:"ensemble_size" db:"ensemble_size"`
	Config             *string   `json:"config" db:"config"`
	Status             string    `json:"status" db:"status"`
	JobID              *string   `json:"job_id" db:"job_id"`
	ErrorMessage       *string   `json:"error_message" db:"error_message"`
	CreatedAt          time.Time `json:"created_at" db:"created_at"`
	UpdatedAt          time.Time `json:"updated_at" db:"updated_at"`
	CompletedAt        *time.Time `json:"completed_at" db:"completed_at"`
}

// CreateMissionRequest represents a request to create a new mission
type CreateMissionRequest struct {
	Name               string    `json:"name" binding:"required"`
	Description        string    `json:"description"`
	LastKnownLat       float64   `json:"last_known_lat" binding:"required,min=-90,max=90"`
	LastKnownLon       float64   `json:"last_known_lon" binding:"required,min=-180,max=180"`
	LastKnownTime      time.Time `json:"last_known_time" binding:"required"`
	ObjectType         string    `json:"object_type" binding:"required"`
	UncertaintyRadiusM *float64  `json:"uncertainty_radius_m"`
	ForecastHours      int       `json:"forecast_hours" binding:"required,min=1,max=168"`
	EnsembleSize       int       `json:"ensemble_size" binding:"min=100,max=10000"`
}

// MissionListResponse represents a paginated list of missions
type MissionListResponse struct {
	Missions []Mission `json:"missions"`
	Total    int       `json:"total"`
	Page     int       `json:"page"`
	PageSize int       `json:"page_size"`
}
