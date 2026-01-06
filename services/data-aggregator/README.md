# Data Aggregator Service

The Data Aggregator Service is responsible for collecting, storing, and managing environmental forcing data for the Driftline platform. It maintains a rolling window of datasets and ensures the latest forecast data is always available.

## Features

- **Scheduled Data Collection**: Automatically collects data from multiple sources on a configurable schedule
- **Rolling Window Management**: Maintains a 7-day rolling window of historical datasets
- **Forecast Persistence**: Retains the latest forecast data (up to 120 hours)
- **Database Tracking**: Records metadata for all available datasets in PostgreSQL
- **S3/MinIO Storage**: Caches data files in object storage for efficient retrieval
- **Automatic Cleanup**: Removes old data to manage storage and ensure freshness

## Data Sources

### NOAA GFS Wind Data
- **Source**: NOAA Global Forecast System (GFS)
- **Variables**: 10m wind components (UGRD, VGRD)
- **Resolution**: 0.25 degrees
- **Update Frequency**: Every 6 hours (00, 06, 12, 18 UTC)
- **Forecast Range**: Up to 120 hours (5 days)
- **Data Format**: GRIB2

### Copernicus Marine Ocean Currents
- **Source**: Copernicus Marine Service (CMEMS)
- **Variables**: Eastward (uo) and Northward (vo) velocities
- **Resolution**: 1/12 degree (~9km)
- **Update Frequency**: Daily
- **Forecast Range**: Up to 5 days
- **Data Format**: NetCDF

## Architecture

```
Data Aggregator Service
├── Scheduler (APScheduler)
│   ├── Data Collection Job (every 6 hours)
│   └── Cleanup Job (daily at 2 AM)
├── Collectors
│   ├── NOAA Wind Collector
│   └── Copernicus Ocean Collector
├── Services
│   ├── Database Service (PostgreSQL)
│   └── Storage Service (MinIO/S3)
└── Data Flow
    ├── Download from source
    ├── Upload to S3/MinIO
    └── Record metadata in database
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/1` |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `http://minio:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |
| `S3_BUCKET` | S3 bucket name | `environmental-data` |
| `COPERNICUS_USERNAME` | Copernicus Marine username | - |
| `COPERNICUS_PASSWORD` | Copernicus Marine password | - |
| `HISTORICAL_DAYS` | Days of historical data to maintain | `7` |
| `FORECAST_HOURS` | Hours of forecast data to collect | `120` |
| `FORECAST_INTERVAL_HOURS` | Interval between forecast hours | `3` |
| `COLLECTION_SCHEDULE` | Cron schedule for data collection | `0 */6 * * *` |
| `CLEANUP_SCHEDULE` | Cron schedule for cleanup | `0 2 * * *` |
| `MAX_DATA_AGE_DAYS` | Maximum age for data retention | `14` |

## Database Schema

### `aggregator_datasets`

Tracks all available datasets:

```sql
CREATE TABLE aggregator_datasets (
    id UUID PRIMARY KEY,
    data_type VARCHAR(50),           -- 'wind', 'ocean_currents', 'waves'
    source VARCHAR(50),               -- 'noaa_gfs', 'copernicus', etc.
    forecast_date TIMESTAMP,          -- Date of forecast run
    forecast_cycle VARCHAR(10),       -- '00', '06', '12', '18'
    valid_time_start TIMESTAMP,       -- Start of valid time range
    valid_time_end TIMESTAMP,         -- End of valid time range
    file_path VARCHAR(500),           -- S3 path to data file
    file_size_bytes BIGINT,           -- Size of file
    is_forecast BOOLEAN,              -- True for forecast, False for analysis
    created_at TIMESTAMP,             -- When record was created
    last_accessed_at TIMESTAMP        -- Last access time
);
```

### `aggregator_collection_status`

Tracks collection run status:

```sql
CREATE TABLE aggregator_collection_status (
    collection_id UUID PRIMARY KEY,
    data_type VARCHAR(50),
    status VARCHAR(20),               -- 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    records_collected INTEGER,
    error_message TEXT
);
```

## Usage

### Running with Docker

```bash
docker build -t driftline/data-aggregator:latest .

docker run -d \
  --name data-aggregator \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/driftline \
  -e S3_ENDPOINT=http://minio:9000 \
  -e COPERNICUS_USERNAME=your_username \
  -e COPERNICUS_PASSWORD=your_password \
  driftline/data-aggregator:latest
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://...
export S3_ENDPOINT=http://localhost:9000
export COPERNICUS_USERNAME=your_username
export COPERNICUS_PASSWORD=your_password

# Run the service
python -m app.main
```

## Behavior

### At Startup

1. **Historical Data Check**: Checks for the past 7 days of data
2. **Missing Data Download**: Downloads any missing historical datasets
3. **Initial Forecast**: Collects the latest forecast data
4. **Schedule Jobs**: Sets up recurring jobs for collection and cleanup

### Scheduled Collection (Every 6 Hours)

1. Finds the latest complete forecast run from NOAA
2. Downloads wind data for 0-120 hours at 3-hour intervals
3. Downloads ocean currents forecast (if credentials available)
4. Uploads files to S3/MinIO
5. Records dataset metadata in database

### Scheduled Cleanup (Daily at 2 AM)

1. Identifies datasets older than `MAX_DATA_AGE_DAYS`
2. Deletes files from S3/MinIO
3. Removes records from database
4. Logs cleanup statistics

## Integration with Other Services

The Data Aggregator Service provides data to:

- **Drift Worker**: Uses collected datasets for OpenDrift simulations
- **Data Service**: Serves data via REST API
- **API Server**: Queries available datasets for mission planning

Other services can query the `aggregator_datasets` table to find available data for specific time ranges and locations.

## Monitoring

Key metrics to monitor:

- Collection success/failure rate
- Number of datasets collected per run
- Storage space used
- Database table sizes
- Scheduler job status

## Troubleshooting

### Copernicus Data Not Collecting

- Verify `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` are set
- Check Copernicus Marine Service status
- Review logs for authentication errors

### NOAA Data Download Failures

- Check network connectivity to NOAA servers
- Verify NOAA GFS data availability (occasionally unavailable)
- Review throttling settings if rate-limited

### Storage Issues

- Ensure MinIO/S3 bucket exists and is accessible
- Check available disk space
- Verify S3 credentials are correct

### Database Connection Issues

- Verify `DATABASE_URL` is correct
- Ensure PostgreSQL is running and accessible
- Check database user permissions

## License

See the main repository LICENSE file.
