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
    def get_filename(self, date:datetime) -> str:
        """Generate filename for a given date"""
        date_str = date.strftime("%Y%m%dT%H")
        return f"cmems_currents_{date_str}.nc"
    
    def download_ocean_currents(
        self,
        date: datetime,
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
            date_str = date.strftime("%Y%m%dT%H")
            filename = "cmems_currents_"+date_str+".nc"

            s3_key = self.get_s3_key(date=date, filename=filename)
            if self.storage.file_exists(s3_key):
                logger.info(f"Data for {date.date()} already exists in storage: {s3_key}")
                return None  # Already exists
            
            
            # Create output file
            out_file = self.temp_dir / filename
            
            if out_file.exists():
                logger.info(f"File already exists: {out_file}")
                return out_file
            
            logger.info(
                f"Downloading ocean currents data for {date.date()} to {out_file}"
            )
            
            cm.subset(
                username = self.username,
                password = self.password,
                dataset_id="cmems_mod_glo_phy_anfc_merged-uv_PT1H-i",

                variables=[
                    "utotal",
                    "vtotal"
                ],

                start_datetime=date,
                end_datetime=date,
                output_filename=filename,
                output_directory=self.temp_dir,
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
            # Calculate start time (days_back ago at midnight)
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(days=days_back)
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate total hours to collect
            total_hours =  24
            
            logger.info(f"Collecting hourly data from {start_time} for {total_hours} hours")
            
            # Iterate through each hour
            for hour_offset in range(total_hours):
                current_time = start_time + timedelta(hours=hour_offset)
                
                logger.info(f"Downloading ocean currents for {current_time}")
                
                file_path = self.download_ocean_currents(date=current_time)
                
                if file_path:
                    # Record the dataset for this hour
                    cycle = f"{current_time.hour:02d}"
                    success = self._record_dataset(
                        analysis_date=current_time,
                        cycle=cycle,
                        forecast_date=current_time,
                        local_file_path=str(file_path),
                        is_forecast=False
                    )
                    
                    if success:
                        collected += 1
                        logger.info(f"Successfully collected hour {hour_offset+1}/{total_hours}")
                else:
                    logger.warning(f"Failed to download data for {current_time}")
            
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Historical collection completed: {collected}/{total_hours} datasets")
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
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate total forecast hours
            logger.info(f"Collecting hourly forecast data for {forecast_hours} hours from {start_time}")
            
            # Iterate through each forecast hour
            for hour_offset in range(forecast_hours):
                forecast_time = start_time + timedelta(hours=hour_offset)
                
                logger.info(f"Downloading forecast ocean currents for {forecast_time}")
                
                file_path = self.download_ocean_currents(date=forecast_time)
                
                if file_path:
                    # Record the forecast dataset
                    cycle = f"{forecast_time.hour:02d}"
                    success = self._record_dataset(
                        analysis_date=now,
                        cycle=cycle,
                        forecast_date=forecast_time,
                        local_file_path=str(file_path),
                        is_forecast=True
                    )
                    
                    if success:
                        collected += 1
                        logger.info(f"Successfully collected forecast hour {hour_offset+1}/{forecast_hours}")
                else:
                    logger.warning(f"Failed to download forecast data for {forecast_time}")
            
            self.db.complete_collection(collection_id, collected)
            logger.info(f"Forecast collection completed: {collected}/{forecast_hours} datasets")
            return collected
            
        except Exception as e:
            error_msg = f"Error during forecast collection: {e}"
            logger.error(error_msg)
            self.db.complete_collection(collection_id, collected, error_msg)
            return collected
