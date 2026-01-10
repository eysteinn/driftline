"""
Main Data Aggregator Service with scheduling
"""
import logging
import sys
import signal
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import config
from app.services import DatabaseService, StorageService
from app.collectors import NOAAWindCollector, CopernicusOceanCollector

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class DataAggregatorService:
    """Main service for data aggregation"""
    
    def __init__(self):
        """Initialize the data aggregator service"""
        logger.info("Initializing Data Aggregator Service")
        
        # Initialize services
        self.db_service = DatabaseService()
        self.storage_service = StorageService()
        
        # Initialize collectors
        self.wind_collector = NOAAWindCollector(
            db_service=self.db_service,
            storage_service=self.storage_service
        )
        self.ocean_collector = CopernicusOceanCollector(
            db_service=self.db_service,
            storage_service=self.storage_service
        )
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def collect_all_historical(self):
        """Collect historical data from all sources"""
        logger.info("=== Starting historical data collection ===")
        
        # Collect historical data for the past N days
        days_back = config.HISTORICAL_DAYS
        
        try:
            # Collect wind data for each day
            logger.info(f"Collecting wind data for past {days_back} days")
            for day in range(days_back):
                logger.info(f"Collecting wind data for {day} days back")
                self.wind_collector.collect_historical(days_back=day)
            
            # Collect ocean currents data for each day
            if self.ocean_collector.is_available():
                logger.info(f"Collecting ocean currents for past {days_back} days")
                for day in range(days_back):
                    logger.info(f"Collecting ocean currents for {day} days back")
                    self.ocean_collector.collect_historical(days_back=day)
            else:
                logger.warning("Ocean currents collector not available - skipping")
            
            logger.info("=== Historical data collection completed ===")
            
        except Exception as e:
            logger.error(f"Error during historical collection: {e}")
    
    def collect_all_forecasts(self):
        """Collect latest forecast data from all sources"""
        logger.info("=== Starting forecast data collection ===")
        return
        forecast_hours = config.FORECAST_HOURS
        
        try:
            # Collect wind forecasts
            logger.info(f"Collecting wind forecasts for {forecast_hours} hours")
            self.wind_collector.collect_forecast(forecast_hours=forecast_hours)
            
            # Collect ocean currents forecasts
            if self.ocean_collector.is_available():
                logger.info(f"Collecting ocean currents forecasts for {forecast_hours} hours")
                self.ocean_collector.collect_forecast(forecast_hours=forecast_hours)
            else:
                logger.warning("Ocean currents collector not available - skipping")
            
            logger.info("=== Forecast data collection completed ===")
            
        except Exception as e:
            logger.error(f"Error during forecast collection: {e}")
    
    def cleanup_old_data(self):
        """Clean up old data from storage and database"""
        logger.info("=== Starting data cleanup ===")
        
        try:
            max_age_days = config.MAX_DATA_AGE_DAYS
            logger.info(f"Removing datasets older than {max_age_days} days")
            
            # Get old datasets from database
            deleted = self.db_service.cleanup_old_datasets(max_age_days)
            
            # Delete files from storage
            for record in deleted:
                dataset_id, file_path = record
                if file_path:
                    logger.info(f"Deleting file: {file_path}")
                    self.storage_service.delete_file(file_path)
            
            logger.info(f"=== Data cleanup completed: removed {len(deleted)} datasets ===")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def setup_scheduled_jobs(self):
        """Setup scheduled jobs"""
        logger.info("Setting up scheduled jobs")
        
        # Schedule data collection
        collection_trigger = CronTrigger.from_crontab(config.COLLECTION_SCHEDULE)
        self.scheduler.add_job(
            self.collect_all_forecasts,
            trigger=collection_trigger,
            id='collect_forecasts',
            name='Collect forecast data',
            replace_existing=True
        )
        logger.info(f"Scheduled forecast collection: {config.COLLECTION_SCHEDULE}")
        
        # Schedule cleanup
        cleanup_trigger = CronTrigger.from_crontab(config.CLEANUP_SCHEDULE)
        self.scheduler.add_job(
            self.cleanup_old_data,
            trigger=cleanup_trigger,
            id='cleanup_data',
            name='Clean up old data',
            replace_existing=True
        )
        logger.info(f"Scheduled data cleanup: {config.CLEANUP_SCHEDULE}")
    
    def start(self):
        """Start the aggregator service"""
        logger.info("Starting Data Aggregator Service")
        
        # At startup, check for historical data
        logger.info("Checking for historical data...")
        self.collect_all_historical()
        
        # Collect initial forecast data
        logger.info("Collecting initial forecast data...")
        #self.collect_all_forecasts()
        
        # Setup and start scheduler
        #self.setup_scheduled_jobs()
        #self.scheduler.start()
        logger.info("Scheduler started")
        
        # Print scheduled jobs
        #jobs = self.scheduler.get_jobs()
        #logger.info(f"Active scheduled jobs: {len(jobs)}")
        #for job in jobs:
        #    logger.info(f"  - {job.name} (next run: {job.next_run_time})")
        
        self.running = True
        logger.info("Data Aggregator Service is running")
        
        # Keep the service running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.stop()
    
    def stop(self):
        """Stop the aggregator service"""
        logger.info("Stopping Data Aggregator Service")
        self.running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        
        # Close database connection
        self.db_service.close()
        logger.info("Database connection closed")
        
        logger.info("Data Aggregator Service stopped")


def main():
    """Main entry point"""
    logger.info("=== Driftline Data Aggregator Service ===")
    logger.info(f"Configuration:")
    logger.info(f"  Historical days: {config.HISTORICAL_DAYS}")
    logger.info(f"  Forecast hours: {config.FORECAST_HOURS}")
    logger.info(f"  Collection schedule: {config.COLLECTION_SCHEDULE}")
    logger.info(f"  Cleanup schedule: {config.CLEANUP_SCHEDULE}")
    logger.info(f"  Max data age: {config.MAX_DATA_AGE_DAYS} days")
    
    service = DataAggregatorService()
    service.start()


if __name__ == '__main__':
    main()
