"""
Unit tests for Drift Worker
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestDriftWorker(unittest.TestCase):
    """Test cases for DriftWorker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_vars = {
            'REDIS_URL': 'redis://localhost:6379/0',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test',
            'S3_ENDPOINT': 'http://localhost:9000',
            'S3_ACCESS_KEY': 'test_key',
            'S3_SECRET_KEY': 'test_secret',
            'MAX_CONCURRENT_JOBS': '2'
        }
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
    
    def tearDown(self):
        """Clean up after tests"""
        for key in self.env_vars.keys():
            if key in os.environ:
                del os.environ[key]
    
    @patch('worker.psycopg2.connect')
    @patch('worker.redis.from_url')
    @patch('worker.boto3.client')
    def test_worker_initialization(self, mock_boto3, mock_redis, mock_psycopg2):
        """Test worker initializes correctly with environment variables"""
        # Mock connections
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client
        
        mock_db_conn = Mock()
        mock_psycopg2.return_value = mock_db_conn
        
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client
        
        # Import after mocking
        from worker import DriftWorker
        
        # Create worker
        worker = DriftWorker()
        
        # Assert connections were made
        mock_redis.assert_called_once()
        mock_psycopg2.assert_called_once_with(self.env_vars['DATABASE_URL'])
        mock_boto3.assert_called_once()
        
        # Assert configuration
        self.assertEqual(worker.max_concurrent_jobs, 2)
        self.assertEqual(worker.redis_url, self.env_vars['REDIS_URL'])
    
    @patch('worker.psycopg2.connect')
    @patch('worker.redis.from_url')
    @patch('worker.boto3.client')
    def test_update_mission_status(self, mock_boto3, mock_redis, mock_psycopg2):
        """Test mission status update in database"""
        # Mock connections
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client
        
        mock_cursor = Mock()
        mock_db_conn = Mock()
        mock_db_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_psycopg2.return_value = mock_db_conn
        
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client
        
        from worker import DriftWorker
        
        worker = DriftWorker()
        
        # Test status update
        mission_id = 'test-mission-123'
        worker._update_mission_status(mission_id, 'processing')
        
        # Verify SQL was executed
        mock_cursor.execute.assert_called()
    
    def test_job_format_validation(self):
        """Test job data format is correct"""
        job = {
            "mission_id": "test-123",
            "params": {
                "latitude": 60.0,
                "longitude": -3.0,
                "start_time": "2024-01-01T12:00:00Z",
                "duration_hours": 24,
                "num_particles": 100,
                "object_type": 1
            }
        }
        
        # Validate job structure
        self.assertIn('mission_id', job)
        self.assertIn('params', job)
        self.assertIn('latitude', job['params'])
        self.assertIn('longitude', job['params'])
        
        # Validate data types
        self.assertIsInstance(job['params']['latitude'], (int, float))
        self.assertIsInstance(job['params']['longitude'], (int, float))
        self.assertIsInstance(job['params']['duration_hours'], int)
        self.assertIsInstance(job['params']['num_particles'], int)
    
    def test_environment_validation(self):
        """Test that missing environment variables are caught"""
        # Remove required env var
        del os.environ['DATABASE_URL']
        
        # Import after removing env var
        from worker import DriftWorker
        
        # Should raise error on initialization
        with self.assertRaises(ValueError) as context:
            worker = DriftWorker()
        
        self.assertIn('DATABASE_URL', str(context.exception))


class TestJobProcessing(unittest.TestCase):
    """Test cases for job processing logic"""
    
    def test_job_serialization(self):
        """Test job can be serialized to/from JSON"""
        job = {
            "mission_id": "test-456",
            "params": {
                "latitude": 59.9,
                "longitude": -4.1,
                "start_time": "2024-01-01T12:00:00Z",
                "duration_hours": 48,
                "num_particles": 500,
                "object_type": 2
            }
        }
        
        # Serialize
        job_json = json.dumps(job)
        
        # Deserialize
        job_parsed = json.loads(job_json)
        
        # Verify
        self.assertEqual(job, job_parsed)
    
    def test_coordinate_validation(self):
        """Test coordinate values are valid"""
        valid_coords = [
            (0, 0),
            (60.0, -3.0),
            (-45.5, 170.2),
            (90, 180),
            (-90, -180)
        ]
        
        for lat, lon in valid_coords:
            self.assertTrue(-90 <= lat <= 90, f"Invalid latitude: {lat}")
            self.assertTrue(-180 <= lon <= 180, f"Invalid longitude: {lon}")


if __name__ == '__main__':
    unittest.main()
