"""
Storage service for managing S3/MinIO bucket
"""
import logging
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional
from app.config import config

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing S3/MinIO storage"""
    
    def __init__(self):
        """Initialize storage service"""
        self.client = None
        self.bucket = config.S3_BUCKET
        self._connect()
        self._ensure_bucket()
    
    def _connect(self):
        """Connect to S3/MinIO"""
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=config.S3_ENDPOINT,
                aws_access_key_id=config.S3_ACCESS_KEY,
                aws_secret_access_key=config.S3_SECRET_KEY,
                config=BotoConfig(signature_version='s3v4'),
                use_ssl=config.S3_USE_SSL
            )
            logger.info(f"Connected to S3 at {config.S3_ENDPOINT}")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise
    
    def _ensure_bucket(self):
        """Ensure the bucket exists"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket '{self.bucket}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Created bucket '{self.bucket}'")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            s3_key: S3 object key
        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking if file exists {s3_key}: {e}")
                raise
        
    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Upload a file to S3
        
        Args:
            local_path: Path to local file
            s3_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.upload_file(local_path, self.bucket, s3_key)
            logger.info(f"Uploaded {local_path} to s3://{self.bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted s3://{self.bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        Get the size of a file in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File size in bytes, or None if error
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return response['ContentLength']
        except Exception as e:
            logger.error(f"Failed to get file size: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if storage service is available"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False
