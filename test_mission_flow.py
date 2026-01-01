#!/usr/bin/env python3
"""
Integration test for mission creation flow
Tests the entire flow from user creating a mission through to results being accessible
"""

import json
import time
import sys
import os
from datetime import datetime, timedelta

# Test configuration from environment variables with sensible defaults for development
TEST_CONFIG = {
    'api_base_url': os.getenv('API_BASE_URL', 'http://localhost:8000/api/v1'),
    'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'database_url': os.getenv('DATABASE_URL', 'postgresql://driftline_user:dev_password@localhost:5432/driftline'),
    's3_endpoint': os.getenv('S3_ENDPOINT', 'http://localhost:9000'),
    's3_access_key': os.getenv('S3_ACCESS_KEY', 'minioadmin'),
    's3_secret_key': os.getenv('S3_SECRET_KEY', 'minioadmin'),
}

class MissionFlowTest:
    """Test the complete mission flow"""
    
    def __init__(self):
        self.test_user_email = f"test_{int(time.time())}@example.com"
        self.test_user_password = "TestPassword123!"
        self.access_token = None
        self.mission_id = None
        
    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def test_api_health(self):
        """Test that API is running and responding"""
        import requests
        
        self.log("Testing API health check...")
        try:
            response = requests.get(f"{TEST_CONFIG['api_base_url'].replace('/api/v1', '')}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✓ API is healthy: {data}", "SUCCESS")
                return True
            else:
                self.log(f"✗ API returned status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Cannot connect to API: {e}", "ERROR")
            return False
    
    def test_redis_connection(self):
        """Test that Redis is accessible"""
        import redis
        
        self.log("Testing Redis connection...")
        try:
            r = redis.from_url(TEST_CONFIG['redis_url'], socket_connect_timeout=5)
            r.ping()
            self.log("✓ Redis is accessible", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"✗ Cannot connect to Redis: {e}", "ERROR")
            return False
    
    def test_database_connection(self):
        """Test that database is accessible"""
        import psycopg2
        
        self.log("Testing database connection...")
        try:
            conn = psycopg2.connect(TEST_CONFIG['database_url'])
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()
            self.log(f"✓ Database is accessible: {version}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"✗ Cannot connect to database: {e}", "ERROR")
            return False
    
    def test_s3_connection(self):
        """Test that S3/MinIO is accessible"""
        import boto3
        from botocore.client import Config
        
        self.log("Testing S3/MinIO connection...")
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=TEST_CONFIG['s3_endpoint'],
                aws_access_key_id=TEST_CONFIG['s3_access_key'],
                aws_secret_access_key=TEST_CONFIG['s3_secret_key'],
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            # List buckets to verify connection
            buckets = s3_client.list_buckets()
            self.log(f"✓ S3/MinIO is accessible, found {len(buckets['Buckets'])} buckets", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"✗ Cannot connect to S3/MinIO: {e}", "ERROR")
            return False
    
    def test_user_registration(self):
        """Test user registration"""
        import requests
        
        self.log("Testing user registration...")
        try:
            payload = {
                'email': self.test_user_email,
                'password': self.test_user_password,
                'fullName': 'Test User'
            }
            response = requests.post(
                f"{TEST_CONFIG['api_base_url']}/auth/register",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                if 'data' in data and 'accessToken' in data['data']:
                    self.access_token = data['data']['accessToken']
                    self.log(f"✓ User registered successfully", "SUCCESS")
                    return True
                else:
                    self.log(f"✗ Registration response missing token: {data}", "ERROR")
                    return False
            else:
                self.log(f"✗ Registration failed with status {response.status_code}: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Registration error: {e}", "ERROR")
            return False
    
    def test_mission_creation(self):
        """Test creating a mission"""
        import requests
        
        if not self.access_token:
            self.log("✗ Cannot test mission creation without access token", "ERROR")
            return False
        
        self.log("Testing mission creation...")
        try:
            # Create a test mission
            payload = {
                'name': 'Test Mission',
                'description': 'Integration test mission',
                'lastKnownLat': 60.0,
                'lastKnownLon': -3.0,
                'lastKnownTime': datetime.utcnow().isoformat() + 'Z',
                'objectType': '1',
                'forecastHours': 24,
                'ensembleSize': 100
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{TEST_CONFIG['api_base_url']}/missions",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                if 'data' in data and 'id' in data['data']:
                    self.mission_id = data['data']['id']
                    self.log(f"✓ Mission created: {self.mission_id}", "SUCCESS")
                    self.log(f"  Status: {data['data']['status']}", "INFO")
                    return True
                else:
                    self.log(f"✗ Mission creation response missing ID: {data}", "ERROR")
                    return False
            else:
                self.log(f"✗ Mission creation failed with status {response.status_code}: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Mission creation error: {e}", "ERROR")
            return False
    
    def test_job_in_queue(self):
        """Test that job was added to Redis queue"""
        import redis
        
        self.log("Checking if job was queued in Redis...")
        try:
            r = redis.from_url(TEST_CONFIG['redis_url'])
            queue_name = 'drift_jobs'
            queue_length = r.llen(queue_name)
            
            if queue_length > 0:
                # Peek at the last job
                job_data = r.lindex(queue_name, -1)
                if job_data:
                    job = json.loads(job_data)
                    self.log(f"✓ Job found in queue. Queue length: {queue_length}", "SUCCESS")
                    self.log(f"  Job mission ID: {job.get('mission_id')}", "INFO")
                    return True
                else:
                    self.log(f"✗ Queue has length {queue_length} but couldn't read job", "ERROR")
                    return False
            else:
                self.log(f"✗ No jobs in queue", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Error checking queue: {e}", "ERROR")
            return False
    
    def test_mission_status(self):
        """Test retrieving mission status"""
        import requests
        
        if not self.access_token or not self.mission_id:
            self.log("✗ Cannot test mission status without access token and mission ID", "ERROR")
            return False
        
        self.log("Testing mission status retrieval...")
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(
                f"{TEST_CONFIG['api_base_url']}/missions/{self.mission_id}/status",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('data', {}).get('status', 'unknown')
                self.log(f"✓ Mission status retrieved: {status}", "SUCCESS")
                return True
            else:
                self.log(f"✗ Status retrieval failed with status {response.status_code}: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Status retrieval error: {e}", "ERROR")
            return False
    
    def test_mission_retrieval(self):
        """Test retrieving mission details"""
        import requests
        
        if not self.access_token or not self.mission_id:
            self.log("✗ Cannot test mission retrieval without access token and mission ID", "ERROR")
            return False
        
        self.log("Testing mission details retrieval...")
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(
                f"{TEST_CONFIG['api_base_url']}/missions/{self.mission_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                mission = data.get('data', {})
                self.log(f"✓ Mission details retrieved", "SUCCESS")
                self.log(f"  Name: {mission.get('name')}", "INFO")
                self.log(f"  Status: {mission.get('status')}", "INFO")
                self.log(f"  Created: {mission.get('createdAt')}", "INFO")
                return True
            else:
                self.log(f"✗ Mission retrieval failed with status {response.status_code}: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Mission retrieval error: {e}", "ERROR")
            return False
    
    def test_list_missions(self):
        """Test listing missions"""
        import requests
        
        if not self.access_token:
            self.log("✗ Cannot test mission listing without access token", "ERROR")
            return False
        
        self.log("Testing mission listing...")
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(
                f"{TEST_CONFIG['api_base_url']}/missions",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                missions = data.get('data', [])
                self.log(f"✓ Mission list retrieved, found {len(missions)} mission(s)", "SUCCESS")
                return True
            else:
                self.log(f"✗ Mission listing failed with status {response.status_code}: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"✗ Mission listing error: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        self.log("=" * 60)
        self.log("Starting Mission Flow Integration Tests")
        self.log("=" * 60)
        
        tests = [
            ("API Health", self.test_api_health),
            ("Redis Connection", self.test_redis_connection),
            ("Database Connection", self.test_database_connection),
            ("S3/MinIO Connection", self.test_s3_connection),
            ("User Registration", self.test_user_registration),
            ("Mission Creation", self.test_mission_creation),
            ("Job Queuing", self.test_job_in_queue),
            ("Mission Status Retrieval", self.test_mission_status),
            ("Mission Details Retrieval", self.test_mission_retrieval),
            ("Mission Listing", self.test_list_missions),
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log("-" * 60)
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                self.log(f"✗ Unexpected error in {test_name}: {e}", "ERROR")
                results.append((test_name, False))
            time.sleep(0.5)  # Small delay between tests
        
        # Summary
        self.log("=" * 60)
        self.log("Test Summary")
        self.log("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        failed = len(results) - passed
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log("-" * 60)
        self.log(f"Total: {len(results)} tests")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        self.log("=" * 60)
        
        return failed == 0


def main():
    """Main entry point"""
    # Check dependencies
    try:
        import requests
        import redis
        import psycopg2
        import boto3
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("Install with: pip install requests redis psycopg2-binary boto3")
        sys.exit(1)
    
    tester = MissionFlowTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
