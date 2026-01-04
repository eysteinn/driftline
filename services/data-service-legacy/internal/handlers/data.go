package handlers

import (
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/models"
	"github.com/eysteinn/driftline/services/data-service/internal/services"
	"github.com/gin-gonic/gin"
)

// DataHandler handles environmental data requests
type DataHandler struct {
	dataService *services.DataService
}

// NewDataHandler creates a new data handler
func NewDataHandler(dataService *services.DataService) *DataHandler {
	return &DataHandler{
		dataService: dataService,
	}
}

// GetOceanCurrents handles requests for ocean current data
func (h *DataHandler) GetOceanCurrents(c *gin.Context) {
	req := &models.DataRequest{
		DataType: models.DataTypeOceanCurrents,
	}
	h.handleDataRequest(c, req)
}

// GetWind handles requests for wind data
func (h *DataHandler) GetWind(c *gin.Context) {
	req := &models.DataRequest{
		DataType: models.DataTypeWind,
	}
	h.handleDataRequest(c, req)
}

// GetWaves handles requests for wave data
func (h *DataHandler) GetWaves(c *gin.Context) {
	req := &models.DataRequest{
		DataType: models.DataTypeWaves,
	}
	h.handleDataRequest(c, req)
}

// handleDataRequest processes a data request
func (h *DataHandler) handleDataRequest(c *gin.Context, req *models.DataRequest) {
	// Parse query parameters
	if err := h.parseQueryParams(c, req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	// Get data from service
	ctx := c.Request.Context()
	resp, err := h.dataService.GetData(ctx, req)
	if err != nil {
		log.Printf("Error getting data: %v", err)
		
		// Map errors to HTTP status codes
		status := http.StatusInternalServerError
		if err == models.ErrInvalidBounds || err == models.ErrInvalidTimeRange {
			status = http.StatusBadRequest
		} else if err == models.ErrDataNotFound {
			status = http.StatusNotFound
		}
		
		c.JSON(status, gin.H{
			"error": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, resp)
}

// parseQueryParams extracts parameters from query string
func (h *DataHandler) parseQueryParams(c *gin.Context, req *models.DataRequest) error {
	// Spatial bounds (required)
	minLat, err := parseFloat(c.Query("min_lat"))
	if err != nil {
		return err
	}
	req.MinLat = minLat

	maxLat, err := parseFloat(c.Query("max_lat"))
	if err != nil {
		return err
	}
	req.MaxLat = maxLat

	minLon, err := parseFloat(c.Query("min_lon"))
	if err != nil {
		return err
	}
	req.MinLon = minLon

	maxLon, err := parseFloat(c.Query("max_lon"))
	if err != nil {
		return err
	}
	req.MaxLon = maxLon

	// Temporal bounds (required)
	startTimeStr := c.Query("start_time")
	if startTimeStr == "" {
		// Default to current time
		req.StartTime = time.Now().UTC()
	} else {
		startTime, err := time.Parse(time.RFC3339, startTimeStr)
		if err != nil {
			return err
		}
		req.StartTime = startTime
	}

	endTimeStr := c.Query("end_time")
	if endTimeStr == "" {
		// Default to 48 hours from start
		req.EndTime = req.StartTime.Add(48 * time.Hour)
	} else {
		endTime, err := time.Parse(time.RFC3339, endTimeStr)
		if err != nil {
			return err
		}
		req.EndTime = endTime
	}

	// Optional parameters
	if resolution := c.Query("resolution"); resolution != "" {
		req.Resolution = resolution
	}

	return nil
}

// parseFloat parses a float from string
func parseFloat(s string) (float64, error) {
	if s == "" {
		return 0, models.ErrInvalidBounds
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	return f, nil
}
