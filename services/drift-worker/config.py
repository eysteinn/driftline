"""
Configuration constants for Drift Worker
"""

# Leeway object types
# Based on OpenDrift Leeway model categories
OBJECT_TYPES = {
    1: "Person-in-water (PIW)",
    2: "Life raft with canopy",
    3: "Life raft without canopy",
    4: "Life raft - general",
    5: "Fishing vessel",
    6: "PIW - vertical",
    7: "Sailing vessel - general",
    8: "Power boat",
    9: "Debris",
    10: "Medical waste",
    11: "Fishing gear",
    12: "Recreational boat",
    13: "Surf board",
    14: "Kayak",
    15: "Canoe",
    16: "Personal watercraft",
}

# Default simulation parameters
DEFAULT_NUM_PARTICLES = 1000
DEFAULT_DURATION_HOURS = 24
DEFAULT_TIME_STEP = 3600  # seconds (1 hour)
DEFAULT_OUTPUT_INTERVAL = 3600  # seconds (1 hour)
DEFAULT_SEED_RADIUS = 100  # meters
DEFAULT_OBJECT_TYPE = 1  # Person-in-water

# S3/MinIO buckets
DATA_BUCKET = "driftline-data"
RESULTS_BUCKET = "driftline-results"

# Redis queue names
JOB_QUEUE = "drift_jobs"
RESULT_QUEUE = "drift_results"

# Mission statuses
STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Forcing data paths
FORCING_DATA_PATHS = {
    "ocean_currents": "ocean_currents",
    "wind": "wind",
    "waves": "waves"
}

# Output formats
OUTPUT_NETCDF = "netcdf"
OUTPUT_GEOJSON = "geojson"
OUTPUT_PNG = "png"

# Pixel size for density maps (meters)
DENSITY_MAP_PIXEL_SIZE = 1000

# OpenDrift model settings
OPENDRIFT_MODEL = "leeway"
OPENDRIFT_LOG_LEVEL = "WARNING"

# Timeout settings
DATABASE_TIMEOUT = 30  # seconds
REDIS_TIMEOUT = 5  # seconds
S3_TIMEOUT = 60  # seconds
DATA_SERVICE_TIMEOUT = 120  # seconds

# Data service configuration
DEFAULT_DATA_SERVICE_URL = "http://data-service:8000"

# Spatial buffer for environmental data requests (degrees)
# Add buffer around mission area to ensure adequate coverage
SPATIAL_BUFFER = 2.0  # degrees
