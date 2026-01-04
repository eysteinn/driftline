"""
API handlers for environmental data endpoints
"""
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from app.models import (
    DataRequest, DataType, InvalidBoundsError,
    InvalidTimeRangeError, DataNotFoundError, ExternalSourceError
)
from app.services import DataService

logger = logging.getLogger(__name__)

# Create blueprint
data_bp = Blueprint('data', __name__)

# Data service will be injected
_data_service: DataService = None


def init_handlers(data_service: DataService):
    """Initialize handlers with data service"""
    global _data_service
    _data_service = data_service


@data_bp.route('/ocean-currents', methods=['GET'])
def get_ocean_currents():
    """Get ocean currents data"""
    return _handle_data_request(DataType.OCEAN_CURRENTS)


@data_bp.route('/wind', methods=['GET'])
def get_wind():
    """Get wind data"""
    return _handle_data_request(DataType.WIND)


@data_bp.route('/waves', methods=['GET'])
def get_waves():
    """Get wave data"""
    return _handle_data_request(DataType.WAVES)


def _handle_data_request(data_type: DataType):
    """
    Handle data request for any data type
    
    Args:
        data_type: Type of data requested
        
    Returns:
        JSON response
    """
    try:
        # Parse query parameters
        data_request = _parse_query_params(data_type)
        
        # Get data from service
        response = _data_service.get_data(data_request)
        
        # Return JSON response
        return jsonify(response.to_dict()), 200
        
    except (InvalidBoundsError, InvalidTimeRangeError, ValueError) as e:
        logger.warning(f"Invalid request: {e}")
        return jsonify({'error': str(e)}), 400
    
    except DataNotFoundError as e:
        logger.warning(f"Data not found: {e}")
        return jsonify({'error': str(e)}), 404
    
    except ExternalSourceError as e:
        logger.error(f"External source error: {e}")
        return jsonify({'error': str(e)}), 502
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _parse_query_params(data_type: DataType) -> DataRequest:
    """
    Parse query parameters into DataRequest
    
    Args:
        data_type: Type of data requested
        
    Returns:
        DataRequest object
        
    Raises:
        ValueError: If required parameters are missing or invalid
    """
    # Required spatial bounds
    try:
        min_lat = float(request.args.get('min_lat'))
        max_lat = float(request.args.get('max_lat'))
        min_lon = float(request.args.get('min_lon'))
        max_lon = float(request.args.get('max_lon'))
    except (TypeError, ValueError) as e:
        raise ValueError(
            "Missing or invalid spatial bounds. "
            "Required: min_lat, max_lat, min_lon, max_lon"
        ) from e
    
    # Temporal bounds (with defaults)
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid start_time format. Expected ISO 8601 format: {e}"
            ) from e
    else:
        # Default to current time
        start_time = datetime.now(timezone.utc)
    
    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid end_time format. Expected ISO 8601 format: {e}"
            ) from e
    else:
        # Default to 48 hours from start
        end_time = start_time + timedelta(hours=48)
    
    # Optional parameters
    resolution = request.args.get('resolution')
    variables = request.args.getlist('variables') or None
    
    return DataRequest(
        data_type=data_type,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        resolution=resolution,
        variables=variables
    )
