# Mission Flow Verification Guide

This document provides a comprehensive guide to verify that the complete mission creation, processing, and results retrieval flow works correctly.

## Overview

The mission flow involves:
1. **User** creates a mission via Frontend or API
2. **API Server** validates and stores mission in PostgreSQL
3. **API Server** enqueues job in Redis queue
4. **Drift Worker** picks up job from Redis
5. **Drift Worker** runs OpenDrift simulation
6. **Drift Worker** uploads results to MinIO (S3)
7. **Drift Worker** updates mission status in PostgreSQL
8. **User** retrieves results via API

## Prerequisites

Before testing, ensure all services are running:

```bash
cd /home/runner/work/driftline/driftline
docker compose -f docker-compose.dev.yml up -d
```

Wait for all services to be healthy:

```bash
docker compose -f docker-compose.dev.yml ps
```

Expected services:
- `driftline-postgres` (PostgreSQL)
- `driftline-redis` (Redis)
- `driftline-minio` (MinIO S3)
- `driftline-api` (API Server)
- `driftline-drift-worker` (Drift Worker)
- `driftline-data-service` (Data Service)
- `driftline-results-processor` (Results Processor)
- `driftline-frontend` (Frontend)
- `driftline-nginx` (Reverse Proxy)

## Manual Verification Steps

### Step 1: Verify Infrastructure

#### PostgreSQL Database
```bash
docker exec -it driftline-postgres psql -U driftline_user -d driftline -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
```

Expected tables: `users`, `missions`, `mission_results`, `api_keys`, `subscriptions`, `usage_records`, `invoices`, `audit_logs`

#### Redis
```bash
docker exec -it driftline-redis redis-cli PING
```

Expected output: `PONG`

#### MinIO S3
Open browser to: http://localhost:9001
Login with: `minioadmin` / `minioadmin`

### Step 2: Test API Health

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "service": "driftline-api"
}
```

### Step 3: Register a Test User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "fullName": "Test User"
  }'
```

Expected output:
```json
{
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "user": {
      "id": "uuid",
      "email": "test@example.com",
      "fullName": "Test User",
      ...
    }
  }
}
```

Save the `accessToken` for subsequent requests.

### Step 4: Create a Mission

```bash
export ACCESS_TOKEN="<your_access_token_from_step_3>"

curl -X POST http://localhost:8000/api/v1/missions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "name": "Test Mission",
    "description": "Integration test mission",
    "lastKnownLat": 60.0,
    "lastKnownLon": -3.0,
    "lastKnownTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "objectType": "1",
    "forecastHours": 24,
    "ensembleSize": 100
  }'
```

Expected output:
```json
{
  "data": {
    "id": "uuid",
    "name": "Test Mission",
    "status": "queued",
    ...
  }
}
```

Save the mission `id` for subsequent requests.

### Step 5: Verify Job in Redis Queue

```bash
docker exec -it driftline-redis redis-cli LLEN drift_jobs
```

Expected output: `1` (or more if multiple jobs are queued)

To inspect the job:
```bash
docker exec -it driftline-redis redis-cli LINDEX drift_jobs 0
```

Expected: JSON string with mission parameters

### Step 6: Monitor Drift Worker

Check worker logs to see if it picks up the job:

```bash
docker compose -f docker-compose.dev.yml logs -f drift-worker
```

Expected log entries:
- "Received job from queue"
- "Processing mission <mission_id>"
- "Running simulation"
- "Uploaded results to s3://..."
- "Mission <mission_id> completed successfully"

### Step 7: Check Mission Status

```bash
export MISSION_ID="<mission_id_from_step_4>"

curl http://localhost:8000/api/v1/missions/$MISSION_ID/status \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Expected output:
```json
{
  "data": {
    "status": "processing" | "completed" | "failed"
  }
}
```

Check status periodically until it becomes `completed`.

### Step 8: Verify Results in Database

```bash
docker exec -it driftline-postgres psql -U driftline_user -d driftline -c \
  "SELECT id, status, completed_at FROM missions WHERE id = '<mission_id>';"
```

Expected: Status should be `completed` with a `completed_at` timestamp.

Check for results:
```bash
docker exec -it driftline-postgres psql -U driftline_user -d driftline -c \
  "SELECT id, mission_id, netcdf_path FROM mission_results WHERE mission_id = '<mission_id>';"
```

Expected: One or more result rows with S3 paths.

### Step 9: Verify Results in MinIO

1. Open MinIO Console: http://localhost:9001
2. Login with: `minioadmin` / `minioadmin`
3. Navigate to bucket: `driftline-results`
4. Look for folder: `<mission_id>/`
5. Verify file exists: `<mission_id>/raw/particles.nc`

### Step 10: Retrieve Results via API

```bash
curl http://localhost:8000/api/v1/missions/$MISSION_ID/results \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Expected output:
```json
{
  "data": {
    "id": "uuid",
    "missionId": "uuid",
    "netcdfPath": "s3://driftline-results/<mission_id>/raw/particles.nc",
    ...
  }
}
```

### Step 11: List All Missions

```bash
curl http://localhost:8000/api/v1/missions \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Expected output:
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Test Mission",
      "status": "completed",
      ...
    }
  ],
  "total": 1,
  "page": 1,
  "perPage": 50
}
```

## Automated Test Script

Run the automated integration test:

```bash
cd /home/runner/work/driftline/driftline
pip install requests redis psycopg2-binary boto3
python test_mission_flow.py
```

This script will:
- Test all service connections
- Register a test user
- Create a test mission
- Verify job queuing
- Check mission status and retrieval
- Generate a test report

## Common Issues and Troubleshooting

### Issue: Services not starting

**Solution:**
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### Issue: Database schema not initialized

**Solution:**
```bash
docker exec -i driftline-postgres psql -U driftline_user -d driftline < sql/init/01_schema.sql
```

### Issue: Redis queue not being processed

**Check:**
- Is drift-worker running? `docker compose -f docker-compose.dev.yml ps drift-worker`
- Check worker logs: `docker compose -f docker-compose.dev.yml logs drift-worker`
- Verify Redis connection in worker logs

### Issue: Mission stuck in "queued" status

**Check:**
1. Drift worker logs for errors
2. Redis queue: `docker exec -it driftline-redis redis-cli LLEN drift_jobs`
3. If queue has jobs but worker isn't processing, restart worker:
   ```bash
   docker compose -f docker-compose.dev.yml restart drift-worker
   ```

### Issue: Results not accessible

**Check:**
1. Mission status is "completed"
2. Mission_results table has entry for the mission
3. MinIO has the file at the specified path
4. Results processor completed successfully

## Success Criteria

The mission flow is working correctly if:

1. ✅ User can register and get JWT token
2. ✅ User can create a mission with valid parameters
3. ✅ Mission is stored in database with "queued" status
4. ✅ Job is added to Redis queue
5. ✅ Drift worker picks up and processes the job
6. ✅ Simulation completes and results are uploaded to MinIO
7. ✅ Mission status updates to "completed"
8. ✅ Results are stored in mission_results table
9. ✅ User can retrieve mission status via API
10. ✅ User can retrieve mission results via API
11. ✅ Results remain accessible after system restarts

## Performance Expectations

- Mission creation: < 1 second
- Job queuing: < 1 second
- Worker pickup: < 10 seconds
- Simulation (100 particles, 24 hours): 30-120 seconds
- Results upload: < 5 seconds
- Status retrieval: < 1 second
- Results retrieval: < 1 second

## Data Persistence Verification

To verify data persists across restarts:

1. Create a mission and wait for completion
2. Note the mission ID and results
3. Restart all services:
   ```bash
   docker compose -f docker-compose.dev.yml restart
   ```
4. Wait for services to be healthy
5. Query the mission and results again
6. Verify data is unchanged

## Security Verification

1. ✅ Protected endpoints require valid JWT
2. ✅ Users can only access their own missions
3. ✅ Invalid tokens are rejected
4. ✅ Expired tokens are rejected
5. ✅ Users cannot access other users' missions

Test with invalid token:
```bash
curl http://localhost:8000/api/v1/missions \
  -H "Authorization: Bearer invalid_token"
```

Expected: 401 Unauthorized

## Conclusion

If all steps above pass successfully, the mission flow is fully functional and integrated. The system can:
- Accept user mission requests
- Process them asynchronously
- Store results persistently
- Make results accessible to users

Document any failures or issues in the PR for investigation and resolution.
