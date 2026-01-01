# Drift Worker

The Drift Worker is a Python service that executes OpenDrift Leeway simulations for SAR (Search and Rescue) drift forecasting missions.

## Features

- Redis queue-based job processing
- OpenDrift Leeway model integration
- S3/MinIO integration for data and results
- PostgreSQL database for mission status tracking
- Configurable simulation parameters
- Error handling and automatic reconnection
- Detailed logging

## Architecture

The worker:
1. Polls a Redis queue for new drift simulation jobs
2. Downloads required forcing data (ocean currents, wind, waves) from S3
3. Initializes and runs OpenDrift Leeway model
4. Exports results to NetCDF format
5. Uploads results to S3
6. Updates mission status in PostgreSQL database

## Configuration

Configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `S3_ENDPOINT` | MinIO/S3 endpoint URL | Required |
| `S3_ACCESS_KEY` | S3 access key | Required |
| `S3_SECRET_KEY` | S3 secret key | Required |
| `MAX_CONCURRENT_JOBS` | Maximum concurrent jobs | `2` |
| `QUEUE_NAME` | Redis queue name | `drift_jobs` |
| `POLL_INTERVAL` | Queue polling interval (seconds) | `5` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Job Format

Jobs are JSON objects pushed to the Redis queue with the following structure:

```json
{
  "mission_id": "uuid-here",
  "params": {
    "latitude": 60.5,
    "longitude": -3.2,
    "start_time": "2024-01-01T12:00:00Z",
    "duration_hours": 24,
    "num_particles": 1000,
    "object_type": 1
  }
}
```

### Object Types (Leeway Categories)

The `object_type` parameter corresponds to Leeway object categories:

- `1`: Person-in-water (PIW)
- `2`: Life raft with canopy
- `3`: Life raft without canopy
- `4`: Sailing vessel
- `5`: Fishing vessel
- `6`: Power boat
- And more (see OpenDrift Leeway documentation)

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/driftline"
export REDIS_URL="redis://localhost:6379/0"
export S3_ENDPOINT="http://localhost:9000"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin"
export LOG_LEVEL="DEBUG"

# Run worker
python worker.py
```

### Docker Development

```bash
# Build image
docker build -t driftline-drift-worker .

# Run container
docker run -e DATABASE_URL=... -e REDIS_URL=... driftline-drift-worker
```

## Testing

To test the worker, push a job to the Redis queue:

```python
import redis
import json

r = redis.from_url('redis://localhost:6379/0')
job = {
    "mission_id": "test-mission-123",
    "params": {
        "latitude": 60.0,
        "longitude": -3.0,
        "start_time": "2024-01-01T12:00:00Z",
        "duration_hours": 24,
        "num_particles": 100,
        "object_type": 1
    }
}
r.rpush('drift_jobs', json.dumps(job))
```

## Dependencies

Main dependencies:
- `opendrift>=1.11.0` - Lagrangian particle tracking framework
- `redis>=4.5.0` - Redis client for job queue
- `psycopg2-binary>=2.9.0` - PostgreSQL client
- `boto3>=1.26.0` - S3 client for MinIO
- `numpy`, `scipy`, `xarray` - Scientific computing
- `netCDF4` - NetCDF file handling

## Output Format

The worker produces:
- **NetCDF density map** (`particles.nc`) - Contains particle positions and probability density
- **Animation** (optional) - MP4 video of particle drift

Results are uploaded to S3 at: `s3://driftline-results/{mission_id}/raw/particles.nc`

## Error Handling

- Automatic reconnection on Redis/DB connection loss
- Detailed error logging with stack traces
- Mission status updates on failure
- Temporary file cleanup

## Scaling

The worker is designed to be horizontally scalable:
- Multiple workers can poll the same Redis queue
- Each worker processes one job at a time by default
- Configure `MAX_CONCURRENT_JOBS` to process multiple jobs per worker

Example scaling in docker-compose:

```yaml
drift-worker:
  deploy:
    replicas: 3
```

## Monitoring

Key log messages to monitor:
- `Connected to Redis/PostgreSQL/S3` - Successful initialization
- `Received job from queue` - Job picked up
- `Mission {id} completed successfully` - Successful completion
- `Mission {id} failed: {error}` - Job failure
- `Redis connection error` - Connection issues

## Future Enhancements

- [ ] Support for multiple forcing data sources (NOAA, Copernicus)
- [ ] Real-time data ingestion
- [ ] Advanced Leeway configuration options
- [ ] Ensemble simulations
- [ ] Result validation and quality checks
- [ ] Metrics and performance monitoring
- [ ] Graceful shutdown and job retry mechanisms
