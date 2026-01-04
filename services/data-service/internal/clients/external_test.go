package clients

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/models"
)

func TestCopernicusClient_FetchData_Success(t *testing.T) {
	// Create mock server
	mockData := []byte("mock NetCDF data content")
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify authentication
		username, password, ok := r.BasicAuth()
		if !ok || username != "testuser" || password != "testpass" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}

		// Verify query parameters for THREDDS NCSS API
		query := r.URL.Query()
		if query.Get("north") == "" || query.Get("south") == "" {
			t.Error("Expected spatial parameters (north/south)")
		}
		if query.Get("west") == "" || query.Get("east") == "" {
			t.Error("Expected spatial parameters (west/east)")
		}
		if query.Get("time_start") == "" || query.Get("time_end") == "" {
			t.Error("Expected temporal parameters")
		}
		if query.Get("accept") != "netcdf" {
			t.Errorf("Expected accept=netcdf, got %s", query.Get("accept"))
		}

		// Return mock data
		w.WriteHeader(http.StatusOK)
		w.Write(mockData)
	}))
	defer server.Close()

	// Create client with mock server
	client := NewCopernicusClient(server.URL, "testuser", "testpass")

	// Create valid request
	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	ctx := context.Background()
	filePath, err := client.FetchData(ctx, req)
	if err != nil {
		t.Fatalf("FetchData() error = %v", err)
	}

	// Verify file was created
	if filePath == "" {
		t.Fatal("Expected non-empty file path")
	}

	// Verify file content
	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("Failed to read file: %v", err)
	}

	if string(content) != string(mockData) {
		t.Errorf("File content = %s, want %s", string(content), string(mockData))
	}

	// Clean up
	_ = os.Remove(filePath)
}

func TestCopernicusClient_FetchData_InvalidRequest(t *testing.T) {
	client := NewCopernicusClient("http://example.com", "user", "pass")

	// Invalid request - bad bounds
	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    70.0,
		MaxLat:    60.0, // Invalid: MinLat >= MaxLat
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	_, err := client.FetchData(ctx, req)
	if err == nil {
		t.Error("Expected error for invalid request, got nil")
	}
}

func TestCopernicusClient_FetchData_AuthenticationFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte("Authentication failed"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "baduser", "badpass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	_, err := client.FetchData(ctx, req)
	if err == nil {
		t.Error("Expected error for auth failure, got nil")
	}
	if !strings.Contains(err.Error(), "401") {
		t.Errorf("Expected 401 error, got: %v", err)
	}
}

func TestCopernicusClient_FetchData_ServerError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte("Internal server error"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	_, err := client.FetchData(ctx, req)
	if err == nil {
		t.Error("Expected error for server error, got nil")
	}
	if !strings.Contains(err.Error(), "500") {
		t.Errorf("Expected 500 error, got: %v", err)
	}
}

func TestCopernicusClient_FetchData_ContextCancellation(t *testing.T) {
	// Create server that delays response
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(100 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("data"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	// Create context that cancels immediately
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	_, err := client.FetchData(ctx, req)
	if err == nil {
		t.Error("Expected error for cancelled context, got nil")
	}
	if !strings.Contains(err.Error(), "context canceled") {
		t.Errorf("Expected context canceled error, got: %v", err)
	}
}

func TestCopernicusClient_FetchData_Retry(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			// Fail first 2 attempts with 503 (retryable)
			w.WriteHeader(http.StatusServiceUnavailable)
			w.Write([]byte("Service temporarily unavailable"))
			return
		}
		// Succeed on 3rd attempt
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("success"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	filePath, err := client.FetchData(ctx, req)
	if err != nil {
		t.Fatalf("Expected success after retries, got error: %v", err)
	}

	if attempts != 3 {
		t.Errorf("Expected 3 attempts, got %d", attempts)
	}

	// Clean up
	_ = os.Remove(filePath)
}

func TestCopernicusClient_HealthCheck_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify it's a health check request for THREDDS catalog
		if !strings.Contains(r.URL.Path, "catalog") {
			t.Errorf("Expected catalog path for health check, got %s", r.URL.Path)
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL+"/ncss", "user", "pass")

	ctx := context.Background()
	err := client.HealthCheck(ctx)
	if err != nil {
		t.Errorf("HealthCheck() error = %v", err)
	}
}

func TestCopernicusClient_HealthCheck_Failure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	ctx := context.Background()
	err := client.HealthCheck(ctx)
	if err == nil {
		t.Error("Expected error for health check failure, got nil")
	}
}

func TestCopernicusClient_HealthCheck_NoEndpoint(t *testing.T) {
	client := NewCopernicusClient("", "user", "pass")

	ctx := context.Background()
	err := client.HealthCheck(ctx)
	if err == nil {
		t.Error("Expected error for empty endpoint, got nil")
	}
}

func TestCopernicusClient_BuildMotuURL(t *testing.T) {
	client := NewCopernicusClient("http://example.com/thredds/ncss", "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
		EndTime:   time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC),
	}

	url, err := client.buildMotuURL(req)
	if err != nil {
		t.Fatalf("buildMotuURL() error = %v", err)
	}

	// Verify URL contains expected parameters for THREDDS NCSS
	expectedParams := []string{
		"north=70",
		"south=60",
		"west=-20",
		"east=-10",
		"time_start=2024-01-01",
		"time_end=2024-01-02",
		"var=uo",
		"var=vo",
		"accept=netcdf",
	}

	for _, param := range expectedParams {
		if !strings.Contains(url, param) {
			t.Errorf("URL missing parameter: %s\nGot: %s", param, url)
		}
	}
}

func TestCopernicusClient_WithHTTPClient(t *testing.T) {
	customClient := &http.Client{Timeout: 1 * time.Second}
	client := NewCopernicusClient("http://example.com", "user", "pass",
		WithHTTPClient(customClient))

	if client.httpClient != customClient {
		t.Error("Custom HTTP client not set")
	}
}

func TestCopernicusClient_WithConfig(t *testing.T) {
	customConfig := CopernicusConfig{
		DatasetID: "custom_dataset",
		ServiceID: "custom_service",
		Variables: []string{"custom_var"},
	}

	client := NewCopernicusClient("http://example.com", "user", "pass",
		WithConfig(customConfig))

	if client.config.DatasetID != customConfig.DatasetID {
		t.Errorf("DatasetID = %s, want %s", client.config.DatasetID, customConfig.DatasetID)
	}
	if client.config.ServiceID != customConfig.ServiceID {
		t.Errorf("ServiceID = %s, want %s", client.config.ServiceID, customConfig.ServiceID)
	}
}

func TestIsRetryableError(t *testing.T) {
	tests := []struct {
		name  string
		err   error
		want  bool
	}{
		{"nil error", nil, false},
		{"500 error", fmt.Errorf("HTTP 500: Internal Server Error"), true},
		{"503 error", fmt.Errorf("HTTP 503: Service Unavailable"), true},
		{"timeout", fmt.Errorf("request timeout"), true},
		{"connection reset", fmt.Errorf("connection reset by peer"), true},
		{"400 error", fmt.Errorf("HTTP 400: Bad Request"), false},
		{"401 error", fmt.Errorf("HTTP 401: Unauthorized"), false},
		{"404 error", fmt.Errorf("HTTP 404: Not Found"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isRetryableError(tt.err)
			if got != tt.want {
				t.Errorf("isRetryableError() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestFormatFloat(t *testing.T) {
	tests := []struct {
		input float64
		want  string
	}{
		{60.0, "60.000000"},
		{-20.5, "-20.500000"},
		{-10.123456, "-10.123456"},
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("%.6f", tt.input), func(t *testing.T) {
			got := formatFloat(tt.input)
			if got != tt.want {
				t.Errorf("formatFloat(%f) = %s, want %s", tt.input, got, tt.want)
			}
		})
	}
}

func TestCopernicusClient_NoCredentialLogging(t *testing.T) {
	// This test ensures credentials are never logged
	// We check that error messages don't contain the password
	
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte("Auth failed"))
	}))
	defer server.Close()

	sensitivePassword := "super-secret-password-12345"
	client := NewCopernicusClient(server.URL, "user", sensitivePassword)

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	_, err := client.FetchData(ctx, req)
	if err == nil {
		t.Fatal("Expected error")
	}

	// Verify password is not in error message
	if strings.Contains(err.Error(), sensitivePassword) {
		t.Errorf("Error message contains password: %v", err)
	}
}

func TestCopernicusClient_StreamingToFile(t *testing.T) {
	// Test that large responses are streamed, not loaded into memory
	largeDataSize := 1024 * 1024 // 1MB
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		// Write large response in chunks
		chunk := make([]byte, 1024)
		for i := 0; i < largeDataSize/1024; i++ {
			w.Write(chunk)
		}
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
	}

	ctx := context.Background()
	filePath, err := client.FetchData(ctx, req)
	if err != nil {
		t.Fatalf("FetchData() error = %v", err)
	}

	// Verify file size
	info, err := os.Stat(filePath)
	if err != nil {
		t.Fatalf("Failed to stat file: %v", err)
	}

	if info.Size() != int64(largeDataSize) {
		t.Errorf("File size = %d, want %d", info.Size(), largeDataSize)
	}

	// Clean up
	_ = os.Remove(filePath)
}

func TestCopernicusClient_CustomVariables(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		variables := r.URL.Query()["var"]
		if len(variables) != 3 {
			t.Errorf("Expected 3 variables, got %d", len(variables))
			w.WriteHeader(http.StatusOK)
			w.Write([]byte("data"))
			return
		}
		if variables[0] != "custom1" || variables[1] != "custom2" || variables[2] != "custom3" {
			t.Errorf("Unexpected variables: %v", variables)
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("data"))
	}))
	defer server.Close()

	client := NewCopernicusClient(server.URL, "user", "pass")

	req := &models.DataRequest{
		DataType:  models.DataTypeOceanCurrents,
		MinLat:    60.0,
		MaxLat:    70.0,
		MinLon:    -20.0,
		MaxLon:    -10.0,
		StartTime: time.Now(),
		EndTime:   time.Now().Add(24 * time.Hour),
		Variables: []string{"custom1", "custom2", "custom3"},
	}

	ctx := context.Background()
	filePath, err := client.FetchData(ctx, req)
	if err != nil {
		t.Fatalf("FetchData() error = %v", err)
	}

	// Clean up
	_ = os.Remove(filePath)
}
