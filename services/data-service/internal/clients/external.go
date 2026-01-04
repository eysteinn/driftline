package clients

import (
	"context"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/eysteinn/driftline/services/data-service/internal/models"
)

// ExternalDataClient represents a client for fetching data from external sources
type ExternalDataClient interface {
	FetchData(ctx context.Context, req *models.DataRequest) (string, error)
	HealthCheck(ctx context.Context) error
}

// CopernicusConfig holds configuration for Copernicus Marine data requests
type CopernicusConfig struct {
	// Dataset and service identifiers for Motu API
	DatasetID string
	ServiceID string
	ProductID string
	// Variables to fetch (e.g., "uo", "vo" for ocean currents)
	Variables []string
}

// CopernicusClient implements ExternalDataClient for Copernicus Marine Service
type CopernicusClient struct {
	endpoint   string
	username   string
	password   string
	httpClient *http.Client
	config     CopernicusConfig
}

// CopernicusClientOption is a functional option for CopernicusClient
type CopernicusClientOption func(*CopernicusClient)

// WithHTTPClient sets a custom HTTP client
func WithHTTPClient(client *http.Client) CopernicusClientOption {
	return func(c *CopernicusClient) {
		c.httpClient = client
	}
}

// WithConfig sets the Copernicus configuration
func WithConfig(config CopernicusConfig) CopernicusClientOption {
	return func(c *CopernicusClient) {
		c.config = config
	}
}

// NewCopernicusClient creates a new Copernicus Marine client
func NewCopernicusClient(endpoint, username, password string, opts ...CopernicusClientOption) *CopernicusClient {
	client := &CopernicusClient{
		endpoint:   endpoint,
		username:   username,
		password:   password,
		httpClient: &http.Client{Timeout: 5 * time.Minute},
		config: CopernicusConfig{
			// Default configuration for CMEMS Global Ocean Physics Analysis
			DatasetID: "cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
			ServiceID: "GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS",
			ProductID: "global-analysis-forecast-phy-001-024",
			Variables: []string{"uo", "vo"}, // eastward and northward velocities
		},
	}
	
	for _, opt := range opts {
		opt(client)
	}
	
	return client
}

// FetchData fetches ocean current data from Copernicus Marine
func (c *CopernicusClient) FetchData(ctx context.Context, req *models.DataRequest) (string, error) {
	// Validate request
	if err := req.Validate(); err != nil {
		return "", fmt.Errorf("invalid request: %w", err)
	}
	
	// Build Motu API request URL
	requestURL, err := c.buildMotuURL(req)
	if err != nil {
		return "", fmt.Errorf("failed to build Motu URL: %w", err)
	}
	
	// Create temporary file for NetCDF data
	tmpFile, err := os.CreateTemp("", "copernicus_*.nc")
	if err != nil {
		return "", fmt.Errorf("failed to create temp file: %w", err)
	}
	defer tmpFile.Close()
	
	tmpPath := tmpFile.Name()
	
	// Download data with retries
	err = c.downloadWithRetry(ctx, requestURL, tmpFile)
	if err != nil {
		os.Remove(tmpPath) // Clean up on error
		return "", fmt.Errorf("failed to download data: %w", err)
	}
	
	return tmpPath, nil
}

// buildMotuURL constructs the Motu API request URL
func (c *CopernicusClient) buildMotuURL(req *models.DataRequest) (string, error) {
	if c.endpoint == "" {
		return "", fmt.Errorf("endpoint not configured")
	}
	
	u, err := url.Parse(c.endpoint)
	if err != nil {
		return "", fmt.Errorf("invalid endpoint URL: %w", err)
	}
	
	// Build query parameters for Motu subsetting API
	q := u.Query()
	q.Set("action", "productdownload")
	q.Set("service", c.config.ServiceID)
	q.Set("product", c.config.DatasetID)
	
	// Spatial subsetting
	q.Set("x_lo", formatFloat(req.MinLon))
	q.Set("x_hi", formatFloat(req.MaxLon))
	q.Set("y_lo", formatFloat(req.MinLat))
	q.Set("y_hi", formatFloat(req.MaxLat))
	
	// Temporal subsetting
	q.Set("t_lo", req.StartTime.Format("2006-01-02 15:04:05"))
	q.Set("t_hi", req.EndTime.Format("2006-01-02 15:04:05"))
	
	// Variables - use configured or requested variables
	variables := c.config.Variables
	if len(req.Variables) > 0 {
		variables = req.Variables
	}
	for _, v := range variables {
		q.Add("variable", v)
	}
	
	// Output mode and format
	q.Set("mode", "console")
	q.Set("out_dir", "/tmp")
	q.Set("out_name", "data.nc")
	
	u.RawQuery = q.Encode()
	return u.String(), nil
}

// downloadWithRetry downloads data with exponential backoff retry logic
func (c *CopernicusClient) downloadWithRetry(ctx context.Context, requestURL string, dest io.Writer) error {
	maxRetries := 3
	baseDelay := 1 * time.Second
	
	var lastErr error
	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			// Exponential backoff
			delay := time.Duration(math.Pow(2, float64(attempt-1))) * baseDelay
			select {
			case <-time.After(delay):
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		
		err := c.downloadData(ctx, requestURL, dest)
		if err == nil {
			return nil
		}
		
		lastErr = err
		
		// Don't retry on context cancellation or client errors (4xx)
		if ctx.Err() != nil {
			return ctx.Err()
		}
		
		// Check if error is retryable (5xx or network errors)
		if !isRetryableError(err) {
			return err
		}
	}
	
	return fmt.Errorf("failed after %d retries: %w", maxRetries, lastErr)
}

// downloadData performs the actual HTTP request and streams response to file
func (c *CopernicusClient) downloadData(ctx context.Context, requestURL string, dest io.Writer) error {
	req, err := http.NewRequestWithContext(ctx, "GET", requestURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	
	// Set basic authentication
	req.SetBasicAuth(c.username, c.password)
	
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	
	// Check HTTP status
	if resp.StatusCode != http.StatusOK {
		// Read a snippet of the response body for error context
		bodySnippet := make([]byte, 512)
		n, _ := io.ReadFull(resp.Body, bodySnippet)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodySnippet[:n]))
	}
	
	// Stream response body to destination
	_, err = io.Copy(dest, resp.Body)
	if err != nil {
		return fmt.Errorf("failed to write response: %w", err)
	}
	
	return nil
}

// isRetryableError determines if an error should trigger a retry
func isRetryableError(err error) bool {
	if err == nil {
		return false
	}
	
	errStr := err.Error()
	
	// Retry on 5xx server errors
	for code := 500; code < 600; code++ {
		if strings.Contains(errStr, fmt.Sprintf("HTTP %d", code)) {
			return true
		}
	}
	
	// Retry on common network errors
	retryablePatterns := []string{
		"timeout",
		"connection reset",
		"connection refused",
		"temporary failure",
		"EOF",
	}
	
	for _, pattern := range retryablePatterns {
		if strings.Contains(errStr, pattern) {
			return true
		}
	}
	
	return false
}

// formatFloat formats a float64 to string with appropriate precision
func formatFloat(f float64) string {
	return strconv.FormatFloat(f, 'f', 6, 64)
}

// HealthCheck verifies the Copernicus service is accessible
func (c *CopernicusClient) HealthCheck(ctx context.Context) error {
	if c.endpoint == "" {
		return fmt.Errorf("endpoint not configured")
	}
	
	// Parse endpoint URL
	u, err := url.Parse(c.endpoint)
	if err != nil {
		return fmt.Errorf("invalid endpoint URL: %w", err)
	}
	
	// Build a minimal health check request
	q := u.Query()
	q.Set("action", "describeproduct")
	q.Set("service", c.config.ServiceID)
	u.RawQuery = q.Encode()
	
	req, err := http.NewRequestWithContext(ctx, "GET", u.String(), nil)
	if err != nil {
		return fmt.Errorf("failed to create health check request: %w", err)
	}
	
	// Set basic authentication
	req.SetBasicAuth(c.username, c.password)
	
	// Use shorter timeout for health check
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("health check request failed: %w", err)
	}
	defer resp.Body.Close()
	
	// Accept both 200 OK and 401 Unauthorized as "service is up"
	// 401 means the endpoint is reachable but credentials might be invalid
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusUnauthorized {
		return fmt.Errorf("health check failed with status: %d", resp.StatusCode)
	}
	
	return nil
}

// NOAAClient implements ExternalDataClient for NOAA data services
type NOAAClient struct {
	gfsEndpoint string
	ww3Endpoint string
}

// NewNOAAClient creates a new NOAA client
func NewNOAAClient(gfsEndpoint, ww3Endpoint string) *NOAAClient {
	if gfsEndpoint == "" {
		gfsEndpoint = "https://nomads.ncep.noaa.gov/dods/gfs_0p25"
	}
	if ww3Endpoint == "" {
		ww3Endpoint = "https://nomads.ncep.noaa.gov/dods/wave/gfswave"
	}
	
	return &NOAAClient{
		gfsEndpoint: gfsEndpoint,
		ww3Endpoint: ww3Endpoint,
	}
}

// FetchWindData fetches wind data from NOAA GFS
func (c *NOAAClient) FetchWindData(ctx context.Context, req *models.DataRequest) (string, error) {
	// TODO: Implement GFS wind data fetching
	// This would involve:
	// 1. Determining the appropriate GFS forecast run
	// 2. Constructing OPeNDAP URL with subsetting parameters
	// 3. Downloading wind U and V components
	// 4. Converting to NetCDF format expected by OpenDrift
	// 5. Returning the file path
	
	return "", fmt.Errorf("NOAA GFS wind data fetching not yet implemented")
}

// FetchWaveData fetches wave data from NOAA WaveWatch III
func (c *NOAAClient) FetchWaveData(ctx context.Context, req *models.DataRequest) (string, error) {
	// TODO: Implement WaveWatch III data fetching
	// Similar process to wind data but for wave parameters
	
	return "", fmt.Errorf("NOAA WaveWatch III wave data fetching not yet implemented")
}

// FetchData implements ExternalDataClient interface
func (c *NOAAClient) FetchData(ctx context.Context, req *models.DataRequest) (string, error) {
	switch req.DataType {
	case models.DataTypeWind:
		return c.FetchWindData(ctx, req)
	case models.DataTypeWaves:
		return c.FetchWaveData(ctx, req)
	default:
		return "", fmt.Errorf("unsupported data type for NOAA client: %s", req.DataType)
	}
}

// HealthCheck verifies NOAA services are accessible
func (c *NOAAClient) HealthCheck(ctx context.Context) error {
	// TODO: Implement health check
	return nil
}

// DataClientFactory creates appropriate clients based on data type
type DataClientFactory struct {
	copernicusClient *CopernicusClient
	noaaClient       *NOAAClient
}

// NewDataClientFactory creates a new factory with configured clients
func NewDataClientFactory(copernicusEndpoint, copernicusUser, copernicusPass string) *DataClientFactory {
	return &DataClientFactory{
		copernicusClient: NewCopernicusClient(copernicusEndpoint, copernicusUser, copernicusPass),
		noaaClient:       NewNOAAClient("", ""),
	}
}

// GetClient returns the appropriate client for a data type
func (f *DataClientFactory) GetClient(dataType models.DataType) (ExternalDataClient, error) {
	switch dataType {
	case models.DataTypeOceanCurrents:
		return f.copernicusClient, nil
	case models.DataTypeWind:
		return f.noaaClient, nil
	case models.DataTypeWaves:
		return f.noaaClient, nil
	default:
		return nil, fmt.Errorf("unknown data type: %s", dataType)
	}
}

// Example of how to use the clients:
//
// ```go
// factory := NewDataClientFactory(
//     "https://my.cmems-du.eu/motu-web/Motu",
//     "username",
//     "password",
// )
//
// client, err := factory.GetClient(models.DataTypeOceanCurrents)
// if err != nil {
//     return err
// }
//
// filePath, err := client.FetchData(ctx, request)
// if err != nil {
//     return err
// }
// ```
