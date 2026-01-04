"""
MinIO/S3 storage service for data service
"""
import logging
from typing import Optional
from io import BytesIO
from pathlib import Path
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from app.config import config

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO/S3-based storage service"""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        use_ssl: Optional[bool] = None
    ):
        """
        Initialize storage service
        
        Args:
            endpoint: S3 endpoint URL
            access_key: S3 access key
            secret_key: S3 secret key
            bucket: S3 bucket name
            use_ssl: Whether to use SSL
        """
        self.endpoint = endpoint or config.S3_ENDPOINT
        self.access_key = access_key or config.S3_ACCESS_KEY
        self.secret_key = secret_key or config.S3_SECRET_KEY
        self.bucket = bucket or config.S3_BUCKET
        self.use_ssl = use_ssl if use_ssl is not None else config.S3_USE_SSL
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish S3 connection"""
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=BotoConfig(signature_version='s3v4'),
                use_ssl=self.use_ssl
            )
            
            # Create bucket if it doesn't exist
            try:
                self.client.head_bucket(Bucket=self.bucket)
                logger.info(f"Connected to S3 bucket: {self.bucket}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    logger.info(f"Creating S3 bucket: {self.bucket}")
                    self.client.create_bucket(Bucket=self.bucket)
                else:
                    raise
        except Exception as e:
            logger.warning(f"Failed to connect to S3: {e}")
            self.client = None
    
    def exists(self, object_key: str) -> bool:
        """
        Check if object exists in storage
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if object exists, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            logger.error(f"Error checking object existence: {e}")
            return False
    
    def upload_file(self, local_path: str, object_key: str) -> bool:
        """
        Upload file to storage
        
        Args:
            local_path: Local file path
            object_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.upload_file(local_path, self.bucket, object_key)
            logger.info(f"Uploaded file to S3: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def upload_fileobj(self, file_obj: BytesIO, object_key: str) -> bool:
        """
        Upload file object to storage
        
        Args:
            file_obj: File-like object
            object_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            file_obj.seek(0)
            self.client.upload_fileobj(file_obj, self.bucket, object_key)
            logger.info(f"Uploaded file object to S3: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file object: {e}")
            return False
    
    def download_file(self, object_key: str, local_path: str) -> bool:
        """
        Download file from storage
        
        Args:
            object_key: S3 object key
            local_path: Local file path to save to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Create parent directory if it doesn't exist
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.client.download_file(self.bucket, object_key, local_path)
            logger.info(f"Downloaded file from S3: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def download_fileobj(self, object_key: str) -> Optional[BytesIO]:
        """
        Download file object from storage
        
        Args:
            object_key: S3 object key
            
        Returns:
            BytesIO object or None if error
        """
        if not self.client:
            return None
        
        try:
            file_obj = BytesIO()
            self.client.download_fileobj(self.bucket, object_key, file_obj)
            file_obj.seek(0)
            logger.info(f"Downloaded file object from S3: {object_key}")
            return file_obj
        except ClientError as e:
            logger.error(f"Error downloading file object: {e}")
            return None
    
    def get_presigned_url(self, object_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for object
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if error
        """
        if not self.client:
            return None
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_key},
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned URL for: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if S3 is available"""
        if not self.client:
            return False
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False
