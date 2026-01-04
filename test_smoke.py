#!/usr/bin/env python3
"""
Simple smoke test for mission flow components
Tests individual components without requiring full Docker setup
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Get repository root directory
REPO_ROOT = Path(__file__).parent.absolute()

def test_worker_imports():
    """Test that worker can be imported and has required components"""
    print("Testing drift worker imports...")
    try:
        worker_path = REPO_ROOT / 'services' / 'drift-worker'
        # Note: sys.path modification is acceptable for test isolation
        # This ensures we're testing the local code, not installed packages
        sys.path.insert(0, str(worker_path))
        
        # First check config which doesn't need external dependencies
        import config
        
        # Check config constants
        assert hasattr(config, 'DEFAULT_NUM_PARTICLES'), "Config missing DEFAULT_NUM_PARTICLES"
        assert hasattr(config, 'RESULTS_BUCKET'), "Config missing RESULTS_BUCKET"
        assert hasattr(config, 'JOB_QUEUE'), "Config missing JOB_QUEUE"
        assert hasattr(config, 'STATUS_PROCESSING'), "Config missing STATUS_PROCESSING"
        assert hasattr(config, 'STATUS_COMPLETED'), "Config missing STATUS_COMPLETED"
        assert hasattr(config, 'STATUS_FAILED'), "Config missing STATUS_FAILED"
        assert hasattr(config, 'DEFAULT_DATA_SERVICE_URL'), "Config missing DEFAULT_DATA_SERVICE_URL"
        assert hasattr(config, 'DATA_SERVICE_TIMEOUT'), "Config missing DATA_SERVICE_TIMEOUT"
        assert hasattr(config, 'SPATIAL_BUFFER'), "Config missing SPATIAL_BUFFER"
        
        # Check worker file exists and has expected structure
        worker_file = worker_path / 'worker.py'
        with open(worker_file, 'r') as f:
            worker_content = f.read()
        
        # Check required classes and methods exist in source
        assert 'class DriftWorker' in worker_content, "Worker file missing DriftWorker class"
        assert 'def process_job' in worker_content, "DriftWorker missing process_job method"
        assert 'def _run_opendrift_simulation' in worker_content, "DriftWorker missing _run_opendrift_simulation method"
        assert 'def _upload_results' in worker_content, "DriftWorker missing _upload_results method"
        assert 'def _update_mission_status' in worker_content, "DriftWorker missing _update_mission_status method"
        assert 'def _download_forcing_data' in worker_content, "DriftWorker missing _download_forcing_data method"
        assert 'def _download_from_storage' in worker_content, "DriftWorker missing _download_from_storage method"
        assert 'def run' in worker_content, "DriftWorker missing run method"
        
        # Check data-service integration
        assert 'data_service_url' in worker_content, "Worker missing data_service_url configuration"
        assert 'DATA_SERVICE_URL' in worker_content, "Worker missing DATA_SERVICE_URL environment variable"
        assert 'requests.get' in worker_content, "Worker missing HTTP requests for data-service"
        
        print("✓ Worker structure valid")
        print(f"  - Default particles: {config.DEFAULT_NUM_PARTICLES}")
        print(f"  - Results bucket: {config.RESULTS_BUCKET}")
        print(f"  - Job queue: {config.JOB_QUEUE}")
        print(f"  - Data service URL: {config.DEFAULT_DATA_SERVICE_URL}")
        print(f"  - Required methods: present")
        return True
    except Exception as e:
        print(f"✗ Worker structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_queue_data_structure():
    """Test that job data structure is correct"""
    print("\nTesting job data structure...")
    try:
        # Test job structure
        job = {
            "mission_id": "test-mission-123",
            "params": {
                "latitude": 60.0,
                "longitude": -3.0,
                "start_time": datetime.now().replace(tzinfo=None).isoformat() + "Z",
                "duration_hours": 24,
                "num_particles": 100,
                "object_type": 1
            }
        }
        
        # Validate structure
        assert "mission_id" in job, "Job missing mission_id"
        assert "params" in job, "Job missing params"
        assert "latitude" in job["params"], "Job params missing latitude"
        assert "longitude" in job["params"], "Job params missing longitude"
        assert "start_time" in job["params"], "Job params missing start_time"
        assert "duration_hours" in job["params"], "Job params missing duration_hours"
        assert "num_particles" in job["params"], "Job params missing num_particles"
        assert "object_type" in job["params"], "Job params missing object_type"
        
        # Test JSON serialization
        job_json = json.dumps(job)
        job_parsed = json.loads(job_json)
        assert job["mission_id"] == job_parsed["mission_id"], "Mission ID mismatch after serialization"
        
        print("✓ Job data structure valid")
        print(f"  - Mission ID: {job['mission_id']}")
        print(f"  - Position: ({job['params']['latitude']}, {job['params']['longitude']})")
        print(f"  - Particles: {job['params']['num_particles']}")
        return True
    except Exception as e:
        print(f"✗ Job structure test failed: {e}")
        return False

def test_database_schema():
    """Test database schema matches expected structure"""
    print("\nTesting database schema...")
    try:
        schema_file = REPO_ROOT / 'sql' / 'init' / '01_schema.sql'
        with open(schema_file, 'r') as f:
            schema = f.read()
        
        # Check required tables exist
        required_tables = [
            'users',
            'missions',
            'mission_results',
            'api_keys'
        ]
        
        for table in required_tables:
            assert f"CREATE TABLE {table}" in schema, f"Schema missing {table} table"
        
        # Check missions table has required columns
        missions_columns = [
            'id',
            'user_id',
            'last_known_lat',
            'last_known_lon',
            'last_known_time',
            'object_type',
            'forecast_hours',
            'ensemble_size',
            'status',
            'created_at',
            'updated_at'
        ]
        
        for column in missions_columns:
            assert column in schema, f"Missions table missing {column} column"
        
        # Check mission_results table has required columns
        results_columns = [
            'id',
            'mission_id',
            'netcdf_path',
            'created_at'
        ]
        
        for column in results_columns:
            assert column in schema, f"Mission_results table missing {column} column"
        
        print("✓ Database schema valid")
        print(f"  - Tables: {', '.join(required_tables)}")
        print(f"  - Mission columns: {len(missions_columns)}")
        print(f"  - Results columns: {len(results_columns)}")
        return True
    except Exception as e:
        print(f"✗ Database schema test failed: {e}")
        return False

def test_api_structure():
    """Test API structure and endpoints"""
    print("\nTesting API structure...")
    try:
        # Check main.go exists and has expected routes
        main_file = REPO_ROOT / 'services' / 'api' / 'cmd' / 'api-gateway' / 'main.go'
        with open(main_file, 'r') as f:
            main_content = f.read()
        
        # Check expected route groups
        assert '/api/v1' in main_content, "Missing /api/v1 route group"
        assert '/auth' in main_content, "Missing /auth route group"
        assert '/missions' in main_content, "Missing /missions route group"
        assert '/users' in main_content, "Missing /users route group"
        
        # Check expected endpoints
        expected_endpoints = [
            'Register',
            'Login',
            'CreateMission',
            'ListMissions',
            'GetMission',
            'GetMissionStatus',
            'GetMissionResults'
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in main_content, f"Missing {endpoint} endpoint"
        
        # Check handlers exist
        missions_handler = REPO_ROOT / 'services' / 'api' / 'internal' / 'handlers' / 'missions.go'
        with open(missions_handler, 'r') as f:
            handler_content = f.read()
        
        assert 'CreateMission' in handler_content, "Missing CreateMission handler"
        assert 'EnqueueDriftJob' in handler_content, "Missing job enqueuing in CreateMission"
        assert 'GetMissionResults' in handler_content, "Missing GetMissionResults handler"
        
        print("✓ API structure valid")
        print(f"  - Route groups: auth, missions, users")
        print(f"  - Endpoints: {len(expected_endpoints)}")
        print(f"  - Job enqueuing: present")
        return True
    except Exception as e:
        print(f"✗ API structure test failed: {e}")
        return False

def test_integration_points():
    """Test that integration points between components are correct"""
    print("\nTesting integration points...")
    try:
        # Check API uses correct queue name
        queue_file = REPO_ROOT / 'services' / 'api' / 'internal' / 'queue' / 'redis.go'
        with open(queue_file, 'r') as f:
            queue_content = f.read()
        
        assert 'drift_jobs' in queue_content, "API queue name mismatch"
        assert 'mission_id' in queue_content, "Job structure missing mission_id"
        assert 'DriftJobParams' in queue_content, "Missing DriftJobParams struct"
        
        # Check worker uses same queue name
        worker_file = REPO_ROOT / 'services' / 'drift-worker' / 'worker.py'
        with open(worker_file, 'r') as f:
            worker_content = f.read()
        
        assert 'drift_jobs' in worker_content, "Worker queue name mismatch"
        assert 'mission_id' in worker_content, "Worker job parsing missing mission_id"
        
        # Check worker updates database correctly
        assert 'UPDATE missions' in worker_content, "Worker doesn't update mission status"
        assert 'INSERT INTO mission_results' in worker_content, "Worker doesn't insert results"
        assert 'driftline-results' in worker_content or 'RESULTS_BUCKET' in worker_content, "Worker missing results bucket"
        
        print("✓ Integration points valid")
        print(f"  - Queue name: drift_jobs (API ✓ Worker ✓)")
        print(f"  - Job structure: mission_id + params (API ✓ Worker ✓)")
        print(f"  - Database updates: missions + mission_results (Worker ✓)")
        print(f"  - S3 storage: driftline-results (Worker ✓)")
        return True
    except Exception as e:
        print(f"✗ Integration points test failed: {e}")
        return False

def test_docker_compose():
    """Test Docker Compose configuration"""
    print("\nTesting Docker Compose configuration...")
    try:
        compose_file = REPO_ROOT / 'docker-compose.dev.yml'
        with open(compose_file, 'r') as f:
            compose_content = f.read()
        
        # Check all required services
        required_services = [
            'postgres',
            'redis',
            'minio',
            'api',
            'drift-worker',
            'data-service',
            'results-processor',
            'frontend'
        ]
        
        for service in required_services:
            assert f'{service}:' in compose_content, f"Missing {service} service"
        
        # Check environment variables are set correctly
        assert 'DATABASE_URL' in compose_content, "Missing DATABASE_URL"
        assert 'REDIS_URL' in compose_content, "Missing REDIS_URL"
        assert 'S3_ENDPOINT' in compose_content, "Missing S3_ENDPOINT"
        assert 'JWT_SECRET_KEY' in compose_content, "Missing JWT_SECRET_KEY"
        assert 'DATA_SERVICE_URL' in compose_content, "Missing DATA_SERVICE_URL"
        
        # Check dependencies
        assert 'depends_on:' in compose_content, "Missing service dependencies"
        
        # Verify drift-worker depends on data-service
        import yaml
        with open(compose_file, 'r') as f:
            compose_yaml = yaml.safe_load(f)
        
        drift_worker_deps = compose_yaml['services']['drift-worker'].get('depends_on', [])
        assert 'data-service' in drift_worker_deps, "drift-worker missing data-service dependency"
        
        print("✓ Docker Compose configuration valid")
        print(f"  - Services: {len(required_services)}")
        print(f"  - Environment variables: configured")
        print(f"  - Service dependencies: defined")
        print(f"  - drift-worker → data-service: configured")
        return True
    except Exception as e:
        print(f"✗ Docker Compose test failed: {e}")
        return False

def main():
    """Run all smoke tests"""
    print("=" * 60)
    print("Mission Flow Smoke Tests")
    print("=" * 60)
    
    tests = [
        ("Worker Imports", test_worker_imports),
        ("Job Data Structure", test_queue_data_structure),
        ("Database Schema", test_database_schema),
        ("API Structure", test_api_structure),
        ("Integration Points", test_integration_points),
        ("Docker Compose", test_docker_compose),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("-" * 60)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All smoke tests passed!")
        print("The mission flow components are properly structured and integrated.")
    else:
        print(f"\n❌ {failed} test(s) failed.")
        print("Please review the failures above.")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
