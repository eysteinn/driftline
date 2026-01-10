"""
Data models for Data Aggregator
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DatasetRecord:
    """Record of an available dataset"""
    id: Optional[str] = None
    data_type: str = ""  # 'ocean_currents', 'wind', 'waves'
    source: str = ""  # 'copernicus', 'noaa_gfs', etc.
    forecast_date: datetime = None  # Date of the forecast run
    forecast_cycle: str = ""  # '00', '06', '12', '18'
    valid_time_start: datetime = None  # Start of valid time range
    valid_time_end: datetime = None  # End of valid time range
    file_path: str = ""  # S3 path to the data file
    file_size_bytes: int = 0
    is_forecast: bool = False  # True for forecast, False for historical/analysis
    created_at: datetime = None
    last_accessed_at: Optional[datetime] = None


@dataclass
class CollectionStatus:
    """Status of a data collection run"""
    collection_id: str
    data_type: str
    status: str  # 'running', 'completed', 'failed'
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_collected: int = 0
    error_message: Optional[str] = None
