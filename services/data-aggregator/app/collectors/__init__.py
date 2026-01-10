"""
Data collectors package
"""
from app.collectors.base import BaseCollector
from app.collectors.noaa_wind import NOAAWindCollector
from app.collectors.copernicus_ocean import CopernicusOceanCollector

__all__ = ['BaseCollector', 'NOAAWindCollector', 'CopernicusOceanCollector']
