package services

import (
	"context"
	"testing"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/models"
)

func TestGenerateCacheKey(t *testing.T) {
	s := &DataService{}

	req1 := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	req2 := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	// Same requests should generate same key
	key1 := s.generateCacheKey(req1)
	key2 := s.generateCacheKey(req2)

	if key1 != key2 {
		t.Errorf("Same requests generated different keys: %s != %s", key1, key2)
	}

	// Different requests should generate different keys
	req3 := &models.DataRequest{
		DataType:  models.DataTypeWind,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	key3 := s.generateCacheKey(req3)
	if key1 == key3 {
		t.Errorf("Different requests generated same key")
	}
}

func TestBuildStubResponse(t *testing.T) {
	s := &DataService{}

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	resp, err := s.buildStubResponse(req)
	if err != nil {
		t.Fatalf("buildStubResponse() error = %v", err)
	}

	if resp.DataType != models.DataTypeOceanCurrents {
		t.Errorf("Expected DataType %s, got %s", models.DataTypeOceanCurrents, resp.DataType)
	}

	if resp.Source == "" {
		t.Error("Expected non-empty Source")
	}

	if resp.Metadata == nil {
		t.Fatal("Expected Metadata to be non-nil")
	}

	if len(resp.Metadata.Variables) == 0 {
		t.Error("Expected at least one variable in Metadata")
	}

	if resp.Metadata.Bounds.MinLat != req.MinLat {
		t.Errorf("Expected MinLat %f, got %f", req.MinLat, resp.Metadata.Bounds.MinLat)
	}
}

func TestGetDefaultVariables(t *testing.T) {
	tests := []struct {
		name     string
		dataType models.DataType
		want     int // number of expected variables
	}{
		{"ocean currents", models.DataTypeOceanCurrents, 2},
		{"wind", models.DataTypeWind, 2},
		{"waves", models.DataTypeWaves, 2},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			vars := getDefaultVariables(tt.dataType)
			if len(vars) != tt.want {
				t.Errorf("getDefaultVariables() returned %d variables, want %d", len(vars), tt.want)
			}
		})
	}
}

func TestGetDataSource(t *testing.T) {
	tests := []struct {
		name     string
		dataType models.DataType
		wantNil  bool
	}{
		{"ocean currents", models.DataTypeOceanCurrents, false},
		{"wind", models.DataTypeWind, false},
		{"waves", models.DataTypeWaves, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			source := getDataSource(tt.dataType)
			if (source == "") == !tt.wantNil {
				t.Errorf("getDataSource() returned empty string for %s", tt.dataType)
			}
		})
	}
}

func TestDataServiceValidation(t *testing.T) {
	// Test that service properly validates requests
	s := &DataService{}

	ctx := context.Background()

	// Invalid request - bad bounds
	invalidReq := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    70.0,
		MaxLat:    60.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	_, err := s.GetData(ctx, invalidReq)
	if err == nil {
		t.Error("Expected error for invalid request, got nil")
	}
}
