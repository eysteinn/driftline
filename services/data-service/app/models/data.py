"""
Data models for environmental data requests and responses
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class DataType(str, Enum):
    """Types of environmental data"""
    OCEAN_CURRENTS = "ocean_currents"
    WIND = "wind"
    WAVES = "waves"


@dataclass
class DataRequest:
    """Request for environmental data"""
    data_type: DataType
    
    # Spatial bounds (WGS84 coordinates)
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    
    # Temporal bounds
    start_time: datetime
    end_time: datetime
    
    # Optional parameters
    resolution: Optional[str] = None
    variables: Optional[List[str]] = None
    
    def validate(self) -> None:
        """Validate the request parameters"""
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat must be less than max_lat")
        if self.min_lon >= self.max_lon:
            raise ValueError("min_lon must be less than max_lon")
        if self.min_lat < -90 or self.max_lat > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if self.min_lon < -180 or self.max_lon > 180:
            raise ValueError("Longitude must be between -180 and 180")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")


@dataclass
class Bounds:
    """Spatial boundaries"""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


@dataclass
class TimeRange:
    """Temporal boundaries"""
    start: datetime
    end: datetime


@dataclass
class Metadata:
    """Metadata about the data"""
    variables: List[str]
    resolution: str
    bounds: Bounds
    time_range: TimeRange
    time_steps: int = 0
    units: Optional[Dict[str, str]] = None
    description: Optional[str] = None


@dataclass
class DataResponse:
    """Response containing environmental data"""
    data_type: DataType
    source: str
    cache_hit: bool
    metadata: Metadata
    expires_at: datetime
    file_urls: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        def convert_value(v):
            if isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, Enum):
                return v.value
            elif hasattr(v, '__dataclass_fields__'):
                return {k: convert_value(val) for k, val in asdict(v).items()}
            return v
        
        return {k: convert_value(v) for k, v in asdict(self).items()}


# Error classes
class DataServiceError(Exception):
    """Base exception for data service errors"""
    pass


class InvalidBoundsError(DataServiceError):
    """Invalid spatial bounds"""
    pass


class InvalidTimeRangeError(DataServiceError):
    """Invalid time range"""
    pass


class DataNotFoundError(DataServiceError):
    """Data not found"""
    pass


class ExternalSourceError(DataServiceError):
    """Error fetching from external source"""
    pass
