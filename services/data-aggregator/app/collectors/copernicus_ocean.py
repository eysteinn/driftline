"""
Copernicus Marine ocean currents data collector
Based on the example code provided in the issue comments
"""
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from app.collectors.base import BaseCollector
from app.config import config

logger = logging.getLogger(__name__)


class CopernicusOceanCollector(BaseCollector):
    """Collector for Copernicus Marine ocean currents data"""
    
    def __init__(self, db_service, storage_service):
        super().__init__(db_service, storage_service)
        self.data_type = "ocean_currents"
        self.source = "copernicus"
        self.dataset_id = config.COPERNICUS_DATASET_ID
        self.username = config.COPERNICUS_USERNAME
        self.password = config.COPERNICUS_PASSWORD
        self.temp_dir = Path("/tmp/copernicus_ocean_data")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.username or not self.password:
            logger.warning(
                "Copernicus credentials not configured. "
                "Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD environment variables."
            )
    
    def is_available(self) -> bool:
        """Check if collector is properly configured"""
        return bool(self.username and self.password)
    
    def download_ocean_currents(
        self,
        start_date: datetime,
        end_date: datetime,
        min_depth: float = 0.5,
        max_depth: float = 0.5
    ) -> Optional[Path]:
        """
        Download ocean currents data from Copernicus
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            min_depth: Minimum depth in meters
            max_depth: Maximum depth in meters
            
        Returns:
            Path to downloaded NetCDF file, or None if error
        """
        if not self.is_available():
            logger.error("Copernicus collector not available - missing credentials")
            return None
        
        try:
            import copernicusmarine as cm
            
            # Create output file
            date_str = start_date.strftime("%Y%m%d")
            out_file = self.temp_dir / f"cmems_currents_{date_str}.nc"
            
            if out_file.exists():
                logger.info(f"File already exists: {out_file}")
                return out_file
            
            logger.info(
                f"Downloading ocean currents from {start_date} to {end_date} "
                f"at depth {min_depth}-{max_depth}m"
            )
            
            # Use copernicusmarine subset to download global data
            # Note: We download global data as subsetting will be done at query time
            cm.subset(
                username=self.username,
                password=self.password,
                dataset_id=self.dataset_id,
                variables=[
                    "uo",  # zonal (eastward) current
                    "vo"   # meridional (northward) current
                ],
                # Time range (ISO 8601)
                start_datetime=start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                end_datetime=end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                # Depth (surface only)
                minimum_depth=min_depth,
                maximum_depth=max_depth,
                # Output
                output_filename=str(out_file),
                output_directory=str(self.temp_dir),
                force_download=True
            )
            
            logger.info(f"Successfully downloaded ocean currents to {out_file}")
            return out_file
            
        except ImportError:
            logger.error(
                "copernicusmarine package not installed. "
                "Install with: pip install copernicusmarine"
            )
            return None
        except Exception as e:
            logger.error(f"Error downloading ocean currents: {e}")
            return None
    
    def collect_historical(self, days_back: int, **kwargs) -> int:
        """
        Collect historical ocean currents data
        
        Args:
            days_back: Number of days to go back
            
        Returns:
            Number of datasets collected
        """
        logger.info(f"Starting historical ocean currents collection for {days_back} days back")
        collection_id = self.db.start_collection(self.data_type)
        collected = 0
        
        if not self.is_available():
            error_msg = "Copernicus credentials not configured"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
        
        try:
            # Collect data for the specified day
            target_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            logger.info(f"Downloading historical ocean currents for {start_date.date()}")
            
            file_path = self.download_ocean_currents(
                start_date=start_date,
                end_date=end_date
            )
            
            if file_path:
                # Copernicus data typically has 6-hour intervals
                # Record the dataset with the full day coverage
                success = self._record_dataset(
                    forecast_date=start_date,
                    forecast_cycle="00",
                    valid_time_start=start_date,
                    valid_time_end=end_date,
                    local_file_path=str(file_path),
                    is_forecast=False
                )
                
                if success:
                    collected += 1
            
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Historical collection completed: {collected} datasets")
            return collected
            
        except Exception as e:
            error_msg = f"Error during historical collection: {e}"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
    
    def collect_forecast(self, forecast_hours: int, **kwargs) -> int:
        """
        Collect forecast ocean currents data
        
        Args:
            forecast_hours: Number of forecast hours to collect
            
        Returns:
            Number of datasets collected
        """
        logger.info(f"Starting forecast ocean currents collection for {forecast_hours} hours")
        collection_id = self.db.start_collection(self.data_type)
        collected = 0
        
        if not self.is_available():
            error_msg = "Copernicus credentials not configured"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
        
        try:
            # Get current time
            now = datetime.now(timezone.utc)
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate end date based on forecast hours
            forecast_days = (forecast_hours // 24) + 1
            end_date = start_date + timedelta(days=forecast_days)
            
            logger.info(f"Downloading forecast ocean currents from {start_date} to {end_date}")
            
            file_path = self.download_ocean_currents(
                start_date=start_date,
                end_date=end_date
            )
            
            if file_path:
                # Record the forecast dataset
                success = self._record_dataset(
                    forecast_date=now,
                    forecast_cycle="00",
                    valid_time_start=start_date,
                    valid_time_end=end_date,
                    local_file_path=str(file_path),
                    is_forecast=True
                )
                
                if success:
                    collected += 1
            
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Forecast collection completed: {collected} datasets")
            return collected
            
        except Exception as e:
            error_msg = f"Error during forecast collection: {e}"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
