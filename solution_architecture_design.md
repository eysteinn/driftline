# Driftline – Solution Architecture Design
## Global SAR Drift SaaS Platform

**Product Name:** Driftline  
**Version:** 1.0  
**Date:** December 30, 2025  
**Deployment Strategy:** Docker + Docker Compose

---

## 1. Executive Summary

This document describes the complete technical solution architecture for **Driftline**, a global SAR drift forecasting SaaS platform. The system is designed with a streamlined architecture featuring a single API server that handles authentication, missions, and billing, plus specialized workers for drift computation and data processing. All components are containerized with Docker and deployable via Docker Compose for development and single-node production environments. For production scale-out, the architecture supports Kubernetes orchestration.

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer / Nginx                     │
└──────┬──────────────────────────────────┬─────────────────────┘
       │                                   │
       ▼                                   ▼
┌──────────────┐                   ┌──────────────────────┐
│   Web UI     │                   │   API Server         │
│  (Frontend)  │                   │  - Auth              │
│              │                   │  - Missions          │
│              │                   │  - Billing           │
└──────────────┘                   └──────┬───────────────┘
                                          │
                    ┌─────────────────────┼─────────────────┐
                    ▼                     ▼                 ▼
              ┌──────────┐          ┌──────────┐    ┌──────────┐
              │   Job    │          │   Data   │    │ Storage  │
              │  Queue   │          │ Service  │    │  Layer   │
              └────┬─────┘          └────┬─────┘    │ - Postgres│
                   │                     │          │ - Redis   │
                   ▼                     │          │ - MinIO   │
            ┌──────────────┐            │          └──────────┘
            │ Drift Worker │◄───────────┘
            │ (OpenDrift)  │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │  Results     │
            │  Processor   │
            └──────────────┘
```

---

## 2. Technology Stack

### Core Technologies
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Container Runtime | Docker | 24+ | Containerization |
| Orchestration (Dev) | Docker Compose | 2.20+ | Service orchestration |
| Orchestration (Prod) | Kubernetes | 1.28+ | Production scaling |
| API Services | Go (Golang) | 1.21+ | REST API backend services |
| API Framework | Gin / Fiber | Latest | HTTP web framework |
| Frontend | React + TypeScript | 18+ | Web UI |
| Map Visualization | Leaflet / MapLibre GL | 2.0+ | Interactive mapping |
| Database | PostgreSQL | 16+ | Relational data |
| Cache | Redis | 7+ | Session, rate limiting |
| Object Storage | MinIO | RELEASE.2024+ | S3-compatible storage |
| Message Queue | Redis | 7+ | Job queue |
| Drift Engine | OpenDrift (Python) | 1.11+ | Particle simulation |
| Data Processing | Python | 3.11+ | NetCDF, xarray, geospatial |
| Web Server | Nginx | 1.25+ | Reverse proxy, static files |
| Monitoring | Prometheus + Grafana | Latest | Metrics & dashboards |

### Programming Languages
- **API Services:** Go 1.21+
- **Drift Engine & Data Processing:** Python 3.11+
- **Frontend:** TypeScript
- **Infrastructure:** Bash, Docker, YAML

---

## 3. Component Architecture

### 3.1 Web UI (Frontend)

**Container:** `driftline-frontend`

#### Technology Stack
- React 18 with TypeScript
- Material-UI (MUI) or Ant Design for components
- MapLibre GL JS for interactive mapping
- React Query for data fetching
- Zustand or Redux for state management
- Vite for build tooling

#### Responsibilities
- User authentication flow
- Interactive map interface for position input
- Mission configuration form
- Real-time job status updates (WebSocket)
- Results visualization:
  - Probability heatmaps
  - Search area polygons
  - Particle trajectories
  - Time series animations
- PDF report generation (client-side with jsPDF or server-side)
- User account management

#### Docker Configuration
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### Environment Variables
- `VITE_API_BASE_URL`: API server endpoint
- `VITE_MAP_TILE_URL`: Map tile server
- `VITE_WS_URL`: WebSocket endpoint

---

### 3.2 API Server

**Container:** `driftline-api`

#### Technology Stack
- Go 1.21+ with Gin framework
- GORM for database operations
- go-playground/validator for request validation
- golang-jwt/jwt for authentication
- golang.org/x/crypto/bcrypt for password hashing
- Stripe Go SDK for payment processing
- CORS middleware
- Rate limiting via Redis (go-redis)
- Swagger documentation (swaggo/swag)

#### Responsibilities
**Authentication & User Management:**
- User registration and email verification
- Login and token issuance (JWT)
- Token refresh and revocation
- Password reset flow
- API key generation and management
- Role-based access control (RBAC)
- SSO integration (Google, Microsoft) for enterprise

**Mission Management:**
- Mission CRUD operations
- Input validation (coordinates, time ranges, object types)
- Mission metadata management
- Search and filtering
- Access control enforcement
- Job queue submission
- Audit logging

**Billing & Subscription:**
- Payment processing (Stripe integration)
- Subscription management
- Usage tracking and metering
- Invoice generation
- Credit system for pre-paid plans
- Webhook handling for payment events

**API Features:**
- Request validation
- Rate limiting per API key and IP
- API versioning (e.g., `/v1/missions`)
- WebSocket connections for real-time updates
- Logging and request tracing

#### Key Endpoints
```go
// Missions
POST   /v1/missions              // Create new mission
GET    /v1/missions              // List user missions
GET    /v1/missions/:id          // Get mission details
DELETE /v1/missions/:id          // Delete mission
GET    /v1/missions/:id/status   // Get job status
GET    /v1/missions/:id/results  // Download results

// User Management
POST   /v1/auth/register
POST   /v1/auth/login
POST   /v1/auth/refresh
GET    /v1/users/me
PATCH  /v1/users/me

// Billing
GET    /v1/billing/usage
GET    /v1/billing/invoices
POST   /v1/billing/payment-methods

// WebSocket
WS     /v1/ws/missions/:id       // Real-time updates
```

#### Docker Configuration
```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o api-gateway ./cmd/api-gateway

# Run stage
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/api-gateway .
EXPOSE 8000
CMD ["./api-gateway"]
```

#### Environment Variables
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `JWT_SECRET_KEY`: For token signing
- `JWT_EXPIRATION_MINUTES`: Token expiration (default: 60)
- `STRIPE_API_KEY`: Payment processing
- `STRIPE_WEBHOOK_SECRET`: Webhook verification
- `S3_ENDPOINT`: MinIO endpoint
- `S3_ACCESS_KEY`: S3 credentials
- `S3_SECRET_KEY`: S3 credentials
- `CORS_ORIGINS`: Allowed frontend origins
- `SMTP_HOST`: Email server for notifications
- `SMTP_PORT`: Email server port
- `SMTP_USER`: Email credentials
- `SMTP_PASSWORD`: Email credentials

---

### 3.3 Database Schema

**All schemas consolidated in PostgreSQL**

#### Users & Authentication

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    scopes JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

#### Missions

```sql
CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255),
    description TEXT,
    
    -- Input parameters
    last_known_lat FLOAT NOT NULL,
    last_known_lon FLOAT NOT NULL,
    last_known_time TIMESTAMP NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    uncertainty_radius_m FLOAT,
    forecast_hours INTEGER NOT NULL,
    ensemble_size INTEGER DEFAULT 1000,
    
    -- Configuration
    config JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'created',
    job_id UUID,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_missions_user ON missions(user_id);
CREATE INDEX idx_missions_status ON missions(status);
CREATE INDEX idx_missions_created ON missions(created_at DESC);
```

#### Mission Object Types
Predefined leeway categories from OpenDrift:
- Person in water (PIW)
- Life raft (inflated)
- Small boat (power/sail)
- Fishing vessel
- Container
- Debris field

#### Billing & Subscriptions

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    mission_id UUID REFERENCES missions(id),
    usage_type VARCHAR(50),  -- 'mission', 'urgent_priority', etc.
    quantity INTEGER DEFAULT 1,
    amount_cents INTEGER,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    stripe_invoice_id VARCHAR(255),
    amount_cents INTEGER,
    status VARCHAR(50),
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 3.4 Job Queue

**Technology:** Redis + Go workers

#### Implementation
- Redis as message broker
- Go libraries (asynq or custom implementation) for queue management
- Job priorities: `urgent`, `normal`, `low`

#### Responsibilities

#### Responsibilities
- Enqueue drift simulation jobs
- Priority queue management
- Job scheduling and retry logic
- Worker health monitoring
- Concurrency control
- Dead letter queue for failed jobs

#### Job Structure
```json
{
  "job_id": "uuid",
  "mission_id": "uuid",
  "priority": "urgent",
  "input": {
    "lat": 64.5,
    "lon": -18.2,
    "time": "2025-12-30T14:30:00Z",
    "object_type": "PIW",
    "uncertainty_radius": 5000,
    "forecast_hours": 48,
    "ensemble_size": 1000
  },
  "forcing_data": {
    "ocean_currents": "s3://driftline-data/cmems/...",
    "wind": "s3://driftline-data/gfs/...",
    "waves": "s3://driftline-data/ww3/..."
  },
  "created_at": "2025-12-30T14:35:00Z",
  "ttl": 3600
}
```

---

### 3.5 Drift Worker (OpenDrift Engine)

**Container:** `driftline-drift-worker`

#### Technology Stack
- Python 3.11
- OpenDrift 1.11+
- NumPy, SciPy for numerical operations
- xarray, netCDF4 for data handling
- Matplotlib for visualization (optional)

#### Responsibilities
- Execute Lagrangian particle simulations
- Load environmental forcing data
- Apply leeway coefficients
- Generate particle trajectories
- Calculate uncertainty envelopes
- Export results to standardized formats

#### Docker Configuration
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libproj-dev \
    libgeos-dev \
    libnetcdf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir opendrift numpy xarray
COPY . .
CMD ["python", "worker.py"]
```

#### Simulation Workflow
1. Receive job from queue
2. Download forcing data from object storage
3. Initialize OpenDrift Leeway model
4. Seed particles at last known position with uncertainty
5. Run forward simulation
6. Export outputs:
   - NetCDF: Full particle trajectories
   - GeoJSON: Trajectories, centroids, search areas
   - PNG: Probability heatmap
7. Upload results to object storage
8. Update mission status in database
9. Emit completion event

#### Environment Variables
- `REDIS_URL`: Job queue connection
- `S3_ENDPOINT`: MinIO endpoint
- `S3_ACCESS_KEY`: S3 credentials
- `S3_SECRET_KEY`: S3 credentials
- `DATABASE_URL`: For status updates
- `MAX_CONCURRENT_JOBS`: Worker concurrency

#### Scaling Strategy
- Horizontal scaling: Deploy multiple worker containers
- CPU-bound workload: Provision 2-4 vCPU per worker
- Memory: 4-8 GB per worker depending on ensemble size

---

### 3.6 Data Service

**Container:** `driftline-data-service`

#### Technology Stack
- Go 1.21+ with Gin framework for API layer
- Python worker processes for NetCDF processing (xarray)
- THREDDS integration or custom subsetting logic

#### Responsibilities
- Fetch and cache environmental forcing data
- Spatial and temporal subsetting
- Format conversion (NetCDF → Zarr)
- Data quality checks
- Metadata management

#### Data Sources Integration
```python
# Example sources configuration
data_sources = {
    "ocean_currents": {
        "provider": "copernicus_marine",
        "dataset": "GLOBAL_ANALYSISFORECAST_PHY_001_024",
        "variables": ["uo", "vo"],  # eastward, northward velocity
        "resolution": "1/12 degree",
        "update_frequency": "daily"
    },
    "wind": {
        "provider": "noaa_gfs",
        "url": "https://nomads.ncep.noaa.gov/dods/gfs_0p25",
        "variables": ["ugrd10m", "vgrd10m"],
        "resolution": "0.25 degree",
        "update_frequency": "6 hours"
    },
    "waves": {
        "provider": "noaa_wavewatch3",
        "url": "https://nomads.ncep.noaa.gov/dods/wave/gfswave",
        "variables": ["dirpwsfc", "perpwsfc"],
        "resolution": "0.5 degree",
        "update_frequency": "6 hours"
    }
}
```

#### Caching Strategy
- Geographic grid partitioning (10° × 10° tiles)
- Time window: Rolling 7-day forecast + 3-day hindcast
- Storage: MinIO buckets organized by date and region
- Cache invalidation: Based on data timestamp

---

### 3.7 Results Processor

**Container:** `driftline-results-processor`

#### Technology Stack
- Python 3.11
- Shapely for geometric operations
- Rasterio for grid processing
- ReportLab or WeasyPrint for PDF generation

#### Responsibilities
- Parse OpenDrift NetCDF outputs
- Calculate derived products:
  - Probability density grids (50%, 90%, 95% contours)
  - Search area polygons
  - Most likely position (centroid)
  - Time-to-coast estimates
- Generate visualization assets:
  - Heatmap overlays (GeoTIFF, PNG)
  - Trajectory animations
- Create PDF SAR reports
- Store results in database and object storage

#### Output Structure
```
s3://driftline-results/{mission_id}/
├── raw/
│   └── particles.nc           # Full OpenDrift output
├── processed/
│   ├── trajectories.geojson   # All particle paths
│   ├── search_area_50.geojson # 50% probability polygon
│   ├── search_area_90.geojson # 90% probability polygon
│   ├── centroid.geojson       # Most likely position
│   └── probability.tif        # Raster heatmap
├── visualizations/
│   ├── heatmap.png
│   ├── trajectories.png
│   └── animation.mp4          # Optional
└── report.pdf                 # SAR briefing document
```

#### Database Schema
```sql
CREATE TABLE mission_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES missions(id),
    
    -- Computed positions
    centroid_lat FLOAT,
    centroid_lon FLOAT,
    centroid_time TIMESTAMP,
    
    -- Search areas (stored as GeoJSON)
    search_area_50_geom JSONB,
    search_area_90_geom JSONB,
    
    -- File paths
    netcdf_path VARCHAR(500),
    geojson_path VARCHAR(500),
    pdf_report_path VARCHAR(500),
    
    -- Metadata
    particle_count INTEGER,
    stranded_count INTEGER,
    computation_time_seconds FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 3.8 Storage Layer

#### 3.8.1 PostgreSQL Database

**Container:** `driftline-postgres`

#### Configuration
- Version: PostgreSQL 16
- Extensions: PostGIS, uuid-ossp
- Connection pooling: PgBouncer (optional)

#### Docker Configuration
```dockerfile
FROM postgres:16
ENV POSTGRES_DB=driftline
ENV POSTGRES_USER=driftline_user
ENV POSTGRES_PASSWORD=changeme
COPY init-scripts/ /docker-entrypoint-initdb.d/
```

#### Volume Mapping
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

#### Backup Strategy
- Daily full backups via pg_dump
- Point-in-time recovery (WAL archiving)
- Retention: 30 days

---

#### 3.8.2 Redis Cache

**Container:** `driftline-redis`

#### Use Cases
- Session storage
- Rate limiting counters
- Job queue (BullMQ backend)
- Caching API responses
- WebSocket pub/sub

#### Docker Configuration
```dockerfile
FROM redis:7-alpine
COPY redis.conf /usr/local/etc/redis/redis.conf
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
```

#### Configuration
```conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
appendonly yes
```

---

#### 3.8.3 MinIO Object Storage

**Container:** `driftline-minio`

#### Purpose
- S3-compatible object storage
- Store forcing data (NetCDF files)
- Store mission results
- Serve static assets

#### Bucket Structure
```
driftline-data/           # Environmental forcing data
  ├── ocean_currents/
  ├── wind/
  └── waves/

driftline-results/        # Mission outputs
  ├── {mission_id}/

driftline-reports/        # PDF reports
  └── {mission_id}.pdf
```

#### Docker Configuration
```yaml
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: changeme123
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
```

---

### 3.9 Nginx Reverse Proxy

**Container:** `driftline-nginx`

#### Responsibilities
- SSL/TLS termination
- Reverse proxy to frontend and API server
- Load balancing across multiple API instances
- Static file serving
- Rate limiting
- Compression (gzip, brotli)

#### Configuration
```nginx
upstream api_backend {
    # Can add multiple API instances for load balancing
    server driftline-api:8000;
    # server driftline-api-2:8000;
    # server driftline-api-3:8000;
}

upstream frontend {
    server driftline-frontend:80;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;
    
    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # API
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

### 3.10 Monitoring Stack

#### 3.10.1 Prometheus

**Container:** `driftline-prometheus`

#### Metrics Collection
- API request rates and latencies
- Mission creation and completion rates
- Job queue depth
- Worker utilization
- Database connection pool metrics
- Redis cache hit rates
- Storage usage

#### Configuration
```yaml
scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['driftline-api:8000']
  
  - job_name: 'drift-workers'
    static_configs:
      - targets: ['driftline-drift-worker:9090']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

---

#### 3.10.2 Grafana

**Container:** `driftline-grafana`

#### Dashboards
1. **System Overview**
   - Active missions
   - Queue depth
   - API latency (p50, p95, p99)
   - Error rates

2. **Mission Analytics**
   - Missions by object type
   - Average computation time
   - Geographic distribution

3. **Infrastructure**
   - CPU/Memory usage
   - Database queries per second
   - Storage capacity

4. **Billing & Usage**
   - Revenue metrics
   - User acquisition
   - Plan distribution

---

## 4. Docker Compose Configuration

### 4.1 Development Environment

**File:** `docker-compose.dev.yml`

```yaml
version: '3.9'

services:
  # Storage Layer
  postgres:
    image: postgres:16
    container_name: driftline-postgres
    environment:
      POSTGRES_DB: driftline
      POSTGRES_USER: driftline_user
      POSTGRES_PASSWORD: dev_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U driftline_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: driftline-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: driftline-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # Backend Services
  api:
    build:
      context: ./services/api
      dockerfile: Dockerfile
    container_name: driftline-api
    environment:
      DATABASE_URL: postgresql://driftline_user:dev_password@postgres:5432/driftline
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: dev_secret_key_change_in_production
      JWT_EXPIRATION_MINUTES: 60
      STRIPE_API_KEY: sk_test_...
      STRIPE_WEBHOOK_SECRET: whsec_...
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      CORS_ORIGINS: http://localhost:3000
      SMTP_HOST: smtp.example.com
      SMTP_PORT: 587
      SMTP_USER: notifications@driftline.io
      SMTP_PASSWORD: changeme
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    volumes:
      - ./services/api:/app

  data-service:
    build:
      context: ./services/data-service
      dockerfile: Dockerfile
    container_name: driftline-data-service
    environment:
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      REDIS_URL: redis://redis:6379/1
    depends_on:
      - minio
      - redis
    ports:
      - "8003:8000"
    volumes:
      - ./data_cache:/app/cache

  # Job Processing
  drift-worker:
    build:
      context: ./services/drift-worker
      dockerfile: Dockerfile
    container_name: driftline-drift-worker
    environment:
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: postgresql://driftline_user:dev_password@postgres:5432/driftline
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      MAX_CONCURRENT_JOBS: 2
      LOG_LEVEL: DEBUG
    depends_on:
      - redis
      - postgres
      - minio
      - data-service
    volumes:
      - ./services/drift-worker:/app
    deploy:
      replicas: 2

  results-processor:
    build:
      context: ./services/results-processor
      dockerfile: Dockerfile
    container_name: driftline-results-processor
    environment:
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: postgresql://driftline_user:dev_password@postgres:5432/driftline
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
    depends_on:
      - redis
      - postgres
      - minio

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: driftline-frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api
      VITE_WS_URL: ws://localhost:8000/ws
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  # Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: driftline-nginx
    volumes:
      - ./nginx/nginx.dev.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - frontend
      - api-gateway

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: driftline-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    container_name: driftline-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_SERVER_ROOT_URL: http://localhost:3001
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: driftline-network
```

---

### 4.2 Production Environment

**File:** `docker-compose.prod.yml`

Key differences from development:
- Environment variables from `.env` file or secrets manager
- No volume mounts for code (use built images)
- Health checks and restart policies
- Resource limits
- Read-only root filesystems
- External secrets management
- SSL/TLS certificates via Let's Encrypt
- Multiple worker replicas
- Database connection pooling
- Logging drivers

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  drift-worker:
    image: driftline/drift-worker:${VERSION}
    restart: always
    environment:
      REDIS_URL: ${REDIS_URL}
      DATABASE_URL: ${DATABASE_URL}
      S3_ENDPOINT: ${S3_ENDPOINT}
      S3_ACCESS_KEY: ${S3_ACCESS_KEY}
      S3_SECRET_KEY: ${S3_SECRET_KEY}
      MAX_CONCURRENT_JOBS: 4
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '4'
          memory: 8G
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ... other services with production configurations
```

---

## 5. Data Flow

### 5.1 Mission Creation Flow

```
User → Frontend → API Server → Database + Job Queue (Redis)
                      ↓
                 Drift Worker
```

**Step-by-Step:**
1. User fills form on web UI (position, time, object type)
2. Frontend validates inputs and sends POST request
3. API Server authenticates request (JWT token)
4. API Server validates and stores mission in PostgreSQL
5. API Server enqueues job in Redis
6. Returns mission ID to user
7. Frontend polls for status or subscribes to WebSocket

---

### 5.2 Drift Simulation Flow

```
Drift Worker → Job Queue → Data Service → MinIO
              ↓                          ↑
         OpenDrift Engine                |
              ↓                          |
         Results Processor ──────────────┘
              ↓
         Database + MinIO
              ↓
         API Server → Frontend
```

**Step-by-Step:**
1. Drift Worker pulls job from Redis queue
2. Worker requests forcing data from Data Service
3. Data Service fetches from cache (MinIO) or downloads
4. Worker initializes OpenDrift with mission parameters
5. Runs simulation (5-60 seconds depending on ensemble size)
6. Exports NetCDF and metadata
7. Results Processor creates derived products
8. Uploads all outputs to MinIO
9. Updates mission status to "completed" in database
10. Emits WebSocket event to frontend
11. User downloads results

---

### 5.3 Authentication Flow

```
User → Frontend → API Server → Database
         ↑              ↓
         └── JWT Token ─┘
```

**Login:**
1. User submits email + password
2. API Server verifies credentials
3. Generates JWT token (access + refresh)
4. Returns tokens to frontend
5. Frontend stores in memory/localStorage
6. Subsequent requests include Authorization header

**API Key:**
1. User generates API key in account settings
2. API Server creates key and stores hash
3. Returns key once (user must save)
4. API requests use `X-API-Key` header
5. API Server validates against hashed keys in database

---

## 6. Scaling Strategy

### 6.1 Horizontal Scaling

**Components to Scale:**
| Component | Strategy | Trigger |
|-----------|----------|---------|
| Drift Workers | Increase replicas | Queue depth > 10 |
| API Server | Load balancer | CPU > 70% |
| Data Service | Replicas | Cache miss rate > 30% |
| Results Processor | Replicas | Queue depth > 5 |

### 6.2 Vertical Scaling

**Database:**
- PostgreSQL: Scale to larger instance (16+ vCPU, 64 GB RAM)
- Consider read replicas for reporting queries

**Redis:**
- Single instance sufficient for development
- Redis Cluster for production (3-6 nodes)

**MinIO:**
- Distributed mode with erasure coding
- Multiple nodes for redundancy

---

## 7. Deployment Workflow

### 7.1 Local Development

```bash
# Clone repository
git clone https://github.com/org/driftline.git
cd driftline

# Set up environment
cp .env.example .env
# Edit .env with local configuration

# Build and start services
docker-compose -f docker-compose.dev.yml up --build

# Run database migrations
docker-compose exec api-gateway alembic upgrade head

# Create test user
docker-compose exec api-gateway python scripts/create_test_user.py

# Access application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
# Grafana: http://localhost:3001
```

### 7.2 Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Tag and push to registry
docker tag driftline/api:latest registry.example.com/driftline/api:v1.0.0
docker push registry.example.com/driftline/api:v1.0.0

# Deploy to production server
ssh production-server
cd /opt/driftline
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify services
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### 7.3 CI/CD Pipeline

**GitHub Actions / GitLab CI:**
```yaml
stages:
  - test
  - build
  - deploy

test:
  script:
    - docker-compose -f docker-compose.test.yml up --abort-on-container-exit
    - pytest services/*/tests

build:
  script:
    - docker build -t $CI_REGISTRY_IMAGE/api:$CI_COMMIT_TAG ./services/api
    - docker push $CI_REGISTRY_IMAGE/api:$CI_COMMIT_TAG

deploy-production:
  stage: deploy
  script:
    - ssh production "cd /opt/driftline && docker-compose pull && docker-compose up -d"
  only:
    - tags
```

---

## 8. Security Considerations

### 8.1 Network Security
- All services communicate within internal Docker network
- Only Nginx exposed to public internet
- API rate limiting per IP and per user
- DDoS protection via Cloudflare (optional)

### 8.2 Data Security
- Encryption at rest: MinIO with KMS integration
- Encryption in transit: TLS 1.3 for all external connections
- Secrets management: Docker secrets or HashiCorp Vault
- Database encryption: PostgreSQL SSL connections

### 8.3 Application Security
- Input validation with Go struct tags and validator
- SQL injection prevention via ORM (GORM) and parameterized queries
- CORS configuration restricted to known origins
- Content Security Policy headers
- JWT token expiration (1 hour access, 7 days refresh)
- API key rotation support

### 8.4 Container Security
- Non-root users in containers
- Read-only root filesystems where possible
- Minimal base images (Alpine, Distroless)
- Regular security scanning (Trivy, Snyk)
- Image signing with Docker Content Trust

---

## 9. Disaster Recovery

### 9.1 Backup Strategy

**PostgreSQL:**
- Automated daily backups via pg_dump
- Retention: 30 days
- Offsite backup to S3 Glacier

**MinIO:**
- Bucket replication to secondary region
- Versioning enabled
- Lifecycle policies for data retention

**Redis:**
- RDB snapshots every 6 hours
- AOF for durability
- Quick restore from snapshots

### 9.2 Recovery Procedures

**Database Failure:**
```bash
# Restore from latest backup
docker exec -i driftline-postgres psql -U driftline_user -d driftline < backup.sql
```

**Service Failure:**
```bash
# Restart failed service
docker-compose -f docker-compose.prod.yml restart <service-name>

# Full restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 10. Performance Optimization

### 10.1 Database Optimization
- Indexes on frequently queried columns
- Connection pooling (max 20 connections per service)
- Query optimization with EXPLAIN ANALYZE
- Partitioning for mission history (by month)

### 10.2 Caching Strategy
- Redis for API response caching (TTL: 60 seconds)
- Browser caching for static assets (max-age: 1 year)
- MinIO CDN integration for results delivery
- Data Service pre-warming cache during off-peak hours

### 10.3 API Optimization
- Response pagination (default: 50 items)
- Field filtering (sparse fieldsets)
- Compression (gzip, brotli)
- HTTP/2 push for critical resources

---

## 11. Monitoring and Alerting

### 11.1 Key Metrics

**Application Metrics:**
- Missions created per hour
- Average simulation time
- Job queue length
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)

**Infrastructure Metrics:**
- CPU, memory, disk usage per container
- Database query latency
- Redis cache hit rate
- Network throughput

### 11.2 Alerting Rules

```yaml
alerts:
  - alert: HighJobQueueDepth
    expr: job_queue_depth > 50
    for: 5m
    annotations:
      summary: "Job queue depth is high"
    
  - alert: HighAPILatency
    expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
    for: 5m
    
  - alert: WorkerDown
    expr: up{job="drift-worker"} == 0
    for: 2m
```

### 11.3 Logging

**Structured Logging (JSON):**
```json
{
  "timestamp": "2025-12-30T14:35:22Z",
  "level": "INFO",
  "service": "drift-worker",
  "mission_id": "abc-123",
  "message": "Simulation completed",
  "duration_seconds": 45.2,
  "particle_count": 1000
}
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Or Grafana Loki for lightweight alternative
- Retention: 30 days

---

## 12. Cost Estimation

### 12.1 Infrastructure Costs (Monthly)

**Development Environment:**
- Single cloud VM (4 vCPU, 16 GB RAM): $80
- Object storage (100 GB): $2
- Total: ~$100/month

**Production Environment (Small):**
- Load balancer: $20
- Application servers (2 × 8 vCPU, 32 GB): $320
- Database (4 vCPU, 16 GB): $160
- Redis (2 GB): $20
- Object storage (1 TB): $23
- Bandwidth (500 GB): $45
- Total: ~$600/month

**Production Environment (Medium):**
- Load balancer: $20
- Application servers (4 × 8 vCPU, 32 GB): $640
- Worker nodes (4 × 4 vCPU, 16 GB): $320
- Database (8 vCPU, 64 GB): $480
- Redis cluster (3 nodes): $120
- Object storage (5 TB): $115
- CDN/bandwidth: $200
- Total: ~$2,000/month

---

## 13. Development Roadmap

### Phase 1: MVP (Months 1-3)
- Core services (API Gateway, Auth, Mission, Drift Worker)
- Basic web UI (mission creation, results viewing)
- PostgreSQL + Redis + MinIO setup
- Single region deployment
- Manual deployment

### Phase 2: Beta (Months 4-6)
- Billing integration (Stripe)
- Results Processor with PDF reports
- Real-time WebSocket updates
- Data Service with caching
- Monitoring stack (Prometheus + Grafana)
- CI/CD pipeline

### Phase 3: Production Launch (Months 7-9)
- Multi-region support
- Advanced visualization (animations)
- Mobile-responsive UI
- API rate limiting and quotas
- Documentation and tutorials
- Customer support system

### Phase 4: Scale & Enhance (Months 10-12)
- Kubernetes migration
- Auto-scaling policies
- Advanced analytics dashboard
- Machine learning drift corrections
- AIS data integration
- Enterprise SSO

---

## 14. Summary

This architecture provides a robust, scalable foundation for **Driftline**, the global SAR drift forecasting SaaS platform:

**Key Strengths:**
- ✅ Simplified architecture with single unified API server
- ✅ Go for high-performance API with excellent concurrency
- ✅ Docker containers ensure consistency across environments
- ✅ Clean separation between API, compute, and data processing
- ✅ Horizontally scalable drift workers
- ✅ Object storage for cost-effective data management
- ✅ Comprehensive monitoring and observability
- ✅ Straightforward development to production path
- ✅ Fewer moving parts = easier to maintain and debug

**Technology Choices Rationale:**
- **Go:** High performance, excellent concurrency, fast compilation, strong typing
- **Gin Framework:** Lightweight, fast, great middleware ecosystem
- **PostgreSQL:** Reliable, mature, excellent geospatial support
- **Redis:** Fast, versatile (cache + queue + pub/sub)
- **MinIO:** S3-compatible, self-hosted, no vendor lock-in
- **OpenDrift:** Proven SAR modeling, open source, actively maintained
- **Docker Compose:** Simple orchestration for dev and small prod deployments

**Architecture Benefits:**
- Single API server reduces operational complexity
- No inter-service communication overhead
- Easier to reason about and debug
- Simpler deployment pipeline
- Lower infrastructure costs
- Still scalable via horizontal replication of API server and workers

**Next Steps:**
1. Set up development environment
2. Implement unified API server (auth, missions, billing)
3. Integrate OpenDrift worker
4. Build minimal web UI
5. Deploy to staging environment
6. Beta testing with select users
7. Production launch

This design balances simplicity for initial development with the flexibility to scale as Driftline grows from initial launch to enterprise-scale operations.
