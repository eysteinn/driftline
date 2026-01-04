"""
Main data service for fetching, caching, and serving environmental data
"""
import logging
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import xarray as xr
from app.config import config
from app.models import (
    DataRequest, DataResponse, DataType, Metadata,
    Bounds, TimeRange, ExternalSourceError
)
from app.services.cache import CacheService
from app.services.storage import StorageService
from app.clients import CopernicusClient, NOAAGFSClient, NOAAWaveWatchClient

logger = logging.getLogger(__name__)


class DataService:
    """Service for managing environmental data retrieval and caching"""
    
    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        storage_service: Optional[StorageService] = None,
        copernicus_client: Optional[CopernicusClient] = None,
        gfs_client: Optional[NOAAGFSClient] = None,
        wavewatch_client: Optional[NOAAWaveWatchClient] = None
    ):
        """
        Initialize data service
        
        Args:
            cache_service: Cache service instance
            storage_service: Storage service instance
            copernicus_client: Copernicus client instance
            gfs_client: NOAA GFS client instance
            wavewatch_client: NOAA WaveWatch client instance
        """
        self.cache = cache_service or CacheService()
        self.storage = storage_service or StorageService()
        self.copernicus = copernicus_client or CopernicusClient()
        self.gfs = gfs_client or NOAAGFSClient()
        self.wavewatch = wavewatch_client or NOAAWaveWatchClient()
    
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
        cached_path = self.cache.get(cache_key)
        if cached_path and self.storage.exists(cached_path):
            logger.info(f"Cache hit for key: {cache_key}")
            return self._build_response(request, cached_path, cache_hit=True)
        
        logger.info(f"Cache miss for key: {cache_key}")
        
        # Generate storage key
        storage_key = self._generate_storage_key(request)
        
        # Check if data exists in storage
        if self.storage.exists(storage_key):
            logger.info(f"Data exists in storage: {storage_key}")
            # Update cache
            self.cache.set(cache_key, storage_key, config.CACHE_TTL)
            return self._build_response(request, storage_key, cache_hit=False)
        
        # Fetch from external source
        logger.info(f"Fetching data from external source for {request.data_type}")
        local_path = self._fetch_from_source(request)
        
        if not local_path:
            raise ExternalSourceError(
                f"Failed to fetch {request.data_type} data from external source"
            )
        
        try:
            # Upload to storage
            if self.storage.upload_file(local_path, storage_key):
                logger.info(f"Uploaded data to storage: {storage_key}")
                
                # Update cache
                self.cache.set(cache_key, storage_key, config.CACHE_TTL)
                
                return self._build_response(request, storage_key, cache_hit=False)
            else:
                logger.warning("Failed to upload to storage, using local file")
                return self._build_response(request, local_path, cache_hit=False)
                
        finally:
            # Clean up temporary file if it was created
            try:
                if local_path.startswith(tempfile.gettempdir()):
                    Path(local_path).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {e}")
    
    def _fetch_from_source(self, request: DataRequest) -> Optional[str]:
        """
        Fetch data from appropriate external source
        
        Args:
            request: Data request parameters
            
        Returns:
            Path to downloaded file or None if error
        """
        if request.data_type == DataType.OCEAN_CURRENTS:
            return self.copernicus.fetch_ocean_currents(request)
        elif request.data_type == DataType.WIND:
            return self.gfs.fetch_wind(request)
        elif request.data_type == DataType.WAVES:
            return self.wavewatch.fetch_waves(request)
        else:
            logger.error(f"Unknown data type: {request.data_type}")
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
        file_path: str,
        cache_hit: bool
    ) -> DataResponse:
        """
        Build data response with metadata
        
        Args:
            request: Data request parameters
            file_path: Path to data file (storage key or local path)
            cache_hit: Whether this was a cache hit
            
        Returns:
            Data response object
        """
        # Try to extract metadata from NetCDF file
        metadata = self._extract_metadata(request, file_path)
        
        # Generate presigned URL if file is in storage
        file_url = None
        if self.storage.exists(file_path):
            file_url = self.storage.get_presigned_url(file_path, expiration=3600)
        
        return DataResponse(
            data_type=request.data_type,
            source=self._get_data_source(request.data_type),
            cache_hit=cache_hit,
            file_path=file_path,
            file_url=file_url,
            metadata=metadata,
            expires_at=datetime.utcnow() + timedelta(hours=24)
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
