# Driftline Architecture

This document describes the technical architecture of the Driftline SAR drift forecasting platform.

## System Overview

Driftline is a microservices-based SaaS platform built with:
- **Frontend**: React + TypeScript
- **API Server**: Go (Gin framework)
- **Drift Worker**: Python + OpenDrift
- **Data Service**: Go
- **Results Processor**: Python
- **Infrastructure**: Docker, PostgreSQL, Redis, MinIO

## Architecture Diagram

```
                                Internet
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  Nginx (Port 80) │
                        │  Reverse Proxy   │
                        └──────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
    ┌───────────────────┐         ┌─────────────────┐
    │   Frontend        │         │   API Server    │
    │   (React)         │         │   (Go/Gin)      │
    │   Port 3000       │         │   Port 8000     │
    └───────────────────┘         └────────┬────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                        ▼                  ▼                  ▼
                  ┌──────────┐      ┌──────────┐      ┌──────────┐
                  │PostgreSQL│      │  Redis   │      │  MinIO   │
                  │Database  │      │  Queue   │      │  S3      │
                  └──────────┘      └────┬─────┘      └──────────┘
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                        ▼                ▼                ▼
                ┌──────────────┐  ┌──────────┐  ┌───────────────┐
                │Data Service  │  │  Drift   │  │   Results     │
                │    (Go)      │  │ Worker   │  │  Processor    │
                │              │  │(Python)  │  │  (Python)     │
                └──────────────┘  └──────────┘  └───────────────┘
```

## Components

### 1. Frontend (React + TypeScript)

**Purpose**: User interface for mission creation and visualization

**Technologies**:
- React 18 with TypeScript
- Vite for build tooling
- Material-UI for components
- Leaflet for mapping
- React Query for data fetching
- Zustand for state management

**Key Features**:
- Interactive map for position input
- Mission configuration forms
- Real-time job status updates
- Results visualization (heatmaps, trajectories)
- User authentication and account management

**Deployment**:
- Development: Runs on Vite dev server (port 3000)
- Production: Built as static files served by Nginx

**Environment Variables**:
- `VITE_API_BASE_URL`: Backend API endpoint
- `VITE_WS_URL`: WebSocket endpoint for real-time updates

### 2. API Server (Go)

**Purpose**: Central API gateway for authentication, missions, and billing

**Technologies**:
- Go 1.21+
- Gin web framework
- GORM for database operations
- JWT for authentication
- go-redis for cache/queue

**Responsibilities**:
- User authentication and authorization
- Mission CRUD operations
- Job queue management
- Billing and subscription handling
- WebSocket connections for real-time updates
- Rate limiting and API key validation

**Key Endpoints**:
```
POST   /v1/auth/register      - Register new user
POST   /v1/auth/login         - Login
POST   /v1/missions           - Create mission
GET    /v1/missions           - List missions
GET    /v1/missions/:id       - Get mission details
DELETE /v1/missions/:id       - Delete mission
GET    /v1/missions/:id/status - Get job status
GET    /v1/missions/:id/results - Download results
WS     /v1/ws/missions/:id    - Real-time updates
```

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `JWT_SECRET_KEY`: JWT signing key
- `S3_ENDPOINT`: MinIO endpoint
- `STRIPE_API_KEY`: Payment processing

### 3. Database (PostgreSQL)

**Purpose**: Persistent storage for all application data

**Schema**:
- `users` - User accounts and authentication
- `api_keys` - API key management
- `missions` - Mission metadata
- `mission_results` - Simulation outputs
- `subscriptions` - User subscriptions
- `usage_records` - Usage tracking
- `invoices` - Billing records
- `audit_logs` - Activity tracking

**Extensions**:
- uuid-ossp - UUID generation
- postgis - Geospatial support

### 4. Redis

**Purpose**: Cache, job queue, and pub/sub

**Use Cases**:
- Session storage
- Rate limiting counters
- Job queue for drift simulations
- API response caching
- WebSocket pub/sub for real-time updates

**Configuration**:
- Database 0: Job queue and sessions
- Database 1: Data service cache

### 5. MinIO (S3-Compatible Object Storage)

**Purpose**: Store environmental data and results

**Bucket Structure**:
```
driftline-data/
  ├── ocean_currents/
  ├── wind/
  └── waves/

driftline-results/
  └── {mission_id}/
      ├── raw/particles.nc
      ├── processed/trajectories.geojson
      ├── visualizations/heatmap.png
      └── report.pdf
```

**Access**:
- API: S3 SDK
- Console: http://localhost:9001

### 6. Drift Worker (Python)

**Purpose**: Execute OpenDrift Lagrangian particle simulations

**Technologies**:
- Python 3.11
- OpenDrift 1.11+
- NumPy, xarray for data processing
- boto3 for S3 access

**Workflow**:
1. Poll Redis queue for jobs
2. Download forcing data from MinIO
3. Initialize OpenDrift Leeway model
4. Seed particles at last known position
5. Run forward simulation
6. Export NetCDF outputs
7. Upload results to MinIO
8. Update mission status in database

**Scaling**: Horizontally scalable - run multiple workers

### 7. Data Service (Go)

**Purpose**: Manage environmental forcing data

**Responsibilities**:
- Fetch ocean currents, wind, wave data
- Spatial and temporal subsetting
- Data caching and serving
- Integration with external data sources (NOAA, Copernicus)

**Data Sources**:
- Ocean currents: Copernicus Marine
- Wind: NOAA GFS
- Waves: NOAA WaveWatch III

### 8. Results Processor (Python)

**Purpose**: Generate derived products from simulation outputs

**Technologies**:
- Python 3.11
- Shapely for geometry operations
- Rasterio for grid processing
- ReportLab/WeasyPrint for PDF generation

**Outputs**:
- Probability density grids (50%, 90%, 95% contours)
- Search area polygons (GeoJSON)
- Most likely position (centroid)
- Heatmap visualizations (PNG)
- PDF SAR reports

### 9. Nginx

**Purpose**: Reverse proxy and load balancer

**Responsibilities**:
- SSL/TLS termination (production)
- Route requests to frontend and API
- Static file serving
- Rate limiting
- Compression (gzip, brotli)

**Configuration**:
- Development: nginx.dev.conf
- Production: nginx.prod.conf with SSL

### 10. Monitoring (Prometheus + Grafana)

**Purpose**: System observability and alerting

**Metrics Collected**:
- API request rates and latencies
- Mission creation/completion rates
- Job queue depth
- Worker utilization
- Database performance
- Storage usage

**Dashboards**:
- System overview
- Mission analytics
- Infrastructure metrics
- Billing and usage

## Data Flow

### Mission Creation Flow

```
1. User submits mission via Frontend
2. Frontend → API Server (POST /v1/missions)
3. API Server validates and stores in PostgreSQL
4. API Server enqueues job in Redis
5. API Server returns mission ID to Frontend
6. Frontend subscribes to WebSocket for updates
```

### Drift Simulation Flow

```
1. Drift Worker polls Redis queue
2. Worker requests forcing data from Data Service
3. Data Service fetches from cache or downloads
4. Worker initializes OpenDrift with mission params
5. Worker runs simulation (5-60 seconds)
6. Worker exports NetCDF to MinIO
7. Results Processor generates derived products
8. Processor uploads products to MinIO
9. Processor updates mission status in PostgreSQL
10. API Server emits WebSocket event to Frontend
11. User downloads results
```

## Deployment

### Development

```bash
docker-compose -f docker-compose.dev.yml up --build
```

Services run with hot-reloading and debug logging.

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Services run optimized with:
- Resource limits
- Health checks
- Restart policies
- Log rotation
- SSL/TLS

### Scaling Strategy

**Horizontal Scaling**:
- API Server: Load balance multiple instances
- Drift Workers: Deploy additional workers
- Data Service: Run multiple replicas
- Results Processor: Scale based on queue depth

**Vertical Scaling**:
- Database: Larger instance for high load
- Redis: Scale to cluster mode
- MinIO: Distributed mode with erasure coding

## Security

### Network Security
- Internal Docker network for service communication
- Only Nginx exposed to public internet
- Rate limiting on API endpoints
- DDoS protection (via Cloudflare in production)

### Data Security
- Encryption at rest (MinIO with KMS)
- Encryption in transit (TLS 1.3)
- Database SSL connections
- Secrets managed via environment variables or Vault

### Application Security
- Input validation
- SQL injection prevention (GORM)
- JWT token expiration
- API key rotation support
- CORS configuration
- Security headers

### Container Security
- Non-root users
- Minimal base images (Alpine)
- Regular security scanning
- Read-only root filesystems where possible

## Performance Optimization

### Database
- Indexes on frequently queried columns
- Connection pooling
- Query optimization
- Partitioning for large tables

### Caching
- Redis for API responses (60s TTL)
- Browser caching for static assets
- Data service pre-warming cache

### API
- Response pagination
- Field filtering
- Compression (gzip)
- HTTP/2

## Disaster Recovery

### Backups
- PostgreSQL: Daily pg_dump to S3 Glacier
- MinIO: Bucket replication
- Redis: RDB snapshots + AOF

### Recovery Procedures
- Database restore from latest backup
- Service restart via Docker Compose
- Data recovery from MinIO replicas

## Monitoring and Alerting

### Key Metrics
- Mission creation rate
- Average simulation time
- Job queue length
- API response time (p50, p95, p99)
- Error rate
- Resource utilization

### Alerts
- High job queue depth (>50 for 5 min)
- High API latency (>2s p95)
- Worker down
- Database connection issues
- Disk space low

## Future Enhancements

- Kubernetes deployment for production
- Multi-region support
- Advanced visualizations (animations)
- Machine learning drift corrections
- AIS data integration
- Enterprise SSO (OAuth2)
- GraphQL API option
