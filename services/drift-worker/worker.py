#!/usr/bin/env python3
"""
Driftline Drift Worker
Executes OpenDrift Leeway simulations for SAR missions
"""

import os
import sys
import time
import logging
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.leeway import Leeway
import numpy as np
import requests

# Import configuration
try:
    from config import (
        DEFAULT_NUM_PARTICLES, DEFAULT_DURATION_HOURS, DEFAULT_OBJECT_TYPE,
        DEFAULT_TIME_STEP, DEFAULT_OUTPUT_INTERVAL, DEFAULT_SEED_RADIUS,
        RESULTS_BUCKET, JOB_QUEUE, DENSITY_MAP_PIXEL_SIZE,
        STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED,
        DEFAULT_DATA_SERVICE_URL, DATA_SERVICE_TIMEOUT, SPATIAL_BUFFER
    )
except ImportError:
    # Fallback to defaults if config not available
    DEFAULT_NUM_PARTICLES = 1000
    DEFAULT_DURATION_HOURS = 24
    DEFAULT_OBJECT_TYPE = 1
    DEFAULT_TIME_STEP = 3600
    DEFAULT_OUTPUT_INTERVAL = 3600
    DEFAULT_SEED_RADIUS = 100
    RESULTS_BUCKET = "driftline-results"
    JOB_QUEUE = "drift_jobs"
    DENSITY_MAP_PIXEL_SIZE = 1000
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    DEFAULT_DATA_SERVICE_URL = "http://data-service:8000"
    DATA_SERVICE_TIMEOUT = 120
    SPATIAL_BUFFER = 2.0

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
# Validate log level
if log_level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
    log_level = 'INFO'

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DriftWorker:
    """Worker for processing drift simulation jobs"""
    
    def __init__(self):
        # Configuration
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.database_url = os.getenv('DATABASE_URL')
        self.s3_endpoint = os.getenv('S3_ENDPOINT')
        self.s3_access_key = os.getenv('S3_ACCESS_KEY')
        self.s3_secret_key = os.getenv('S3_SECRET_KEY')
        self.max_concurrent_jobs = int(os.getenv('MAX_CONCURRENT_JOBS', '2'))
        self.queue_name = os.getenv('QUEUE_NAME', JOB_QUEUE)
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '5'))
        self.data_service_url = os.getenv('DATA_SERVICE_URL', DEFAULT_DATA_SERVICE_URL)
        
        # Validate required configuration
        self._validate_config()
        
        # Initialize connections
        self.redis_client: Optional[redis.Redis] = None
        self.db_conn = None
        self.s3_client = None
        
        self._init_connections()
        
        logger.info(f"Initialized DriftWorker with {self.max_concurrent_jobs} max concurrent jobs")
        logger.info(f"Data Service URL: {self.data_service_url}")
    
    def _validate_config(self):
        """Validate required environment variables"""
        required_vars = [
            'DATABASE_URL', 'REDIS_URL', 'S3_ENDPOINT', 
            'S3_ACCESS_KEY', 'S3_SECRET_KEY'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def _init_connections(self):
        """Initialize Redis, database, and S3 connections"""
        try:
            # Redis connection
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            self.redis_client.ping()
            logger.info("Connected to Redis")
            
            # Database connection
            self.db_conn = psycopg2.connect(self.database_url)
            self.db_conn.autocommit = True
            logger.info("Connected to PostgreSQL")
            
            # S3 client
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            logger.info("Connected to S3/MinIO")
            
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            raise
    
    def _update_mission_status(self, mission_id: str, status: str, 
                              error_message: Optional[str] = None,
                              result_location: Optional[str] = None):
        """Update mission status in database"""
        try:
            with self.db_conn.cursor() as cur:
                if result_location:
                    cur.execute(
                        """
                        UPDATE missions 
                        SET status = %s, 
                            completed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (status, mission_id)
                    )
                    cur.execute(
                        """
                        INSERT INTO mission_results 
                        (id, mission_id, netcdf_path, created_at)
                        VALUES (gen_random_uuid(), %s, %s, CURRENT_TIMESTAMP)
                        """,
                        (mission_id, result_location)
                    )
                elif error_message:
                    cur.execute(
                        """
                        UPDATE missions 
                        SET status = %s,
                            error_message = %s,
                            completed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (status, error_message, mission_id)
                    )
                else:
                    cur.execute(
                        """
                        UPDATE missions 
                        SET status = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (status, mission_id)
                    )
            logger.info(f"Updated mission {mission_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update mission status: {e}")
            # Don't re-raise - we don't want to fail the job if DB update fails
            # The job results will still be in S3
    
    def _download_forcing_data(self, mission_params: Dict[str, Any], 
                               temp_dir: str) -> Dict[str, str]:
        """Download required forcing data from data-service API"""
        logger.info("Fetching forcing data from data-service...")
        
        forcing_files = {}
        
        # Extract mission parameters
        lat = mission_params['latitude']
        lon = mission_params['longitude']
        start_time_str = mission_params['start_time']
        duration_hours = mission_params.get('duration_hours', DEFAULT_DURATION_HOURS)
        
        # Calculate spatial bounds with buffer
        min_lat = lat - SPATIAL_BUFFER
        max_lat = lat + SPATIAL_BUFFER
        min_lon = lon - SPATIAL_BUFFER
        max_lon = lon + SPATIAL_BUFFER
        
        # Calculate end time
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Format times for API
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        
        # Data types to fetch
        data_types = [
            ('ocean-currents', 'currents.nc'),
            ('wind', 'wind.nc'),
            ('waves', 'waves.nc')
        ]
        
        for data_type, filename in data_types:
            try:
                logger.info(f"Fetching {data_type} data...")
                
                # Build request parameters
                params = {
                    'min_lat': min_lat,
                    'max_lat': max_lat,
                    'min_lon': min_lon,
                    'max_lon': max_lon,
                    'start_time': start_time_iso,
                    'end_time': end_time_iso
                }
                
                # Call data-service API
                url = f"{self.data_service_url}/v1/data/{data_type}"
                response = requests.get(url, params=params, timeout=DATA_SERVICE_TIMEOUT)
                
                if response.status_code == 200:
                    data = response.json()
                    file_path = data.get('file_path')
                    
                    if file_path:
                        # Download the file from S3/MinIO
                        local_path = os.path.join(temp_dir, filename)
                        self._download_from_storage(file_path, local_path)
                        forcing_files[data_type] = local_path
                        logger.info(f"Downloaded {data_type} data to {local_path}")
                    else:
                        logger.warning(f"No file path returned for {data_type}")
                else:
                    logger.warning(f"Failed to fetch {data_type}: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {data_type} data from data-service")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error fetching {data_type} data: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error fetching {data_type}: {e}")
        
        if forcing_files:
            logger.info(f"Successfully fetched {len(forcing_files)} forcing data files")
        else:
            logger.warning("No forcing data files obtained, will use fallback conditions")
        
        return forcing_files
    
    def _download_from_storage(self, s3_path: str, local_path: str):
        """Download a file from S3/MinIO storage"""
        # Parse S3 path (format: bucket/path/to/file.nc or s3://bucket/path/to/file.nc)
        if not s3_path:
            raise ValueError("S3 path cannot be empty")
        
        # Remove s3:// prefix if present
        s3_path = s3_path.replace('s3://', '')
        
        # Split on first slash to separate bucket from key
        parts = s3_path.split('/', 1)
        
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 path format: {s3_path}. Expected format: 'bucket/path/to/file' or 's3://bucket/path/to/file'")
        
        bucket = parts[0]
        key = parts[1]
        
        if not bucket or not key:
            raise ValueError(f"Invalid S3 path: bucket and key cannot be empty")
        
        logger.debug(f"Downloading from S3: bucket={bucket}, key={key}")
        self.s3_client.download_file(bucket, key, local_path)
    
    def _upload_results(self, mission_id: str, result_file: str) -> str:
        """Upload simulation results to S3"""
        bucket = RESULTS_BUCKET
        key = f"{mission_id}/raw/particles.nc"
        
        try:
            # Ensure bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ('404', 'NoSuchBucket'):
                    self.s3_client.create_bucket(Bucket=bucket)
                    logger.info(f"Created bucket: {bucket}")
                else:
                    raise
            
            # Upload file
            self.s3_client.upload_file(result_file, bucket, key)
            s3_path = f"s3://{bucket}/{key}"
            logger.info(f"Uploaded results to {s3_path}")
            return s3_path
            
        except Exception as e:
            logger.error(f"Failed to upload results: {e}")
            raise
    
    def _enqueue_results_processing(self, mission_id: str, netcdf_path: str):
        """Enqueue a results processing job to Redis"""
        results_queue = os.getenv('RESULTS_QUEUE', 'results_processing')
        
        job_data = {
            'mission_id': mission_id,
            'netcdf_path': netcdf_path
        }
        
        try:
            self.redis_client.rpush(results_queue, json.dumps(job_data))
            logger.info(f"Enqueued results processing job for mission {mission_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue results processing job: {e}")
            # Don't fail the main job if we can't enqueue results processing
    
    def _run_opendrift_simulation(self, mission_params: Dict[str, Any], 
                                  forcing_files: Dict[str, str],
                                  output_file: str):
        """Execute OpenDrift Leeway simulation"""
        logger.info("Initializing OpenDrift Leeway model...")
        
        # Extract mission parameters with defaults
        lat = mission_params['latitude']
        lon = mission_params['longitude']
        # Parse datetime and remove timezone info (OpenDrift expects naive datetimes)
        start_time_str = mission_params['start_time'].replace('Z', '+00:00')
        start_time = datetime.fromisoformat(start_time_str)
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        duration_hours = mission_params.get('duration_hours', DEFAULT_DURATION_HOURS)
        num_particles = mission_params.get('num_particles', DEFAULT_NUM_PARTICLES)
        object_type = mission_params.get('object_type', DEFAULT_OBJECT_TYPE)
        
        # Initialize Leeway model
        o = Leeway(loglevel=logging.WARNING)
        
        # Add readers for forcing data if available
        readers_added = False
        if forcing_files:
            logger.info("Adding environmental data readers from data-service...")
            
            for data_type, file_path in forcing_files.items():
                try:
                    logger.info(f"Adding reader for {data_type}: {file_path}")
                    reader = reader_netCDF_CF_generic.Reader(file_path)
                    o.add_reader(reader)
                    readers_added = True
                    logger.info(f"Successfully added {data_type} reader")
                except Exception as e:
                    logger.warning(f"Failed to add reader for {data_type}: {e}")
        
        # Use fallback conditions if no readers were successfully added
        if not readers_added:
            logger.info("Using constant environmental conditions (fallback mode)")
            o.set_config('environment:fallback:x_wind', 3.0)  # 3 m/s eastward wind
            o.set_config('environment:fallback:y_wind', 2.0)  # 2 m/s northward wind
            o.set_config('environment:fallback:x_sea_water_velocity', 0.2)  # 0.2 m/s eastward current
            o.set_config('environment:fallback:y_sea_water_velocity', 0.1)  # 0.1 m/s northward current
        
        # Seed particles at last known position
        logger.info(f"Seeding {num_particles} particles at ({lat}, {lon})")
        o.seed_elements(
            lon=lon,
            lat=lat,
            radius=DEFAULT_SEED_RADIUS,
            number=num_particles,
            time=start_time,
            object_type=object_type
        )
        
        # Run simulation
        end_time = start_time + timedelta(hours=duration_hours)
        logger.info(f"Running simulation from {start_time} to {end_time}")
        logger.info(f"Exporting trajectory results to {output_file}")
        
        o.run(
            end_time=end_time,
            time_step=DEFAULT_TIME_STEP,
            time_step_output=DEFAULT_OUTPUT_INTERVAL,
            outfile=output_file
        )
        
        # Also export animation (optional)
        try:
            animation_file = output_file.replace('.nc', '_animation.mp4')
            o.animation(
                filename=animation_file,
                fast=False
            )
            logger.info(f"Created animation: {animation_file}")
        except Exception as e:
            logger.warning(f"Could not create animation: {e}")
        
        logger.info("Simulation completed successfully")
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single drift simulation job
        
        Args:
            job: Job dictionary containing mission parameters
            
        Returns:
            Result dictionary with simulation outputs
        """
        mission_id = job.get('mission_id')
        mission_params = job.get('params', {})
        
        logger.info(f"Processing mission {mission_id}")
        
        # Update status to processing
        self._update_mission_status(mission_id, STATUS_PROCESSING)
        
        temp_dir = None
        result_location = None
        
        try:
            # Create temporary directory for work
            temp_dir = tempfile.mkdtemp(prefix=f'drift_{mission_id}_')
            logger.info(f"Working directory: {temp_dir}")
            
            # Download forcing data
            forcing_files = self._download_forcing_data(mission_params, temp_dir)
            
            # Run OpenDrift simulation
            output_file = os.path.join(temp_dir, 'particles.nc')
            self._run_opendrift_simulation(mission_params, forcing_files, output_file)
            
            # Upload results to S3
            result_location = self._upload_results(mission_id, output_file)
            
            # Update mission status to completed
            self._update_mission_status(
                mission_id, 
                STATUS_COMPLETED,
                result_location=result_location
            )
            
            # Enqueue results processing job
            self._enqueue_results_processing(mission_id, result_location)
            
            logger.info(f"Mission {mission_id} completed successfully")
            
            return {
                'mission_id': mission_id,
                'status': 'completed',
                'result_location': result_location
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Mission {mission_id} failed: {error_msg}", exc_info=True)
            
            # Update mission status to failed
            self._update_mission_status(
                mission_id,
                STATUS_FAILED,
                error_message=error_msg
            )
            
            return {
                'mission_id': mission_id,
                'status': 'failed',
                'error': error_msg
            }
            
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
    
    def run(self):
        """Main worker loop"""
        logger.info("Starting drift worker...")
        logger.info(f"Polling queue '{self.queue_name}' every {self.poll_interval} seconds")
        
        while True:
            try:
                # Use blocking pop with timeout
                result = self.redis_client.blpop(self.queue_name, timeout=self.poll_interval)
                
                if result:
                    queue_name, job_data = result
                    logger.info(f"Received job from queue: {queue_name}")
                    
                    try:
                        # Parse job data
                        job = json.loads(job_data)
                        
                        # Process the job
                        result = self.process_job(job)
                        
                        logger.info(f"Job completed: {result}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid job data: {e}")
                    except Exception as e:
                        logger.error(f"Error processing job: {e}", exc_info=True)
                
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5)
                try:
                    self._init_connections()
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
            
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                time.sleep(5)


def main():
    """Entry point for the drift worker"""
    logger.info("Driftline Drift Worker starting...")
    
    worker = None
    try:
        worker = DriftWorker()
        worker.run()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker initialization error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup connections
        if worker:
            if worker.db_conn:
                worker.db_conn.close()
            if worker.redis_client:
                worker.redis_client.close()


if __name__ == '__main__':
    main()
