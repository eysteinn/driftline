# Testing the Mission Flow

This directory contains comprehensive testing tools for verifying the mission creation, processing, and results retrieval flow.

## Test Files

### 1. `test_smoke.py` - Structural Validation
**Purpose**: Validates code structure and integration points without requiring running services.

**What it tests**:
- Worker code structure (classes, methods)
- Job data format and serialization
- Database schema (tables, columns)
- API structure (endpoints, handlers)
- Integration points (queue names, data structures)
- Docker Compose configuration

**Usage**:
```bash
python3 test_smoke.py
```

**Expected result**: All 6 tests should pass, confirming the code is properly structured.

---

### 2. `test_mission_flow.py` - Integration Tests
**Purpose**: Comprehensive integration testing of the complete mission flow.

**Requirements**:
- All services must be running (see Quick Start below)
- Python packages: `requests`, `redis`, `psycopg2-binary`, `boto3`

**What it tests**:
1. API health check
2. Redis connectivity
3. PostgreSQL connectivity
4. MinIO S3 connectivity
5. User registration
6. Mission creation
7. Job enqueueing to Redis
8. Mission status retrieval
9. Mission details retrieval
10. Mission listing

**Installation**:
```bash
pip install requests redis psycopg2-binary boto3
```

**Usage**:
```bash
python3 test_mission_flow.py
```

**Expected result**: All 10 tests should pass, demonstrating end-to-end functionality.

---

### 3. `test_mission_flow.sh` - Quick Bash Test
**Purpose**: Simple bash script to quickly test the flow using curl.

**Requirements**:
- All services running
- `curl` command available
- Optional: `docker` command for Redis queue inspection

**What it tests**:
1. API health
2. User registration
3. Mission creation
4. Mission status
5. Mission listing
6. Redis queue (if Docker available)

**Usage**:
```bash
./test_mission_flow.sh
```

**Expected result**: All checks pass, mission created with status "queued" or "processing".

---

### 4. `MISSION_FLOW_VERIFICATION.md` - Manual Testing Guide
**Purpose**: Step-by-step manual verification procedures.

**Contents**:
- Infrastructure verification steps
- API endpoint testing with curl commands
- Database queries
- S3 storage verification
- Troubleshooting guide
- Performance expectations

**Usage**: Follow the guide to manually verify each component of the flow.

---

### 5. `MISSION_FLOW_VALIDATION.md` - Validation Report
**Purpose**: Complete documentation of validation results.

**Contents**:
- Components verified
- Integration points confirmed
- Data flow diagram
- Test results
- Known issues
- Recommendations

**Usage**: Review this document to understand what has been validated.

---

## Quick Start

### Start All Services

```bash
# Start services
cd /home/runner/work/driftline/driftline
docker compose -f docker-compose.dev.yml up -d

# Wait for services to be healthy (30-60 seconds)
docker compose -f docker-compose.dev.yml ps

# Check logs
docker compose -f docker-compose.dev.yml logs -f
```

### Run Tests

```bash
# 1. Structural validation (no services needed)
python3 test_smoke.py

# 2. Quick bash test (services needed)
./test_mission_flow.sh

# 3. Full integration test (services + Python packages needed)
pip install requests redis psycopg2-binary boto3
python3 test_mission_flow.py
```

### Monitor Processing

```bash
# Watch drift worker logs
docker compose -f docker-compose.dev.yml logs -f drift-worker

# Check Redis queue
docker exec driftline-redis redis-cli LLEN drift_jobs

# Check mission in database
docker exec -it driftline-postgres psql -U driftline_user -d driftline \
  -c "SELECT id, name, status, created_at FROM missions ORDER BY created_at DESC LIMIT 5;"

# Check results
docker exec -it driftline-postgres psql -U driftline_user -d driftline \
  -c "SELECT mission_id, netcdf_path, created_at FROM mission_results ORDER BY created_at DESC LIMIT 5;"
```

## Test Scenarios

### Scenario 1: Happy Path
1. User registers
2. User logs in
3. User creates mission
4. Mission is queued
5. Worker picks up job
6. Worker processes simulation
7. Worker uploads results to S3
8. Worker updates database
9. User retrieves results

**Expected**: All steps succeed, status progresses from "created" → "queued" → "processing" → "completed"

### Scenario 2: Multiple Missions
1. User creates 3 missions simultaneously
2. All missions are queued
3. Worker processes them sequentially
4. All complete successfully
5. User can list all missions
6. User can retrieve results for each

**Expected**: All missions complete, queue processes in order

### Scenario 3: Invalid Input
1. User tries to create mission with invalid coordinates (lat > 90)
2. User tries to create mission with past time
3. User tries to access another user's mission

**Expected**: API returns appropriate error messages

### Scenario 4: Worker Restart
1. Create mission
2. Wait for worker to start processing
3. Restart worker
4. Worker resumes from queue

**Expected**: Mission eventually completes after worker restart

### Scenario 5: Data Persistence
1. Create and complete mission
2. Restart all services
3. Query mission again

**Expected**: Mission data and results still accessible

## Troubleshooting

### Services not starting
```bash
# Check Docker
docker version

# Check logs
docker compose -f docker-compose.dev.yml logs

# Restart
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### Tests failing
```bash
# Check service health
docker compose -f docker-compose.dev.yml ps

# Check API
curl http://localhost:8000/health

# Check database
docker exec -it driftline-postgres psql -U driftline_user -d driftline -c "SELECT version();"

# Check Redis
docker exec -it driftline-redis redis-cli PING

# Check MinIO
curl http://localhost:9000/minio/health/live
```

### Worker not processing
```bash
# Check worker is running
docker compose -f docker-compose.dev.yml ps drift-worker

# Check worker logs
docker compose -f docker-compose.dev.yml logs drift-worker

# Check Redis queue
docker exec driftline-redis redis-cli LLEN drift_jobs

# Restart worker
docker compose -f docker-compose.dev.yml restart drift-worker
```

### Mission stuck in "queued"
- Check worker logs for errors
- Verify Redis connection
- Check queue has jobs: `docker exec driftline-redis redis-cli LLEN drift_jobs`
- Restart worker if needed

### Mission failed
- Check worker logs: `docker compose -f docker-compose.dev.yml logs drift-worker`
- Check error_message in database: `docker exec -it driftline-postgres psql -U driftline_user -d driftline -c "SELECT id, name, status, error_message FROM missions WHERE status = 'failed';"`

## Performance Benchmarks

Expected processing times:
- Mission creation: < 1 second
- Job queuing: < 1 second  
- Worker pickup: < 10 seconds
- Simulation (100 particles, 24h): 30-120 seconds
- Results upload: < 5 seconds
- Status retrieval: < 1 second

Total end-to-end: 1-2 minutes for simple missions

## Success Criteria

The mission flow is working correctly if:

1. ✅ All smoke tests pass
2. ✅ Services start successfully
3. ✅ User can register and login
4. ✅ Mission can be created
5. ✅ Job appears in Redis queue
6. ✅ Worker picks up and processes job
7. ✅ Mission status updates correctly
8. ✅ Results are stored in S3
9. ✅ Results are stored in database
10. ✅ User can retrieve results
11. ✅ Data persists across restarts

## Additional Resources

- `ARCHITECTURE.md` - System architecture documentation
- `README.md` - General project documentation
- `API_INTEGRATION_SUMMARY.md` - API integration details
- `services/drift-worker/worker.py` - Worker implementation
- `services/api/internal/handlers/missions.go` - Mission handlers

## Support

If tests continue to fail after troubleshooting:
1. Check GitHub Issues
2. Review error logs carefully
3. Ensure all environment variables are set correctly
4. Verify Docker has sufficient resources (4GB+ RAM recommended)
5. Check network connectivity between containers

---

**Last Updated**: January 2026  
**Status**: Verified and Ready for Testing
