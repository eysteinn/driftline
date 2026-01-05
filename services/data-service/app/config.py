"""
Configuration for Driftline Data Service
"""
import os
from typing import Optional


class Config:
    """Application configuration"""
    
    # Server
    PORT: int = int(os.getenv('PORT', '8000'))
    # Note: 0.0.0.0 is used by default for Docker container compatibility
    # In production, this should be behind a reverse proxy (nginx)
    # For local development without Docker, set HOST=127.0.0.1
    HOST: str = os.getenv('HOST', '0.0.0.0')
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Redis
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '86400'))  # 24 hours
    
    # MinIO/S3
    S3_ENDPOINT: str = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    S3_ACCESS_KEY: str = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    S3_SECRET_KEY: str = os.getenv('S3_SECRET_KEY', 'minioadmin')
    S3_BUCKET: str = os.getenv('S3_BUCKET', 'environmental-data')
    S3_USE_SSL: bool = os.getenv('S3_USE_SSL', 'false').lower() == 'true'
    
    # Copernicus Marine Service
    COPERNICUS_USERNAME: Optional[str] = os.getenv('COPERNICUS_USERNAME')
    COPERNICUS_PASSWORD: Optional[str] = os.getenv('COPERNICUS_PASSWORD')
    
    # Data sources
    # Copernicus Marine Service - Global Ocean Physics Analysis and Forecast
    CMEMS_OCEAN_CURRENTS_DATASET: str = os.getenv(
        'CMEMS_OCEAN_CURRENTS_DATASET',
        'cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m'
    )
    
    # NOAA GFS - Global Forecast System
    NOAA_GFS_URL: str = os.getenv(
        'NOAA_GFS_URL',
        'https://nomads.ncep.noaa.gov/dods/gfs_0p25'
    )
    
    # NOAA WaveWatch III
    NOAA_WAVEWATCH_URL: str = os.getenv(
        'NOAA_WAVEWATCH_URL',
        'https://nomads.ncep.noaa.gov/dods/wave/gfswave'
    )
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()


# Create singleton instance
config = Config()
