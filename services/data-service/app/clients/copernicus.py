"""
Copernicus Marine Service client for ocean currents data
"""
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import xarray as xr
from app.config import config
from app.models import DataRequest

logger = logging.getLogger(__name__)


class CopernicusClient:
    """Client for Copernicus Marine Service"""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        dataset_id: Optional[str] = None
    ):
        """
        Initialize Copernicus client
        
        Args:
            username: Copernicus username
            password: Copernicus password
            dataset_id: Dataset ID to use
        """
        self.username = username or config.COPERNICUS_USERNAME
        self.password = password or config.COPERNICUS_PASSWORD
        self.dataset_id = dataset_id or config.CMEMS_OCEAN_CURRENTS_DATASET
        
        # Check if credentials are available
        if not self.username or not self.password:
            logger.warning(
                "Copernicus credentials not configured. "
                "Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD environment variables."
            )
    
    def fetch_ocean_currents(
        self,
        request: DataRequest,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch ocean currents data from Copernicus
        
        Args:
            request: Data request parameters
            output_path: Path to save NetCDF file (optional)
            
        Returns:
            Path to downloaded NetCDF file or None if error
        """
        if not self.username or not self.password:
            logger.error("Copernicus credentials not configured")
            return None
        
        try:
            import copernicusmarine as cm
            
            # Create temporary file if output_path not provided
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix='.nc',
                    delete=False
                )
                output_path = temp_file.name
                temp_file.close()
            
            logger.info(f"Fetching ocean currents from Copernicus for bounds: "
                       f"lat=[{request.min_lat}, {request.max_lat}], "
                       f"lon=[{request.min_lon}, {request.max_lon}], "
                       f"time=[{request.start_time}, {request.end_time}]")
            
            # Use copernicusmarine subset to download data
            # The API automatically handles authentication
            try:
                cm.subset(
                    dataset_id=self.dataset_id,
                    variables=['uo', 'vo'],  # eastward and northward velocities
                    minimum_longitude=request.min_lon,
                    maximum_longitude=request.max_lon,
                    minimum_latitude=request.min_lat,
                    maximum_latitude=request.max_lat,
                    start_datetime=request.start_time.strftime('%Y-%m-%d'),
                    end_datetime=request.end_time.strftime('%Y-%m-%d'),
                    output_filename=output_path,
                    username=self.username,
                    password=self.password,
                    force_download=True
                )
                
                logger.info(f"Successfully downloaded ocean currents to {output_path}")
                return output_path
                
            except Exception as e:
                logger.error(f"Error using copernicusmarine subset: {e}")
                # Try alternative approach using open_dataset
                logger.info("Attempting alternative download method...")
                
                ds = cm.open_dataset(
                    dataset_id=self.dataset_id,
                    username=self.username,
                    password=self.password
                )
                
                # Subset the dataset
                ds_subset = ds.sel(
                    latitude=slice(request.min_lat, request.max_lat),
                    longitude=slice(request.min_lon, request.max_lon),
                    time=slice(request.start_time, request.end_time)
                )
                
                # Save to NetCDF
                ds_subset.to_netcdf(output_path)
                ds.close()
                
                logger.info(f"Successfully downloaded ocean currents to {output_path}")
                return output_path
                
        except ImportError:
            logger.error("copernicusmarine package not installed. "
                        "Install with: pip install copernicusmarine")
            return None
        except Exception as e:
            logger.error(f"Error fetching ocean currents from Copernicus: {e}")
            return None
    
    def get_available_variables(self) -> list:
        """Get list of available variables"""
        return [
            'uo',  # Eastward sea water velocity
            'vo',  # Northward sea water velocity
            'thetao',  # Sea water potential temperature
            'so',  # Sea water salinity
        ]
    
    def is_available(self) -> bool:
        """Check if client is properly configured"""
        return bool(self.username and self.password)
