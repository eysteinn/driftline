"""
NOAA data clients for GFS (wind) and WaveWatch III (waves)
"""
import logging
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Optional
import xarray as xr
from app.config import config
from app.models import DataRequest

logger = logging.getLogger(__name__)


class NOAAGFSClient:
    """Client for NOAA GFS wind data"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize NOAA GFS client
        
        Args:
            base_url: Base OPeNDAP URL for GFS data
        """
        self.base_url = base_url or config.NOAA_GFS_URL
    
    def fetch_wind(
        self,
        request: DataRequest,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch wind data from NOAA GFS
        
        Args:
            request: Data request parameters
            output_path: Path to save NetCDF file (optional)
            
        Returns:
            Path to downloaded NetCDF file or None if error
        """
        try:
            logger.info(f"Fetching wind data from NOAA GFS for bounds: "
                       f"lat=[{request.min_lat}, {request.max_lat}], "
                       f"lon=[{request.min_lon}, {request.max_lon}], "
                       f"time=[{request.start_time}, {request.end_time}]")
            
            # Construct OPeNDAP URL
            # GFS data is organized by forecast cycle
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # Search from request start time, or from now if request is in the future
            search_start = request.start_time if request.start_time < now else now
            
            # Try cycles going backwards from search_start
            for step in range(12):  # Try ~3 days of cycles
                dt = search_start - timedelta(hours=6 * step)
                cycle = (dt.hour // 6) * 6
                date_str = dt.strftime('%Y%m%d')
                
                try:
                    # Construct URL for specific forecast
                    # Format: gfs{YYYYMMDD}/gfs_0p25_{HH}z
                    url = f"{self.base_url}/gfs{date_str}/gfs_0p25_{cycle:02d}z"
                    
                    logger.debug(f"Trying GFS URL: {url}")
                    
                    # Open dataset via OPeNDAP
                    ds = xr.open_dataset(url, engine='pydap')
                    
                    # Select wind components (u and v at 10m)
                    # Variable names may vary, try common ones
                    wind_vars = []
                    if 'ugrd10m' in ds.variables:
                        wind_vars.append('ugrd10m')
                    if 'vgrd10m' in ds.variables:
                        wind_vars.append('vgrd10m')
                    
                    if not wind_vars:
                        logger.warning(f"Wind variables not found in dataset at {url}")
                        ds.close()
                        continue
                    
                    # Subset spatially and temporally
                    # Convert timezone-aware datetimes to naive (xarray datasets use naive datetimes)
                    start_time = request.start_time.replace(tzinfo=None) if request.start_time.tzinfo else request.start_time
                    end_time = request.end_time.replace(tzinfo=None) if request.end_time.tzinfo else request.end_time
                    
                    # Convert longitude to 0-360 range (NOAA uses 0-360, not -180 to 180)
                    lon_min = request.min_lon if request.min_lon >= 0 else request.min_lon + 360
                    lon_max = request.max_lon if request.max_lon >= 0 else request.max_lon + 360
                    
                    ds_subset = ds[wind_vars].sel(
                        lat=slice(request.min_lat, request.max_lat),
                        lon=slice(lon_min, lon_max),
                        time=slice(start_time, end_time)
                    )
                    
                    # Check if we got any data
                    if ds_subset['time'].size == 0:
                        logger.debug(f"No data in requested time range at {url}")
                        ds.close()
                        continue
                    
                    # Extract data values to avoid OPeNDAP streaming issues
                    # Create a new dataset with actual data values
                    data_vars = {}
                    for var in wind_vars:
                        data_vars[var] = (['time', 'lat', 'lon'], ds_subset[var].values)
                    
                    output_ds = xr.Dataset(
                        data_vars=data_vars,
                        coords={
                            'time': ds_subset['time'].values,
                            'lat': ds_subset['lat'].values,
                            'lon': ds_subset['lon'].values
                        }
                    )
                    ds.close()
                    
                    # Create temporary file if output_path not provided (generate unique name)
                    save_path = output_path if output_path else f"/tmp/noaa_wind_{uuid.uuid4().hex}.nc"
                    
                    # Save to NetCDF
                    output_ds.to_netcdf(save_path)
                    
                    logger.info(f"Successfully downloaded wind data from {url} to {save_path}")
                    return save_path
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch from {url}: {e}")
                    continue
            
            logger.error("Could not fetch wind data from any available GFS cycle")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching wind data from NOAA GFS: {e}")
            return None
    
    def get_available_variables(self) -> list:
        """Get list of available variables"""
        return [
            'ugrd10m',  # U-component of wind at 10m
            'vgrd10m',  # V-component of wind at 10m
        ]


class NOAAWaveWatchClient:
    """Client for NOAA WaveWatch III wave data"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize NOAA WaveWatch client
        
        Args:
            base_url: Base OPeNDAP URL for WaveWatch data
        """
        self.base_url = base_url or config.NOAA_WAVEWATCH_URL
    
    def fetch_waves(
        self,
        request: DataRequest,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch wave data from NOAA WaveWatch III
        
        Args:
            request: Data request parameters
            output_path: Path to save NetCDF file (optional)
            
        Returns:
            Path to downloaded NetCDF file or None if error
        """
        try:
            logger.info(f"Fetching wave data from NOAA WaveWatch III for bounds: "
                       f"lat=[{request.min_lat}, {request.max_lat}], "
                       f"lon=[{request.min_lon}, {request.max_lon}], "
                       f"time=[{request.start_time}, {request.end_time}]")
            
            # Construct OPeNDAP URL
            cycle_date = request.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Try current and previous day's cycles
            for days_back in range(3):
                try_date = cycle_date - timedelta(days=days_back)
                
                # WaveWatch runs at 00, 06, 12, 18 UTC
                for cycle_hour in ['00', '06', '12', '18']:
                    try:
                        # Construct URL for specific forecast
                        date_str = try_date.strftime('%Y%m%d')
                        url = f"{self.base_url}/{date_str}/gfswave.global.0p25_{cycle_hour}z"
                        
                        logger.debug(f"Trying WaveWatch URL: {url}")
                        
                        # Open dataset via OPeNDAP
                        ds = xr.open_dataset(url, engine='pydap')
                        
                        # Select wave variables
                        wave_vars = []
                        if 'htsgwsfc' in ds.variables:  # Significant height of combined wind waves and swell
                            wave_vars.append('htsgwsfc')
                        if 'perpwsfc' in ds.variables:  # Primary wave mean period
                            wave_vars.append('perpwsfc')
                        
                        if not wave_vars:
                            logger.warning(f"Wave variables not found in dataset")
                            continue
                        
                        # Subset spatially and temporally
                        # Convert timezone-aware datetimes to naive (xarray datasets use naive datetimes)
                        start_time = request.start_time.replace(tzinfo=None) if request.start_time.tzinfo else request.start_time
                        end_time = request.end_time.replace(tzinfo=None) if request.end_time.tzinfo else request.end_time
                        
                        # Convert longitude to 0-360 range (NOAA uses 0-360, not -180 to 180)
                        lon_min = request.min_lon if request.min_lon >= 0 else request.min_lon + 360
                        lon_max = request.max_lon if request.max_lon >= 0 else request.max_lon + 360
                        
                        ds_subset = ds[wave_vars].sel(
                            lat=slice(request.min_lat, request.max_lat),
                            lon=slice(lon_min, lon_max),
                            time=slice(start_time, end_time)
                        )
                        
                        # Extract data values to avoid OPeNDAP streaming issues
                        # Create a new dataset with actual data values
                        data_vars = {}
                        for var in wave_vars:
                            data_vars[var] = (['time', 'lat', 'lon'], ds_subset[var].values)
                        
                        output_ds = xr.Dataset(
                            data_vars=data_vars,
                            coords={
                                'time': ds_subset['time'].values,
                                'lat': ds_subset['lat'].values,
                                'lon': ds_subset['lon'].values
                            }
                        )
                        ds.close()
                        
                        # Create temporary file if output_path not provided (generate unique name)
                        save_path = output_path if output_path else f"/tmp/noaa_wave_{uuid.uuid4().hex}.nc"
                        
                        # Save to NetCDF
                        output_ds.to_netcdf(save_path)
                        
                        logger.info(f"Successfully downloaded wave data to {save_path}")
                        return save_path
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch from {url}: {e}")
                        continue
            
            logger.error("Could not fetch wave data from any available WaveWatch cycle")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching wave data from NOAA WaveWatch: {e}")
            return None
    
    def get_available_variables(self) -> list:
        """Get list of available variables"""
        return [
            'htsgwsfc',  # Significant height of combined wind waves and swell
            'perpwsfc',  # Primary wave mean period
        ]
