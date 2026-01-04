package models

import "time"

// DataType represents the type of environmental data
type DataType string

const (
	DataTypeOceanCurrents DataType = "ocean_currents"
	DataTypeWind          DataType = "wind"
	DataTypeWaves         DataType = "waves"
)

// DataRequest represents a request for environmental data
type DataRequest struct {
	// Type of data requested (ocean_currents, wind, waves)
	DataType DataType `json:"data_type" binding:"required"`
	
	// Spatial bounds (WGS84 coordinates)
	MinLat float64 `json:"min_lat" binding:"required,min=-90,max=90"`
	MaxLat float64 `json:"max_lat" binding:"required,min=-90,max=90"`
	MinLon float64 `json:"min_lon" binding:"required,min=-180,max=180"`
	MaxLon float64 `json:"max_lon" binding:"required,min=-180,max=180"`
	
	// Temporal bounds
	StartTime time.Time `json:"start_time" binding:"required"`
	EndTime   time.Time `json:"end_time" binding:"required"`
	
	// Optional parameters
	Resolution string `json:"resolution,omitempty"` // e.g., "0.25deg", "1km"
	Variables  []string `json:"variables,omitempty"` // Specific variables to retrieve
}

// DataResponse represents the response containing environmental data
type DataResponse struct {
	DataType  DataType  `json:"data_type"`
	Source    string    `json:"source"`
	CacheHit  bool      `json:"cache_hit"`
	FileURL   string    `json:"file_url,omitempty"`   // URL to download data file
	FilePath  string    `json:"file_path,omitempty"`  // Local file path if available
	Metadata  *Metadata `json:"metadata"`
	ExpiresAt time.Time `json:"expires_at"`
}

// Metadata contains information about the data
type Metadata struct {
	Variables   []string          `json:"variables"`
	TimeSteps   int               `json:"time_steps"`
	Resolution  string            `json:"resolution"`
	Bounds      Bounds            `json:"bounds"`
	TimeRange   TimeRange         `json:"time_range"`
	Units       map[string]string `json:"units,omitempty"`
	Description string            `json:"description,omitempty"`
}

// Bounds represents spatial boundaries
type Bounds struct {
	MinLat float64 `json:"min_lat"`
	MaxLat float64 `json:"max_lat"`
	MinLon float64 `json:"min_lon"`
	MaxLon float64 `json:"max_lon"`
}

// TimeRange represents temporal boundaries
type TimeRange struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
}

// Validate checks if the data request is valid
func (r *DataRequest) Validate() error {
	if r.MinLat >= r.MaxLat {
		return ErrInvalidBounds
	}
	if r.MinLon >= r.MaxLon {
		return ErrInvalidBounds
	}
	if r.StartTime.After(r.EndTime) {
		return ErrInvalidTimeRange
	}
	return nil
}
