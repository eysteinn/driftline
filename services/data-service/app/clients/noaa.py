"""
NOAA data clients for GFS (wind) and WaveWatch III (waves)
"""
import logging
import tempfile
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
            # Create temporary file if output_path not provided
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix='.nc',
                    delete=False
                )
                output_path = temp_file.name
                temp_file.close()
            
            logger.info(f"Fetching wind data from NOAA GFS for bounds: "
                       f"lat=[{request.min_lat}, {request.max_lat}], "
                       f"lon=[{request.min_lon}, {request.max_lon}], "
                       f"time=[{request.start_time}, {request.end_time}]")
            
            # Construct OPeNDAP URL
            # GFS data is organized by forecast cycle
            # Use the most recent cycle relative to start_time
            cycle_date = request.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Try current and previous day's cycles
            for days_back in range(3):
                try_date = cycle_date - timedelta(days=days_back)
                
                # GFS runs at 00, 06, 12, 18 UTC
                for cycle_hour in ['00', '06', '12', '18']:
                    try:
                        # Construct URL for specific forecast
                        # Format: gfs_0p25_YYYYMMDD/gfs_0p25_HHz
                        date_str = try_date.strftime('%Y%m%d')
                        url = f"{self.base_url}/{date_str}/gfs_0p25_{cycle_hour}z"
                        
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
                            logger.warning(f"Wind variables not found in dataset")
                            continue
                        
                        # Subset spatially and temporally
                        ds_subset = ds[wind_vars].sel(
                            lat=slice(request.min_lat, request.max_lat),
                            lon=slice(request.min_lon, request.max_lon),
                            time=slice(request.start_time, request.end_time)
                        )
                        
                        # Save to NetCDF
                        ds_subset.to_netcdf(output_path)
                        ds.close()
                        
                        logger.info(f"Successfully downloaded wind data to {output_path}")
                        return output_path
                        
                    except Exception as e:
                        logger.debug(f"Failed to fetch from {url}: {e}")
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
            # Create temporary file if output_path not provided
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix='.nc',
                    delete=False
                )
                output_path = temp_file.name
                temp_file.close()
            
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
                        ds_subset = ds[wave_vars].sel(
                            lat=slice(request.min_lat, request.max_lat),
                            lon=slice(request.min_lon, request.max_lon),
                            time=slice(request.start_time, request.end_time)
                        )
                        
                        # Save to NetCDF
                        ds_subset.to_netcdf(output_path)
                        ds.close()
                        
                        logger.info(f"Successfully downloaded wave data to {output_path}")
                        return output_path
                        
                    except Exception as e:
                        logger.debug(f"Failed to fetch from {url}: {e}")
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
