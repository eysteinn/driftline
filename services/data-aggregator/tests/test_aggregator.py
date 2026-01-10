"""
Tests for Data Aggregator Service
"""
import pytest
from datetime import datetime, timezone
from app.config import config
from app.models import DatasetRecord


def test_config_defaults():
    """Test that config has proper defaults"""
    assert config.HISTORICAL_DAYS == 7
    assert config.FORECAST_HOURS == 120
    assert config.FORECAST_INTERVAL_HOURS == 3
    assert config.MAX_DATA_AGE_DAYS == 14


def test_dataset_record_creation():
    """Test DatasetRecord model"""
    record = DatasetRecord(
        data_type="wind",
        source="noaa_gfs",
        forecast_date=datetime.now(timezone.utc),
        forecast_cycle="00",
        valid_time_start=datetime.now(timezone.utc),
        valid_time_end=datetime.now(timezone.utc),
        file_path="wind/2024/01/01/00/test.grib2",
        file_size_bytes=1024,
        is_forecast=False
    )
    
    assert record.data_type == "wind"
    assert record.source == "noaa_gfs"
    assert record.file_size_bytes == 1024
    assert record.is_forecast is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
