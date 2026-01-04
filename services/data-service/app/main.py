"""
Main Flask application for Driftline Data Service
"""
import logging
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config
from app.services import CacheService, StorageService, DataService
from app.handlers import data_bp, init_handlers

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Initialize services
    logger.info("Initializing services...")
    
    # Cache service
    cache_service = CacheService()
    if cache_service.is_available():
        logger.info("Cache service initialized successfully")
    else:
        logger.warning("Cache service unavailable, continuing without cache")
    
    # Storage service
    storage_service = StorageService()
    if storage_service.is_available():
        logger.info("Storage service initialized successfully")
    else:
        logger.warning("Storage service unavailable, continuing without storage")
    
    # Data service
    data_service = DataService(
        cache_service=cache_service,
        storage_service=storage_service
    )
    logger.info("Data service initialized successfully")
    
    # Initialize handlers
    init_handlers(data_service)
    
    # Register blueprints
    app.register_blueprint(data_bp, url_prefix='/v1/data')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'driftline-data-service',
            'cache': cache_service.is_available(),
            'storage': storage_service.is_available(),
        }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint"""
        return jsonify({
            'service': 'Driftline Data Service',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'ocean_currents': '/v1/data/ocean-currents',
                'wind': '/v1/data/wind',
                'waves': '/v1/data/waves'
            }
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
    logger.info("Flask application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    logger.info(f"Starting Data Service on {config.HOST}:{config.PORT}")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
