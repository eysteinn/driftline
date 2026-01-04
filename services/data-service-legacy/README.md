# Data Service

The Data Service is responsible for managing environmental forcing data required for drift simulations. It provides a REST API for fetching, caching, and serving ocean currents, wind, and wave data.

## Architecture

The service is built with Go and follows a layered architecture:

```
cmd/data-service/       # Application entry point
internal/
  ├── models/           # Data models and types
  ├── handlers/         # HTTP request handlers
  ├── services/         # Business logic
  ├── cache/            # Redis caching layer
  └── storage/          # MinIO/S3 storage layer
```

## Features

- **Environmental Data Types**:
  - Ocean currents (Copernicus Marine Service)
  - Wind data (NOAA GFS)
  - Wave data (NOAA WaveWatch III)

- **Spatial & Temporal Subsetting**:
  - Bounding box filtering (lat/lon)
  - Time range selection

- **Caching Strategy**:
  - Redis-based caching with configurable TTL
  - Automatic cache key generation
  - Cache hit/miss tracking

- **Storage Integration**:
  - MinIO/S3 compatible storage
  - Organized bucket structure by data type and date

## API Endpoints

### Health Check
```bash
GET /health
```

Returns service health status and availability of dependencies.

### Ocean Currents
```bash
GET /v1/data/ocean-currents?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

### Wind Data
```bash
GET /v1/data/wind?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

### Wave Data
```bash
GET /v1/data/waves?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

### Query Parameters

All data endpoints support the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `min_lat` | float | Yes | Minimum latitude (-90 to 90) |
| `max_lat` | float | Yes | Maximum latitude (-90 to 90) |
| `min_lon` | float | Yes | Minimum longitude (-180 to 180) |
| `max_lon` | float | Yes | Maximum longitude (-180 to 180) |
| `start_time` | string | Yes | Start time (RFC3339 format) |
| `end_time` | string | Yes | End time (RFC3339 format) |
| `resolution` | string | No | Desired resolution (e.g., "0.25deg") |
| `variables` | array | No | Specific variables to retrieve |

### Response Format

```json
{
  "data_type": "ocean_currents",
  "source": "Copernicus Marine Service (CMEMS)",
  "cache_hit": true,
  "file_path": "ocean_currents/2024/01/01/data.nc",
  "metadata": {
    "variables": ["eastward_sea_water_velocity", "northward_sea_water_velocity"],
    "resolution": "1/12 degree (~9km)",
    "bounds": {
      "min_lat": 60.0,
      "max_lat": 70.0,
      "min_lon": -20.0,
      "max_lon": -10.0
    },
    "time_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-02T00:00:00Z"
    }
  },
  "expires_at": "2024-01-02T00:00:00Z"
}
```

## Configuration

The service is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | HTTP server port | `8000` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/1` |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `http://localhost:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |

## Development

### Building

```bash
cd services/data-service
go mod download
go build -o data-service ./cmd/data-service
```

### Running Locally

```bash
export PORT=8000
export REDIS_URL=redis://localhost:6379/1
export S3_ENDPOINT=http://localhost:9000
export S3_ACCESS_KEY=minioadmin
export S3_SECRET_KEY=minioadmin

./data-service
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Test ocean currents endpoint
curl "http://localhost:8000/v1/data/ocean-currents?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z"
```

## Docker

### Building the Image

```bash
docker build -t driftline/data-service:latest .
```

### Running with Docker

```bash
docker run -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/1 \
  -e S3_ENDPOINT=http://minio:9000 \
  -e S3_ACCESS_KEY=minioadmin \
  -e S3_SECRET_KEY=minioadmin \
  driftline/data-service:latest
```

## Integration with Other Services

The Data Service is designed to work with:

- **Drift Worker**: Provides environmental forcing data for simulations
- **Redis**: Caches frequently accessed data
- **MinIO**: Stores raw environmental data files

## Future Enhancements

- [ ] Implement actual external data source clients (Copernicus, NOAA)
- [ ] Add data format conversion (NetCDF, Zarr, GeoTIFF)
- [ ] Implement data quality checks
- [ ] Add support for data pre-warming/prefetching
- [ ] Implement geographic grid partitioning for better caching
- [ ] Add metrics and monitoring
- [ ] Support for additional data sources (AIS, satellite data)
- [ ] Data compression and optimization

## Current Status

The service is functional with:
- ✅ Complete API structure
- ✅ Redis caching integration
- ✅ MinIO/S3 storage integration
- ✅ Request validation
- ✅ Error handling
- ✅ Graceful degradation (works without Redis/MinIO)

Pending implementation:
- ⏳ External data source clients (Copernicus, NOAA)
- ⏳ Actual data fetching and subsetting
- ⏳ NetCDF processing
- ⏳ Integration tests

## License

See the main repository LICENSE file.
