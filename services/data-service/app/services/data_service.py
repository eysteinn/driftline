"""
Main data service for fetching, caching, and serving environmental data
"""
import logging
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import xarray as xr
from app.config import config
from app.models import (
    DataRequest, DataResponse, DataType, Metadata,
    Bounds, TimeRange, ExternalSourceError
)
from app.services.cache import CacheService
from app.services.storage import StorageService
from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


class DataService:
    """Service for managing environmental data retrieval and caching"""
    
    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        storage_service: Optional[StorageService] = None,
        database_service: Optional[DatabaseService] = None
    ):
        """
        Initialize data service
        
        Args:
            cache_service: Cache service instance
            storage_service: Storage service instance
            database_service: Database service instance
        """
        self.cache = cache_service or CacheService()
        self.storage = storage_service or StorageService()
        self.database = database_service or DatabaseService()
    
    def get_data(self, request: DataRequest) -> DataResponse:
        """
        Get environmental data based on request
        
        Args:
            request: Data request parameters
            
        Returns:
            Data response with file path and metadata
            
        Raises:
            ValueError: If request is invalid
            ExternalSourceError: If data cannot be fetched
        """
        # Validate request
        request.validate()
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache first
        cached_paths = self.cache.get(cache_key)
        if cached_paths:
            # Ensure cached value is a list
            if isinstance(cached_paths, str):
                cached_paths = [cached_paths]
            # Check if all cached paths exist
            if all(self.storage.exists(path) for path in cached_paths):
                logger.info(f"Cache hit for key: {cache_key}")
                return self._build_response(request, cached_paths, cache_hit=True)
        
        logger.info(f"Cache miss for key: {cache_key}")
        
        # Fetch data from aggregator's collected datasets
        logger.info(f"Fetching data from aggregator for {request.data_type}")
        file_paths = self._fetch_from_aggregator(request)
        
        if not file_paths:
            raise ExternalSourceError(
                f"No data available for {request.data_type} in requested time range. "
                f"Data must be collected by data-aggregator service first."
            )
        
        # Return all file paths without merging
        return self._build_response(request, file_paths, cache_hit=False)
    
    def _fetch_from_aggregator(self, request: DataRequest) -> Optional[List[str]]:
        """
        Fetch data from aggregator's collected datasets
        
        Args:
            request: Data request parameters
            
        Returns:
            List of file paths for available datasets or None if data not available
        """
        try:
            # Map DataType enum to database data_type strings
            data_type_map = {
                DataType.OCEAN_CURRENTS: 'ocean_currents',
                DataType.WIND: 'wind',
                DataType.WAVES: 'waves'
            }
            
            data_type_str = data_type_map.get(request.data_type)
            if not data_type_str:
                logger.error(f"Unknown data type: {request.data_type}")
                return None
            
            # Query database for available datasets
            datasets = self.database.find_datasets(
                data_type=data_type_str,
                start_time=request.start_time,
                end_time=request.end_time
            )
            
            if not datasets:
                logger.info(f"No datasets found in aggregator for {data_type_str}")
                return None
            
            logger.info(f"Found {len(datasets)} datasets in aggregator")
            
            # Check coverage
            #coverage = self.database.check_coverage(
            #    data_type=data_type_str,
            #    start_time=request.start_time,
            #    end_time=request.end_time
            #)
            #print("AAAAAAAAAA")
            #if not coverage['has_coverage']:
            #    logger.warning("Insufficient data coverage in aggregator")
            #    return None
            #print("BBBBBBBBBB")
            #if coverage['gap_count'] > 0:
            #    logger.warning(f"Data has {coverage['gap_count']} gaps")
            #print("CCCCCCCCCC")
            # Return list of file paths instead of merging
            return [dataset['file_path'] for dataset in datasets]
            
        except Exception as e:
            logger.error(f"Error fetching from aggregator: {e}")
            return None
    
    def _generate_cache_key(self, request: DataRequest) -> str:
        """
        Generate cache key from request parameters
        
        Args:
            request: Data request parameters
            
        Returns:
            Cache key string
        """
        # Create key from all request parameters
        key_parts = [
            str(request.data_type.value),
            f"{request.min_lat:.2f}",
            f"{request.max_lat:.2f}",
            f"{request.min_lon:.2f}",
            f"{request.max_lon:.2f}",
            request.start_time.strftime('%Y%m%d'),
            request.end_time.strftime('%Y%m%d'),
        ]
        
        if request.resolution:
            key_parts.append(request.resolution)
        
        key_string = ':'.join(key_parts)
        
        # Hash to keep key size reasonable
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"data:{request.data_type.value}:{key_hash}"
    
    def _generate_storage_key(self, request: DataRequest) -> str:
        """
        Generate storage key from request parameters
        
        Args:
            request: Data request parameters
            
        Returns:
            Storage key string
        """
        # Organize by data type and date
        date_str = request.start_time.strftime('%Y/%m/%d')
        
        # Create unique filename based on bounds
        bounds_hash = hashlib.sha256(
            f"{request.min_lat}{request.max_lat}{request.min_lon}{request.max_lon}".encode()
        ).hexdigest()[:8]
        
        filename = f"data_{bounds_hash}.nc"
        
        return f"{request.data_type.value}/{date_str}/{filename}"
    
    def _build_response(
        self,
        request: DataRequest,
        file_paths: List[str],
        cache_hit: bool
    ) -> DataResponse:
        """
        Build data response with metadata
        
        Args:
            request: Data request parameters
            file_paths: List of paths to data files (storage keys or local paths)
            cache_hit: Whether this was a cache hit
            
        Returns:
            Data response object
        """
        # Try to extract metadata from first NetCDF file (if available)
        metadata = None
        for file_path in file_paths:
            if self.storage.exists(file_path):
                metadata = self._extract_metadata(request, file_path)
                break
        
        if not metadata:
            # Use default metadata if we couldn't extract from files
            metadata = Metadata(
                variables=self._get_default_variables(request.data_type),
                time_steps=0,
                resolution=request.resolution or self._get_default_resolution(request.data_type),
                bounds=Bounds(
                    min_lat=request.min_lat,
                    max_lat=request.max_lat,
                    min_lon=request.min_lon,
                    max_lon=request.max_lon
                ),
                time_range=TimeRange(
                    start=request.start_time,
                    end=request.end_time
                )
            )
        
        # Generate presigned URLs for files in storage
        file_urls = []
        for file_path in file_paths:
            if self.storage.exists(file_path):
                url = self.storage.get_presigned_url(file_path, expiration=3600)
                if url:
                    file_urls.append(url)
        
        return DataResponse(
            data_type=request.data_type,
            source=self._get_data_source(request.data_type),
            cache_hit=cache_hit,
            file_paths=file_paths,
            file_urls=file_urls if file_urls else None,
            metadata=metadata,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
    
    def _extract_metadata(self, request: DataRequest, file_path: str) -> Metadata:
        """
        Extract metadata from NetCDF file or use defaults
        
        Args:
            request: Data request parameters
            file_path: Path to NetCDF file
            
        Returns:
            Metadata object
        """
        try:
            # Try to open and inspect the NetCDF file
            if Path(file_path).exists():
                with xr.open_dataset(file_path) as ds:
                    variables = list(ds.data_vars.keys())
                    time_steps = len(ds.time) if 'time' in ds.dims else 0
                    
                    # Extract units if available
                    units = {}
                    for var in variables:
                        if 'units' in ds[var].attrs:
                            units[var] = ds[var].attrs['units']
                    
                    return Metadata(
                        variables=variables,
                        time_steps=time_steps,
                        resolution=request.resolution or self._get_default_resolution(request.data_type),
                        bounds=Bounds(
                            min_lat=request.min_lat,
                            max_lat=request.max_lat,
                            min_lon=request.min_lon,
                            max_lon=request.max_lon
                        ),
                        time_range=TimeRange(
                            start=request.start_time,
                            end=request.end_time
                        ),
                        units=units if units else None
                    )
        except Exception as e:
            logger.warning(f"Could not extract metadata from file: {e}")
        
        # Return default metadata
        return Metadata(
            variables=self._get_default_variables(request.data_type),
            time_steps=0,
            resolution=request.resolution or self._get_default_resolution(request.data_type),
            bounds=Bounds(
                min_lat=request.min_lat,
                max_lat=request.max_lat,
                min_lon=request.min_lon,
                max_lon=request.max_lon
            ),
            time_range=TimeRange(
                start=request.start_time,
                end=request.end_time
            )
        )
    
    @staticmethod
    def _get_default_variables(data_type: DataType) -> list:
        """Get default variables for data type"""
        if data_type == DataType.OCEAN_CURRENTS:
            return ['eastward_sea_water_velocity', 'northward_sea_water_velocity']
        elif data_type == DataType.WIND:
            return ['eastward_wind', 'northward_wind']
        elif data_type == DataType.WAVES:
            return ['sea_surface_wave_significant_height', 'sea_surface_wave_period']
        return []
    
    @staticmethod
    def _get_default_resolution(data_type: DataType) -> str:
        """Get default resolution for data type"""
        if data_type == DataType.OCEAN_CURRENTS:
            return "1/12 degree (~9km)"
        elif data_type == DataType.WIND:
            return "0.25 degree (~28km)"
        elif data_type == DataType.WAVES:
            return "0.5 degree (~56km)"
        return "unknown"
    
    @staticmethod
    def _get_data_source(data_type: DataType) -> str:
        """Get data source name for data type"""
        if data_type == DataType.OCEAN_CURRENTS:
            return "Copernicus Marine Service (CMEMS)"
        elif data_type == DataType.WIND:
            return "NOAA GFS"
        elif data_type == DataType.WAVES:
            return "NOAA WaveWatch III"
        return "unknown"
