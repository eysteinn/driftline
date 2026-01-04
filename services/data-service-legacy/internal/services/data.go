package services

import (
	"context"
	"crypto/sha256"
	"fmt"
	"log"
	"path/filepath"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/cache"
	"github.com/eysteinn/driftline/services/data-service/internal/models"
	"github.com/eysteinn/driftline/services/data-service/internal/storage"
)

// DataService handles environmental data retrieval and caching
type DataService struct {
	cache   *cache.Service
	storage *storage.Service
}

// NewDataService creates a new data service
func NewDataService(cacheService *cache.Service, storageService *storage.Service) *DataService {
	return &DataService{
		cache:   cacheService,
		storage: storageService,
	}
}

// GetData retrieves environmental data based on the request
func (s *DataService) GetData(ctx context.Context, req *models.DataRequest) (*models.DataResponse, error) {
	// Validate request
	if err := req.Validate(); err != nil {
		return nil, err
	}

	// Generate cache key
	cacheKey := s.generateCacheKey(req)

	// Check cache first
	cachedPath, err := s.cache.Get(ctx, cacheKey)
	if err == nil && cachedPath != "" {
		log.Printf("Cache hit for key: %s", cacheKey)
		return s.buildResponse(req, cachedPath, true)
	}

	log.Printf("Cache miss for key: %s", cacheKey)

	// Check if data exists in storage
	objectKey := s.generateObjectKey(req)
	exists, err := s.storage.Exists(ctx, objectKey)
	if err != nil {
		return nil, fmt.Errorf("failed to check storage: %w", err)
	}

	var filePath string
	if exists {
		log.Printf("Data exists in storage: %s", objectKey)
		// Data exists in storage, use it
		filePath = objectKey
	} else {
		log.Printf("Data not found, would fetch from external source")
		// In a full implementation, this would fetch from external sources
		// For now, return a stub indicating where data would come from
		return s.buildStubResponse(req)
	}

	// Cache the result
	if err := s.cache.Set(ctx, cacheKey, filePath, 24*time.Hour); err != nil {
		log.Printf("Failed to cache result: %v", err)
		// Continue anyway, caching is not critical
	}

	return s.buildResponse(req, filePath, false)
}

// generateCacheKey creates a unique cache key for the request
func (s *DataService) generateCacheKey(req *models.DataRequest) string {
	// Create a unique key based on all request parameters
	key := fmt.Sprintf("%s:%.2f,%.2f,%.2f,%.2f:%s:%s",
		req.DataType,
		req.MinLat, req.MaxLat, req.MinLon, req.MaxLon,
		req.StartTime.Format(time.RFC3339),
		req.EndTime.Format(time.RFC3339),
	)
	
	// Hash the key to keep it reasonably sized
	hash := sha256.Sum256([]byte(key))
	return fmt.Sprintf("data:%s:%x", req.DataType, hash[:8])
}

// generateObjectKey creates a storage key for the data
func (s *DataService) generateObjectKey(req *models.DataRequest) string {
	// Organize by data type and time
	dateStr := req.StartTime.Format("2006/01/02")
	return filepath.Join(string(req.DataType), dateStr, "data.nc")
}

// buildResponse constructs a data response
func (s *DataService) buildResponse(req *models.DataRequest, filePath string, cacheHit bool) (*models.DataResponse, error) {
	metadata := &models.Metadata{
		Variables:  getDefaultVariables(req.DataType),
		Resolution: getDefaultResolution(req.DataType),
		Bounds: models.Bounds{
			MinLat: req.MinLat,
			MaxLat: req.MaxLat,
			MinLon: req.MinLon,
			MaxLon: req.MaxLon,
		},
		TimeRange: models.TimeRange{
			Start: req.StartTime,
			End:   req.EndTime,
		},
	}

	return &models.DataResponse{
		DataType:  req.DataType,
		Source:    getDataSource(req.DataType),
		CacheHit:  cacheHit,
		FilePath:  filePath,
		Metadata:  metadata,
		ExpiresAt: time.Now().Add(24 * time.Hour),
	}, nil
}

// buildStubResponse creates a stub response for demonstration
func (s *DataService) buildStubResponse(req *models.DataRequest) (*models.DataResponse, error) {
	metadata := &models.Metadata{
		Variables:   getDefaultVariables(req.DataType),
		Resolution:  getDefaultResolution(req.DataType),
		Description: fmt.Sprintf("Stub data for %s (external fetch not implemented)", req.DataType),
		Bounds: models.Bounds{
			MinLat: req.MinLat,
			MaxLat: req.MaxLat,
			MinLon: req.MinLon,
			MaxLon: req.MaxLon,
		},
		TimeRange: models.TimeRange{
			Start: req.StartTime,
			End:   req.EndTime,
		},
	}

	return &models.DataResponse{
		DataType:  req.DataType,
		Source:    getDataSource(req.DataType),
		CacheHit:  false,
		Metadata:  metadata,
		ExpiresAt: time.Now().Add(24 * time.Hour),
	}, nil
}

// getDefaultVariables returns default variables for each data type
func getDefaultVariables(dataType models.DataType) []string {
	switch dataType {
	case models.DataTypeOceanCurrents:
		return []string{"eastward_sea_water_velocity", "northward_sea_water_velocity"}
	case models.DataTypeWind:
		return []string{"eastward_wind", "northward_wind"}
	case models.DataTypeWaves:
		return []string{"sea_surface_wave_significant_height", "sea_surface_wave_period"}
	default:
		return []string{}
	}
}

// getDefaultResolution returns default resolution for each data type
func getDefaultResolution(dataType models.DataType) string {
	switch dataType {
	case models.DataTypeOceanCurrents:
		return "1/12 degree (~9km)"
	case models.DataTypeWind:
		return "0.25 degree (~28km)"
	case models.DataTypeWaves:
		return "0.5 degree (~56km)"
	default:
		return "unknown"
	}
}

// getDataSource returns the data source name for each data type
func getDataSource(dataType models.DataType) string {
	switch dataType {
	case models.DataTypeOceanCurrents:
		return "Copernicus Marine Service (CMEMS)"
	case models.DataTypeWind:
		return "NOAA GFS"
	case models.DataTypeWaves:
		return "NOAA WaveWatch III"
	default:
		return "unknown"
	}
}
