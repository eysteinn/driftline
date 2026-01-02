#!/usr/bin/env python3
"""
Driftline Results Processor
Processes OpenDrift outputs and generates derived products
"""

import os
import sys
import time
import logging
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import io

import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import xarray as xr
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import unary_union
import geopandas as gpd
from scipy.ndimage import gaussian_filter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResultsProcessor:
    """Processor for generating derived products from simulation results"""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.database_url = os.getenv('DATABASE_URL')
        self.s3_endpoint = os.getenv('S3_ENDPOINT')
        self.s3_access_key = os.getenv('S3_ACCESS_KEY')
        self.s3_secret_key = os.getenv('S3_SECRET_KEY')
        self.results_bucket = os.getenv('RESULTS_BUCKET', 'driftline-results')
        self.results_queue = os.getenv('RESULTS_QUEUE', 'results_processing')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '5'))
        
        # Initialize connections
        self._init_connections()
        
        logger.info("Initialized ResultsProcessor")
    
    def _init_connections(self):
        """Initialize connections to Redis, database, and S3"""
        # Redis
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        logger.info("Connected to Redis")
        
        # Database
        self.db_conn = psycopg2.connect(self.database_url)
        self.db_conn.autocommit = False
        logger.info("Connected to database")
        
        # S3/MinIO
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            config=Config(signature_version='s3v4')
        )
        logger.info("Connected to S3")
    
    def _download_from_s3(self, s3_path: str, local_path: str):
        """Download file from S3 to local path"""
        # Parse S3 path (s3://bucket/key)
        if not s3_path.startswith('s3://'):
            raise ValueError(f"Invalid S3 path: {s3_path}")
        
        path_parts = s3_path[5:].split('/', 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ''
        
        logger.info(f"Downloading from S3: {bucket}/{key}")
        self.s3_client.download_file(bucket, key, local_path)
    
    def _upload_to_s3(self, local_path: str, s3_key: str) -> str:
        """Upload file to S3 and return S3 URI"""
        try:
            # Ensure bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.results_bucket)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ('404', 'NoSuchBucket'):
                    self.s3_client.create_bucket(Bucket=self.results_bucket)
                    logger.info(f"Created bucket: {self.results_bucket}")
                else:
                    raise
            
            # Upload file
            self.s3_client.upload_file(local_path, self.results_bucket, s3_key)
            s3_path = f"s3://{self.results_bucket}/{s3_key}"
            logger.info(f"Uploaded to {s3_path}")
            return s3_path
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
    
    def _calculate_density_and_contours(self, ds: xr.Dataset, final_time_idx: int = -1) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
        """Calculate particle density and probability contours"""
        # Get final positions
        lons = ds['lon'].isel(time=final_time_idx).values
        lats = ds['lat'].isel(time=final_time_idx).values
        
        # Remove NaN values (stranded particles)
        valid_mask = ~(np.isnan(lons) | np.isnan(lats))
        lons = lons[valid_mask]
        lats = lats[valid_mask]
        
        if len(lons) == 0:
            logger.warning("No valid particles at final time")
            return None, None, None, {}
        
        # Create density grid
        lon_bins = np.linspace(lons.min() - 0.5, lons.max() + 0.5, 100)
        lat_bins = np.linspace(lats.min() - 0.5, lats.max() + 0.5, 100)
        
        density, lon_edges, lat_edges = np.histogram2d(
            lons, lats, bins=[lon_bins, lat_bins]
        )
        
        # Smooth density
        density_smooth = gaussian_filter(density.T, sigma=2)
        density_smooth = density_smooth / density_smooth.sum()  # Normalize
        
        # Calculate centroid (most likely position)
        lon_centers = (lon_edges[:-1] + lon_edges[1:]) / 2
        lat_centers = (lat_edges[:-1] + lat_edges[1:]) / 2
        
        centroid_lon = np.average(lon_centers, weights=density_smooth.sum(axis=0))
        centroid_lat = np.average(lat_centers, weights=density_smooth.sum(axis=1))
        
        # Calculate probability contours
        flat_density = density_smooth.flatten()
        sorted_density = np.sort(flat_density)[::-1]
        cumsum = np.cumsum(sorted_density)
        
        # Find thresholds for 50% and 90% probability
        threshold_50 = sorted_density[np.where(cumsum >= 0.50)[0][0]]
        threshold_90 = sorted_density[np.where(cumsum >= 0.90)[0][0]]
        
        contours = {
            '50': threshold_50,
            '90': threshold_90,
            'centroid_lon': float(centroid_lon),
            'centroid_lat': float(centroid_lat),
            'lon_centers': lon_centers,
            'lat_centers': lat_centers
        }
        
        return density_smooth, lon_centers, lat_centers, contours
    
    def _create_search_area_polygon(self, density: np.ndarray, lon_centers: np.ndarray, 
                                    lat_centers: np.ndarray, threshold: float) -> Optional[dict]:
        """Create GeoJSON polygon from density contour"""
        # Create contour mask
        mask = density >= threshold
        
        # Find contiguous regions
        from scipy import ndimage
        labeled, num_features = ndimage.label(mask)
        
        if num_features == 0:
            return None
        
        # Get the largest region
        sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
        largest_label = np.argmax(sizes) + 1
        largest_mask = (labeled == largest_label)
        
        # Extract boundary points
        from skimage import measure
        contours = measure.find_contours(largest_mask, 0.5)
        
        if len(contours) == 0:
            return None
        
        # Convert to lat/lon coordinates
        contour = contours[0]
        
        # Map indices to coordinates
        lat_coords = lat_centers[np.clip(contour[:, 0].astype(int), 0, len(lat_centers) - 1)]
        lon_coords = lon_centers[np.clip(contour[:, 1].astype(int), 0, len(lon_centers) - 1)]
        
        # Create GeoJSON polygon
        coordinates = [[float(lon), float(lat)] for lon, lat in zip(lon_coords, lat_coords)]
        
        # Close the polygon
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        
        geojson = {
            "type": "Polygon",
            "coordinates": [coordinates]
        }
        
        return geojson
    
    def _generate_trajectory_geojson(self, ds: xr.Dataset, mission_id: str) -> str:
        """Generate GeoJSON with particle trajectories"""
        features = []
        
        # Sample a subset of trajectories (max 100 for performance)
        num_particles = ds.dims['trajectory']
        sample_size = min(100, num_particles)
        sample_indices = np.linspace(0, num_particles - 1, sample_size, dtype=int)
        
        for idx in sample_indices:
            lons = ds['lon'].isel(trajectory=idx).values
            lats = ds['lat'].isel(trajectory=idx).values
            
            # Remove NaN values
            valid_mask = ~(np.isnan(lons) | np.isnan(lats))
            if not np.any(valid_mask):
                continue
            
            lons = lons[valid_mask]
            lats = lats[valid_mask]
            
            coordinates = [[float(lon), float(lat)] for lon, lat in zip(lons, lats)]
            
            feature = {
                "type": "Feature",
                "properties": {
                    "trajectory_id": int(idx)
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return json.dumps(geojson)
    
    def _create_heatmap(self, density: np.ndarray, lon_centers: np.ndarray, 
                       lat_centers: np.ndarray, mission_id: str) -> str:
        """Create heatmap visualization and save to file"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create custom colormap
        colors = ['#000033', '#000055', '#0000BB', '#0E4C92', '#2E8BC0', 
                 '#19D3F3', '#FFF000', '#FF6B00', '#E60000']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)
        
        # Plot density
        lon_grid, lat_grid = np.meshgrid(lon_centers, lat_centers)
        im = ax.pcolormesh(lon_grid, lat_grid, density, cmap=cmap, shading='auto')
        
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'Drift Probability Density - Mission {mission_id[:8]}')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Probability Density')
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def _generate_pdf_report(self, mission_id: str, density: np.ndarray, 
                            lon_centers: np.ndarray, lat_centers: np.ndarray,
                            contours: Dict[str, Any], num_particles: int,
                            num_timesteps: int, stranded_count: int) -> str:
        """Generate a PDF report with simulation results"""
        from matplotlib.backends.backend_pdf import PdfPages
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        
        with PdfPages(temp_file.name) as pdf:
            # Page 1: Title and Summary
            fig = plt.figure(figsize=(8.5, 11))
            fig.text(0.5, 0.95, 'SAR Drift Forecast Report', 
                    ha='center', va='top', fontsize=20, weight='bold')
            fig.text(0.5, 0.90, f'Mission ID: {mission_id}', 
                    ha='center', va='top', fontsize=12)
            fig.text(0.5, 0.87, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}', 
                    ha='center', va='top', fontsize=10, style='italic')
            
            # Summary statistics
            summary_text = f"""
SIMULATION SUMMARY
─────────────────────────────────────────────────
Particles:            {num_particles:,}
Timesteps:            {num_timesteps}
Stranded:             {stranded_count} ({stranded_count/num_particles*100:.1f}%)

MOST LIKELY POSITION
─────────────────────────────────────────────────
Latitude:             {contours['centroid_lat']:.6f}°
Longitude:            {contours['centroid_lon']:.6f}°

SEARCH AREA CONTOURS
─────────────────────────────────────────────────
50% probability area: {contours.get('50_area_km2', 'N/A')} km²
90% probability area: {contours.get('90_area_km2', 'N/A')} km²
95% probability area: {contours.get('95_area_km2', 'N/A')} km²
            """
            fig.text(0.1, 0.75, summary_text, ha='left', va='top', 
                    fontsize=10, family='monospace')
            
            plt.axis('off')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
            
            # Page 2: Density Heatmap
            fig, ax = plt.subplots(figsize=(8.5, 11))
            colors = ['#000033', '#000055', '#0000BB', '#0E4C92', '#2E8BC0', 
                     '#19D3F3', '#FFF000', '#FF6B00', '#E60000']
            cmap = LinearSegmentedColormap.from_list('custom', colors, N=100)
            
            lon_grid, lat_grid = np.meshgrid(lon_centers, lat_centers)
            im = ax.pcolormesh(lon_grid, lat_grid, density, cmap=cmap, shading='auto')
            
            # Mark centroid
            ax.plot(contours['centroid_lon'], contours['centroid_lat'], 
                   'r*', markersize=20, label='Most Likely Position')
            
            ax.set_xlabel('Longitude', fontsize=12)
            ax.set_ylabel('Latitude', fontsize=12)
            ax.set_title('Drift Probability Density Map', fontsize=14, weight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Probability Density', fontsize=10)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
        
        return temp_file.name
    
    def process_results(self, mission_id: str, netcdf_path: str) -> Dict[str, Any]:
        """
        Process simulation results and generate derived products
        
        Args:
            mission_id: Mission identifier
            netcdf_path: S3 path to OpenDrift NetCDF output
            
        Returns:
            Dictionary with paths to generated products
        """
        logger.info(f"Processing results for mission {mission_id}")
        
        temp_dir = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f'results_{mission_id}_')
            
            # Download NetCDF file from S3
            local_nc_path = os.path.join(temp_dir, 'particles.nc')
            self._download_from_s3(netcdf_path, local_nc_path)
            
            # Load NetCDF file
            logger.info("Loading NetCDF file")
            ds = xr.open_dataset(local_nc_path)
            
            # Get metadata
            num_particles = ds.dims['trajectory']
            num_timesteps = ds.dims['time']
            
            # Count stranded particles (particles with NaN positions at final time)
            final_lons = ds['lon'].isel(time=-1).values
            stranded_count = int(np.isnan(final_lons).sum())
            
            # Calculate final time
            times = ds['time'].values
            final_time = times[-1]
            
            logger.info(f"Processing {num_particles} particles over {num_timesteps} timesteps")
            
            # Calculate density and contours
            density, lon_centers, lat_centers, contours = self._calculate_density_and_contours(ds)
            
            if density is None:
                raise ValueError("Failed to calculate density - no valid particles")
            
            # Generate search area polygons
            search_area_50 = self._create_search_area_polygon(
                density, lon_centers, lat_centers, contours['50']
            )
            search_area_90 = self._create_search_area_polygon(
                density, lon_centers, lat_centers, contours['90']
            )
            
            # Generate GeoJSON trajectories
            logger.info("Generating trajectory GeoJSON")
            geojson_content = self._generate_trajectory_geojson(ds, mission_id)
            geojson_path = os.path.join(temp_dir, 'trajectories.geojson')
            with open(geojson_path, 'w') as f:
                f.write(geojson_content)
            
            # Create heatmap
            logger.info("Creating heatmap visualization")
            heatmap_path = self._create_heatmap(density, lon_centers, lat_centers, mission_id)
            
            # Generate PDF report
            logger.info("Generating PDF report")
            pdf_path = self._generate_pdf_report(
                mission_id, density, lon_centers, lat_centers, contours,
                num_particles, num_timesteps, stranded_count
            )
            
            # Upload products to S3
            logger.info("Uploading products to S3")
            geojson_s3 = self._upload_to_s3(geojson_path, f"{mission_id}/trajectories.geojson")
            heatmap_s3 = self._upload_to_s3(heatmap_path, f"{mission_id}/heatmap.png")
            pdf_s3 = self._upload_to_s3(pdf_path, f"{mission_id}/report.pdf")
            
            # Update database with results
            logger.info("Updating database with results")
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mission_results 
                    SET centroid_lat = %s,
                        centroid_lon = %s,
                        centroid_time = %s,
                        search_area_50_geom = %s,
                        search_area_90_geom = %s,
                        geojson_path = %s,
                        heatmap_path = %s,
                        pdf_report_path = %s,
                        particle_count = %s,
                        stranded_count = %s
                    WHERE mission_id = %s
                    """,
                    (
                        contours['centroid_lat'],
                        contours['centroid_lon'],
                        final_time.astype('datetime64[us]').astype(object),
                        json.dumps(search_area_50) if search_area_50 else None,
                        json.dumps(search_area_90) if search_area_90 else None,
                        geojson_s3,
                        heatmap_s3,
                        pdf_s3,
                        num_particles,
                        stranded_count,
                        mission_id
                    )
                )
                self.db_conn.commit()
            
            ds.close()
            
            logger.info(f"Results processing completed for mission {mission_id}")
            
            return {
                'mission_id': mission_id,
                'status': 'completed',
                'centroid': {
                    'lat': contours['centroid_lat'],
                    'lon': contours['centroid_lon']
                },
                'products': {
                    'netcdf': netcdf_path,
                    'geojson': geojson_s3,
                    'heatmap': heatmap_s3,
                    'pdf': pdf_s3,
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process results for mission {mission_id}: {e}", exc_info=True)
            raise
            
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def run(self):
        """Main processor loop"""
        logger.info("Starting results processor...")
        logger.info(f"Polling queue '{self.results_queue}' every {self.poll_interval} seconds")
        
        while True:
            try:
                # Use blocking pop with timeout
                result = self.redis_client.blpop(self.results_queue, timeout=self.poll_interval)
                
                if result:
                    queue_name, job_data = result
                    logger.info(f"Received job from queue: {queue_name}")
                    
                    try:
                        # Parse job data
                        job = json.loads(job_data)
                        mission_id = job.get('mission_id')
                        netcdf_path = job.get('netcdf_path')
                        
                        if not mission_id or not netcdf_path:
                            logger.error(f"Invalid job data: {job}")
                            continue
                        
                        # Process the results
                        result = self.process_results(mission_id, netcdf_path)
                        logger.info(f"Job completed: {result}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid job data: {e}")
                    except Exception as e:
                        logger.error(f"Error processing job: {e}", exc_info=True)
                
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5)
                try:
                    self._init_connections()
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
            
            except Exception as e:
                logger.error(f"Unexpected error in processor loop: {e}", exc_info=True)
                time.sleep(5)


def main():
    processor = ResultsProcessor()
    
    try:
        processor.run()
    except KeyboardInterrupt:
        logger.info("Processor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Processor error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
