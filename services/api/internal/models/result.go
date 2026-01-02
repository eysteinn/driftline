package models

import (
	"encoding/json"
	"time"
)

// MissionResult represents the results of a completed drift simulation
type MissionResult struct {
	ID                      string          `json:"id" db:"id"`
	MissionID               string          `json:"missionId" db:"mission_id"`
	CentroidLat             *float64        `json:"centroidLat" db:"centroid_lat"`
	CentroidLon             *float64        `json:"centroidLon" db:"centroid_lon"`
	CentroidTime            *time.Time      `json:"centroidTime" db:"centroid_time"`
	SearchArea50Geom        json.RawMessage `json:"searchArea50Geom" db:"search_area_50_geom"`
	SearchArea90Geom        json.RawMessage `json:"searchArea90Geom" db:"search_area_90_geom"`
	NetcdfPath              *string         `json:"netcdfPath" db:"netcdf_path"`
	GeojsonPath             *string         `json:"geojsonPath" db:"geojson_path"`
	PdfReportPath           *string         `json:"pdfReportPath" db:"pdf_report_path"`
	ParticleCount           *int            `json:"particleCount" db:"particle_count"`
	StrandedCount           *int            `json:"strandedCount" db:"stranded_count"`
	ComputationTimeSeconds  *float64        `json:"computationTimeSeconds" db:"computation_time_seconds"`
	CreatedAt               time.Time       `json:"createdAt" db:"created_at"`
}
