"""
Database service for tracking datasets
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from app.config import config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for interacting with PostgreSQL database"""
    
    def __init__(self):
        """Initialize database service"""
        self.conn = None
        self.connect()
        self.ensure_tables()
    
    def connect(self):
        """Connect to the database"""
        try:
            self.conn = psycopg2.connect(config.DATABASE_URL)
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def ensure_tables(self):
        """Ensure required tables exist"""
        try:
            with self.conn.cursor() as cur:
                # Create datasets table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS aggregator_datasets (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        data_type VARCHAR(50) NOT NULL,
                        source VARCHAR(50) NOT NULL,
                        run_time TIMESTAMP NOT NULL,
                        valid_time TIMESTAMP NOT NULL,
                        file_path VARCHAR(500) NOT NULL,
                        file_size_bytes BIGINT,
                        is_forecast BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        last_accessed_at TIMESTAMP,
                        UNIQUE(data_type, source, run_time, valid_time)
                    )
                """)
                
                # Create indexes
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_datasets_type 
                    ON aggregator_datasets(data_type)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_datasets_run_time 
                    ON aggregator_datasets(run_time DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_datasets_valid_time 
                    ON aggregator_datasets(valid_time DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_datasets_created 
                    ON aggregator_datasets(created_at DESC)
                """)
                
                # Create collection status table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS aggregator_collection_status (
                        collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        data_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        records_collected INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                """)
                
                self.conn.commit()
                logger.info("Database tables ensured")
                
        except Exception as e:
            logger.error(f"Failed to ensure tables: {e}")
            self.conn.rollback()
            raise
    
    def record_dataset(
        self,
        data_type: str,
        source: str,
        run_time: datetime,
        valid_time: datetime,
        file_path: str,
        file_size_bytes: int,
        is_forecast: bool = False
    ) -> Optional[str]:
        """
        Record a new dataset
        
        Args:
            data_type: Type of data (e.g., 'wind', 'currents')
            source: Data source (e.g., 'noaa_gfs', 'copernicus')
            run_time: When the data was created/generated (model run time)
            valid_time: What time period the data represents (valid for)
            file_path: Path to file in storage
            file_size_bytes: Size of file in bytes
            is_forecast: Whether this is forecast data
        
        Returns:
            Dataset ID if successful, None otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO aggregator_datasets 
                    (data_type, source, run_time, valid_time,
                     file_path, file_size_bytes, is_forecast)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (data_type, source, run_time, valid_time)
                    DO UPDATE SET 
                        file_path = EXCLUDED.file_path,
                        file_size_bytes = EXCLUDED.file_size_bytes,
                        created_at = NOW()
                    RETURNING id
                """, (
                    data_type, source, run_time, valid_time,
                    file_path, file_size_bytes, is_forecast
                ))
                
                result = cur.fetchone()
                self.conn.commit()
                
                if result:
                    dataset_id = str(result[0])
                    logger.info(f"Recorded dataset {dataset_id} for {data_type}")
                    return dataset_id
                    
        except Exception as e:
            logger.error(f"Failed to record dataset: {e}")
            self.conn.rollback()
            return None
    
    def dataset_exists(
        self,
        data_type: str,
        source: str,
        run_time: datetime,
        valid_time: datetime
    ) -> bool:
        """
        Check if a dataset already exists in the database
        
        Args:
            data_type: Type of data
            source: Data source
            run_time: Model run time
            valid_time: Valid time
            
        Returns:
            True if dataset exists, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM aggregator_datasets
                    WHERE data_type = %s 
                      AND source = %s 
                      AND run_time = %s 
                      AND valid_time = %s
                """, (data_type, source, run_time, valid_time))
                
                return cur.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check dataset existence: {e}")
            return False
    
    def get_available_datasets(
        self,
        data_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        is_forecast: Optional[bool] = None
    ) -> List[dict]:
        """
        Get available datasets matching criteria
        
        Args:
            data_type: Filter by data type
            start_time: Filter by valid time start
            end_time: Filter by valid time end
            is_forecast: Filter by forecast/historical flag
            
        Returns:
            List of dataset records
        """
        try:
            # Build WHERE clause from hardcoded conditions only
            # All user input is passed as parameterized values
            conditions = []
            params = []
            
            if data_type:
                conditions.append("data_type = %s")
                params.append(data_type)
            
            if start_time:
                conditions.append("valid_time_end >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("valid_time_start <= %s")
                params.append(end_time)
            
            if is_forecast is not None:
                conditions.append("is_forecast = %s")
                params.append(is_forecast)
            
            # Safe to use f-string here as where_clause only contains hardcoded SQL fragments
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT * FROM aggregator_datasets
                    WHERE {where_clause}
                    ORDER BY forecast_date DESC, valid_time_start
                """, params)
                
                return [dict(row) for row in cur.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get available datasets: {e}")
            return []
    
    def cleanup_old_datasets(self, max_age_days: int) -> List[tuple]:
        """
        Clean up datasets older than max_age_days
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            List of tuples containing (id, file_path) for deleted datasets
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM aggregator_datasets
                    WHERE created_at < %s
                    RETURNING id, file_path
                """, (cutoff_date,))
                
                deleted = cur.fetchall()
                self.conn.commit()
                
                logger.info(f"Cleaned up {len(deleted)} old datasets")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup old datasets: {e}")
            self.conn.rollback()
            return []
    
    def start_collection(self, data_type: str) -> str:
        """Start a new collection run"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO aggregator_collection_status 
                    (data_type, status, started_at)
                    VALUES (%s, 'running', NOW())
                    RETURNING collection_id
                """, (data_type,))
                
                result = cur.fetchone()
                self.conn.commit()
                
                if result:
                    return str(result[0])
                    
        except Exception as e:
            logger.error(f"Failed to start collection: {e}")
            self.conn.rollback()
            return None
    
    def complete_collection(
        self,
        collection_id: str,
        records_collected: int,
        error_message: Optional[str] = None
    ):
        """Mark a collection run as complete"""
        try:
            status = 'failed' if error_message else 'completed'
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE aggregator_collection_status
                    SET status = %s,
                        completed_at = NOW(),
                        records_collected = %s,
                        error_message = %s
                    WHERE collection_id = %s
                """, (status, records_collected, error_message, collection_id))
                
                self.conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to complete collection: {e}")
            self.conn.rollback()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
