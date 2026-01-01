package models

import (
	"time"
)

// MissionResult represents the results of a completed drift simulation
type MissionResult struct {
	ID                      string     `json:"id" db:"id"`
	MissionID               string     `json:"mission_id" db:"mission_id"`
	CentroidLat             *float64   `json:"centroid_lat" db:"centroid_lat"`
	CentroidLon             *float64   `json:"centroid_lon" db:"centroid_lon"`
	CentroidTime            *time.Time `json:"centroid_time" db:"centroid_time"`
	SearchArea50Geom        *string    `json:"search_area_50_geom" db:"search_area_50_geom"`
	SearchArea90Geom        *string    `json:"search_area_90_geom" db:"search_area_90_geom"`
	NetcdfPath              *string    `json:"netcdf_path" db:"netcdf_path"`
	GeojsonPath             *string    `json:"geojson_path" db:"geojson_path"`
	PdfReportPath           *string    `json:"pdf_report_path" db:"pdf_report_path"`
	ParticleCount           *int       `json:"particle_count" db:"particle_count"`
	StrandedCount           *int       `json:"stranded_count" db:"stranded_count"`
	ComputationTimeSeconds  *float64   `json:"computation_time_seconds" db:"computation_time_seconds"`
	CreatedAt               time.Time  `json:"created_at" db:"created_at"`
}
