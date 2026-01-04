"""
Basic tests for data service
"""
import pytest
from datetime import datetime, timedelta
from app.models import DataRequest, DataType


def test_data_request_validation():
    """Test DataRequest validation"""
    # Valid request
    req = DataRequest(
        data_type=DataType.OCEAN_CURRENTS,
        min_lat=60.0,
        max_lat=70.0,
        min_lon=-20.0,
        max_lon=-10.0,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=24)
    )
    req.validate()  # Should not raise
    
    # Invalid lat bounds
    req_invalid_lat = DataRequest(
        data_type=DataType.OCEAN_CURRENTS,
        min_lat=70.0,
        max_lat=60.0,  # max < min
        min_lon=-20.0,
        max_lon=-10.0,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=24)
    )
    with pytest.raises(ValueError, match="min_lat must be less than max_lat"):
        req_invalid_lat.validate()
    
    # Invalid lon bounds
    req_invalid_lon = DataRequest(
        data_type=DataType.OCEAN_CURRENTS,
        min_lat=60.0,
        max_lat=70.0,
        min_lon=-10.0,
        max_lon=-20.0,  # max < min
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=24)
    )
    with pytest.raises(ValueError, match="min_lon must be less than max_lon"):
        req_invalid_lon.validate()
    
    # Invalid time range
    req_invalid_time = DataRequest(
        data_type=DataType.OCEAN_CURRENTS,
        min_lat=60.0,
        max_lat=70.0,
        min_lon=-20.0,
        max_lon=-10.0,
        start_time=datetime.utcnow() + timedelta(hours=24),
        end_time=datetime.utcnow()  # end < start
    )
    with pytest.raises(ValueError, match="start_time must be before end_time"):
        req_invalid_time.validate()


def test_data_types():
    """Test DataType enum"""
    assert DataType.OCEAN_CURRENTS.value == "ocean_currents"
    assert DataType.WIND.value == "wind"
    assert DataType.WAVES.value == "waves"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
