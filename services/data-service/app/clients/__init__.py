"""Clients package for external data sources"""
from .copernicus import CopernicusClient
from .noaa import NOAAGFSClient, NOAAWaveWatchClient

__all__ = [
    'CopernicusClient',
    'NOAAGFSClient',
    'NOAAWaveWatchClient',
]
