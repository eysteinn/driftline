package models

import (
	"time"
)

// Mission represents a drift forecast mission
type Mission struct {
	ID                 string     `json:"id" db:"id"`
	UserID             string     `json:"userId" db:"user_id"`
	Name               string     `json:"name" db:"name"`
	Description        string     `json:"description" db:"description"`
	LastKnownLat       float64    `json:"lastKnownLat" db:"last_known_lat"`
	LastKnownLon       float64    `json:"lastKnownLon" db:"last_known_lon"`
	LastKnownTime      time.Time  `json:"lastKnownTime" db:"last_known_time"`
	ObjectType         string     `json:"objectType" db:"object_type"`
	UncertaintyRadiusM *float64   `json:"uncertaintyRadiusM" db:"uncertainty_radius_m"`
	ForecastHours      int        `json:"forecastHours" db:"forecast_hours"`
	EnsembleSize       int        `json:"ensembleSize" db:"ensemble_size"`
	Backtracking       bool       `json:"backtracking" db:"backtracking"`
	Config             *string    `json:"config" db:"config"`
	Status             string     `json:"status" db:"status"`
	JobID              *string    `json:"jobId" db:"job_id"`
	ErrorMessage       *string    `json:"errorMessage" db:"error_message"`
	CreatedAt          time.Time  `json:"createdAt" db:"created_at"`
	UpdatedAt          time.Time  `json:"updatedAt" db:"updated_at"`
	CompletedAt        *time.Time `json:"completedAt" db:"completed_at"`
}

// CreateMissionRequest represents a request to create a new mission
type CreateMissionRequest struct {
	Name               string    `json:"name" binding:"required"`
	Description        string    `json:"description"`
	LastKnownLat       float64   `json:"lastKnownLat" binding:"required,min=-90,max=90"`
	LastKnownLon       float64   `json:"lastKnownLon" binding:"required,min=-180,max=180"`
	LastKnownTime      time.Time `json:"lastKnownTime" binding:"required"`
	ObjectType         string    `json:"objectType" binding:"required"`
	UncertaintyRadiusM *float64  `json:"uncertaintyRadiusM"`
	ForecastHours      int       `json:"forecastHours" binding:"required,min=1,max=168"`
	EnsembleSize       int       `json:"ensembleSize" binding:"min=100,max=10000"`
	Backtracking       bool      `json:"backtracking"`
}

// MissionListResponse represents a paginated list of missions
type MissionListResponse struct {
	Missions []Mission `json:"missions"`
	Total    int       `json:"total"`
	Page     int       `json:"page"`
	PageSize int       `json:"page_size"`
}
