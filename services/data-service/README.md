# Data Service (Python)

The Data Service is a Python-based REST API responsible for fetching, subsetting, and caching environmental forcing data (ocean currents, wind, waves) from Copernicus Marine and NOAA sources. It leverages mature Python libraries for scientific data processing.

## Features

- **Environmental Data Types**:
  - Ocean currents from Copernicus Marine Service (CMEMS)
  - Wind data from NOAA GFS
  - Wave data from NOAA WaveWatch III

- **Data Processing**:
  - Spatial and temporal subsetting using xarray
  - NetCDF format for efficient scientific data handling
  - Automatic data quality and validation

- **Caching & Storage**:
  - Redis-based caching with configurable TTL
  - MinIO/S3 compatible storage
  - Automatic cache key generation

## Architecture

```
app/
├── main.py              # Flask application entry point
├── config.py            # Configuration management
├── models/              # Data models
│   └── data.py          # DataRequest, DataResponse, etc.
├── services/            # Business logic
│   ├── cache.py         # Redis caching service
│   ├── storage.py       # MinIO/S3 storage service
│   └── data_service.py  # Main data orchestration
├── clients/             # External data source clients
│   ├── copernicus.py    # Copernicus Marine client
│   └── noaa.py          # NOAA GFS and WaveWatch clients
└── handlers/            # HTTP request handlers
    └── data.py          # API endpoint handlers
```

## API Endpoints

### Health Check
```bash
GET /health
```

Returns service health status and availability of dependencies.

**Response:**
```json
{
  "status": "healthy",
  "service": "driftline-data-service",
  "cache": true,
  "storage": true
}
```

### Ocean Currents
```bash
GET /v1/data/ocean-currents?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

Fetch ocean currents data from Copernicus Marine Service.

### Wind Data
```bash
GET /v1/data/wind?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

Fetch wind data from NOAA GFS.

### Wave Data
```bash
GET /v1/data/waves?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
```

Fetch wave data from NOAA WaveWatch III.

### Query Parameters

All data endpoints support the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `min_lat` | float | Yes | Minimum latitude (-90 to 90) |
| `max_lat` | float | Yes | Maximum latitude (-90 to 90) |
| `min_lon` | float | Yes | Minimum longitude (-180 to 180) |
| `max_lon` | float | Yes | Maximum longitude (-180 to 180) |
| `start_time` | string | No | Start time (ISO 8601 format, defaults to now) |
| `end_time` | string | No | End time (ISO 8601 format, defaults to +48h) |
| `resolution` | string | No | Desired resolution (e.g., "0.25deg") |
| `variables` | array | No | Specific variables to retrieve |

### Response Format

```json
{
  "data_type": "ocean_currents",
  "source": "Copernicus Marine Service (CMEMS)",
  "cache_hit": true,
  "file_path": "ocean_currents/2024/01/01/data_abc123.nc",
  "file_url": "https://...",
  "metadata": {
    "variables": ["uo", "vo"],
    "time_steps": 48,
    "resolution": "1/12 degree (~9km)",
    "bounds": {
      "min_lat": 60.0,
      "max_lat": 70.0,
      "min_lon": -20.0,
      "max_lon": -10.0
    },
    "time_range": {
      "start": "2024-01-01T00:00:00+00:00",
      "end": "2024-01-02T00:00:00+00:00"
    },
    "units": {
      "uo": "m/s",
      "vo": "m/s"
    }
  },
  "expires_at": "2024-01-03T00:00:00+00:00"
}
```

## Configuration

The service is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | HTTP server port | `8000` |
| `HOST` | HTTP server host | `0.0.0.0` |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/1` |
| `CACHE_TTL` | Cache TTL in seconds | `86400` (24 hours) |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `http://localhost:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |
| `S3_BUCKET` | S3 bucket name | `environmental-data` |
| `S3_USE_SSL` | Use SSL for S3 | `false` |
| `COPERNICUS_USERNAME` | Copernicus Marine username | - |
| `COPERNICUS_PASSWORD` | Copernicus Marine password | - |
| `CMEMS_OCEAN_CURRENTS_DATASET` | CMEMS dataset ID | `cmems_mod_glo_phy_anfc_0.083deg_P1D-m` |
| `NOAA_GFS_URL` | NOAA GFS OPeNDAP URL | `https://nomads.ncep.noaa.gov/dods/gfs_0p25` |
| `NOAA_WAVEWATCH_URL` | NOAA WaveWatch OPeNDAP URL | `https://nomads.ncep.noaa.gov/dods/wave/gfswave` |

### Copernicus Marine Credentials

To access Copernicus Marine data, you need to:

1. Register at https://marine.copernicus.eu/
2. Set `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` environment variables

Without credentials, the service will work but ocean currents data cannot be fetched from Copernicus.

## Installation & Development

### Local Development

```bash
# Install dependencies
cd services/data-service
pip install -r requirements.txt

# Set environment variables
export REDIS_URL=redis://localhost:6379/1
export S3_ENDPOINT=http://localhost:9000
export S3_ACCESS_KEY=minioadmin
export S3_SECRET_KEY=minioadmin
export COPERNICUS_USERNAME=your_username
export COPERNICUS_PASSWORD=your_password

# Run the service
python -m app.main
```

### Docker

```bash
# Build image
docker build -t driftline/data-service:latest .

# Run container
docker run -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/1 \
  -e S3_ENDPOINT=http://minio:9000 \
  -e S3_ACCESS_KEY=minioadmin \
  -e S3_SECRET_KEY=minioadmin \
  -e COPERNICUS_USERNAME=your_username \
  -e COPERNICUS_PASSWORD=your_password \
  driftline/data-service:latest
```

### Docker Compose

The service is integrated into the main docker-compose setup:

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up --build

# View logs
docker-compose -f docker-compose.dev.yml logs -f data-service
```

## Testing

### Manual Testing

```bash
# Health check
curl http://localhost:8003/health

# Test ocean currents endpoint
curl "http://localhost:8003/v1/data/ocean-currents?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z"

# Test wind endpoint
curl "http://localhost:8003/v1/data/wind?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z"

# Test waves endpoint
curl "http://localhost:8003/v1/data/waves?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z"
```

## Key Libraries

- **Flask** - Web framework
- **xarray** - N-dimensional labeled arrays for scientific data
- **netCDF4** - NetCDF file format support
- **copernicusmarine** - Official Copernicus Marine client
- **pydap** - OPeNDAP client for NOAA data access
- **redis** - Redis client for caching
- **boto3** - AWS S3/MinIO client for storage

## Integration with Other Services

The Data Service integrates with:

- **Drift Worker** - Provides environmental forcing data for OpenDrift simulations
- **Redis** - Caches frequently accessed data
- **MinIO** - Stores raw environmental data files (NetCDF)

## Advantages over Go Implementation

1. **Scientific Python Ecosystem**: Direct access to xarray, netCDF4, pandas for data manipulation
2. **Mature Data Clients**: Official copernicusmarine client and established pydap for OPeNDAP
3. **Stack Unification**: Matches drift-worker's Python environment for easier maintenance
4. **Rapid Development**: Python's flexibility for data processing workflows
5. **Community Support**: Extensive oceanographic/meteorological Python community

## Migration from Go Service

The Python service is a drop-in replacement for the Go service:

- ✅ Same API endpoints and query parameters
- ✅ Same response format
- ✅ Same Redis and MinIO integration
- ✅ Compatible with existing drift-worker

The Go service has been renamed to `data-service-legacy` and is no longer used.

## License

See the main repository LICENSE file.
