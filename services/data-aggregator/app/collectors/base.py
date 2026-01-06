"""
Base collector interface
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from app.services import DatabaseService, StorageService

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for data collectors"""
    
    def __init__(
        self,
        db_service: DatabaseService,
        storage_service: StorageService
    ):
        """
        Initialize collector
        
        Args:
            db_service: Database service instance
            storage_service: Storage service instance
        """
        self.db = db_service
        self.storage = storage_service
        self.data_type = None  # To be set by subclasses
        self.source = None  # To be set by subclasses
    
    @abstractmethod
    def collect_historical(
        self,
        days_back: int,
        **kwargs
    ) -> int:
        """
        Collect historical data
        
        Args:
            days_back: Number of days to go back
            **kwargs: Additional collector-specific parameters
            
        Returns:
            Number of datasets collected
        """
        pass
    
    @abstractmethod
    def collect_forecast(
        self,
        forecast_hours: int,
        **kwargs
    ) -> int:
        """
        Collect forecast data
        
        Args:
            forecast_hours: Number of forecast hours
            **kwargs: Additional collector-specific parameters
            
        Returns:
            Number of datasets collected
        """
        pass
    
    def _record_dataset(
        self,
        forecast_date: datetime,
        forecast_cycle: str,
        valid_time_start: datetime,
        valid_time_end: datetime,
        local_file_path: str,
        is_forecast: bool = False
    ) -> bool:
        """
        Record a dataset in database and upload to storage
        
        Args:
            forecast_date: Date of the forecast run
            forecast_cycle: Forecast cycle (e.g., '00', '06', '12', '18')
            valid_time_start: Start of valid time range
            valid_time_end: End of valid time range
            local_file_path: Path to local file
            is_forecast: Whether this is forecast data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate S3 key
            date_path = forecast_date.strftime("%Y/%m/%d")
            filename = local_file_path.split('/')[-1]
            s3_key = f"{self.data_type}/{date_path}/{forecast_cycle}/{filename}"
            
            # Check if file already exists in storage
            if self.storage.file_exists(s3_key):
                logger.info(f"File already exists in storage: {s3_key}")
                # Get file size from S3
                file_size = self.storage.get_file_size(s3_key)
            else:
                # Upload to storage
                if not self.storage.upload_file(local_file_path, s3_key):
                    logger.error(f"Failed to upload file to storage: {s3_key}")
                    return False
                
                # Get file size
                file_size = self.storage.get_file_size(s3_key)
            
            # Record in database
            dataset_id = self.db.record_dataset(
                data_type=self.data_type,
                source=self.source,
                forecast_date=forecast_date,
                forecast_cycle=forecast_cycle,
                valid_time_start=valid_time_start,
                valid_time_end=valid_time_end,
                file_path=s3_key,
                file_size_bytes=file_size or 0,
                is_forecast=is_forecast
            )
            
            if dataset_id:
                logger.info(f"Recorded dataset {dataset_id} for {self.data_type}")
                return True
            else:
                logger.error("Failed to record dataset in database")
                return False
                
        except Exception as e:
            logger.error(f"Error recording dataset: {e}")
            return False
