"""
Configuration for Data Aggregator Service
"""
import os
from typing import Optional


class Config:
    """Configuration class for Data Aggregator"""
    
    # Service settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://driftline_user:driftline_pass@postgres:5432/driftline"
    )
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/1")
    
    # MinIO/S3 settings
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "environmental-data")
    S3_USE_SSL: bool = os.getenv("S3_USE_SSL", "false").lower() == "true"
    
    # Copernicus Marine credentials
    COPERNICUS_USERNAME: Optional[str] = os.getenv("COPERNICUS_USERNAME")
    COPERNICUS_PASSWORD: Optional[str] = os.getenv("COPERNICUS_PASSWORD")
    COPERNICUS_DATASET_ID: str = os.getenv(
        "COPERNICUS_DATASET_ID",
        "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
    )
    
    # Data collection settings
    HISTORICAL_DAYS: int = int(os.getenv("HISTORICAL_DAYS", "7"))
    FORECAST_HOURS: int = int(os.getenv("FORECAST_HOURS", "120"))
    FORECAST_INTERVAL_HOURS: int = int(os.getenv("FORECAST_INTERVAL_HOURS", "3"))
    
    # Collection schedule (cron format)
    COLLECTION_SCHEDULE: str = os.getenv("COLLECTION_SCHEDULE", "0 */6 * * *")  # Every 6 hours
    CLEANUP_SCHEDULE: str = os.getenv("CLEANUP_SCHEDULE", "0 2 * * *")  # Daily at 2 AM
    
    # Data retention
    MAX_DATA_AGE_DAYS: int = int(os.getenv("MAX_DATA_AGE_DAYS", "14"))
    
    # NOAA GFS settings
    NOAA_GFS_BASE_URL: str = os.getenv(
        "NOAA_GFS_BASE_URL",
        "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
    )


config = Config()
