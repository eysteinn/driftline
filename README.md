# Driftline – Global SAR Drift Forecasting SaaS Platform

![Driftline Logo](https://via.placeholder.com/150x50?text=Driftline)

**Driftline** is a global, self-serve Search and Rescue (SAR) drift forecasting SaaS platform that provides web-based and API-driven probabilistic drift forecasts using environmental forcing data and OpenDrift Lagrangian particle modeling.

## 🌊 Overview

Driftline answers the critical question:

> *"Given the last known position and time of an abandoned vessel or person, where is the most likely position now, and where should search resources be deployed?"*

## 🏗️ Architecture

The platform is built with a modern microservices architecture:

- **Frontend**: React + TypeScript with MapLibre GL for interactive mapping
- **API Server**: Go (Gin framework) for authentication, missions, and billing
- **Drift Worker**: Python + OpenDrift for Lagrangian particle simulations
- **Data Service**: Go for managing environmental forcing data
- **Results Processor**: Python for generating derived products and reports
- **Infrastructure**: Docker + Docker Compose, PostgreSQL, Redis, MinIO

## 📋 Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Go 1.21+ (for local development)
- Node.js 20+ (for frontend development)
- Python 3.11+ (for worker development)
- 8GB+ RAM recommended
- 20GB+ disk space

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/eysteinn/driftline.git
cd driftline
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Development Environment

**Option A: Using Quick Start Script (Recommended)**

```bash
./quick-start.sh
```

The script will:
- Check Docker installation
- Create `.env` file if needed
- Start all services
- Initialize the database schema automatically

**Option B: Manual Start**

```bash
docker compose -f docker-compose.dev.yml up --build -d

# Wait for database to be ready
sleep 5

# Initialize database schema (if not already done)
docker exec -i driftline-postgres psql -U driftline_user -d driftline < sql/init/01_schema.sql
```

This will start all services:

- **Frontend**: http://localhost:3000
- **API Server**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

### 4. Verify Setup

Check that all services are running:

```bash
docker compose -f docker-compose.dev.yml ps
```

View logs:

```bash
docker compose -f docker-compose.dev.yml logs -f
```

### 5. Access the Application

Open your browser and navigate to:
- **Web UI**: http://localhost:3000
- **API Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs (when implemented)

## 📁 Project Structure

```
driftline/
├── frontend/                  # React + TypeScript frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client
│   │   ├── stores/          # State management (Zustand)
│   │   └── types/           # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── services/
│   ├── api/                 # Go API server
│   │   ├── cmd/
│   │   │   └── api-gateway/ # Main entry point
│   │   ├── internal/
│   │   │   ├── auth/        # Authentication logic
│   │   │   ├── missions/    # Mission management
│   │   │   ├── billing/     # Billing and subscriptions
│   │   │   └── database/    # Database layer
│   │   ├── pkg/
│   │   │   └── models/      # Data models
│   │   ├── Dockerfile
│   │   └── go.mod
│   ├── drift-worker/        # Python + OpenDrift worker
│   │   ├── worker.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── data-service/        # Go data service
│   │   ├── cmd/
│   │   ├── internal/
│   │   ├── Dockerfile
│   │   └── go.mod
│   └── results-processor/   # Python results processor
│       ├── processor.py
│       ├── requirements.txt
│       └── Dockerfile
├── sql/
│   └── init/                # Database initialization scripts
│       └── 01_schema.sql
├── nginx/                   # Nginx configurations
│   ├── nginx.dev.conf
│   └── nginx.prod.conf
├── docker-compose.dev.yml   # Development environment
├── docker-compose.prod.yml  # Production environment
├── .env.example            # Environment variables template
├── .gitignore
└── README.md
```

## 🛠️ Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### API Server Development

```bash
cd services/api
go mod download
go run cmd/api-gateway/main.go
```

### Worker Development

```bash
cd services/drift-worker
pip install -r requirements.txt
python worker.py
```

## 🧪 Testing

### Run Frontend Tests

```bash
cd frontend
npm test
```

### Run API Tests

```bash
cd services/api
go test ./...
```

### Run Python Tests

```bash
cd services/drift-worker
pytest
```

## 📦 Building for Production

### Build All Images

```bash
docker-compose -f docker-compose.prod.yml build
```

### Deploy to Production

```bash
# Set production environment variables in .env
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `S3_ENDPOINT`: MinIO/S3 endpoint
- `STRIPE_API_KEY`: Stripe API key for billing (optional)

### Database Migrations

Database schema is managed via SQL scripts in `sql/init/`. For schema changes:

1. Add new migration scripts with sequential numbering
2. Restart the database service to apply changes

## 🔒 Security

- All passwords should be changed from defaults in production
- Use strong, randomly generated secrets for `JWT_SECRET_KEY`
- Enable SSL/TLS in production (configure certificates in nginx)
- Implement rate limiting (configured in nginx)
- Regularly update dependencies

## 📚 API Documentation

API endpoints are organized under `/v1/`:

### Authentication
- `POST /v1/auth/register` - Register new user
- `POST /v1/auth/login` - Login and get JWT token
- `POST /v1/auth/refresh` - Refresh access token

### Missions
- `POST /v1/missions` - Create new mission
- `GET /v1/missions` - List user missions
- `GET /v1/missions/:id` - Get mission details
- `DELETE /v1/missions/:id` - Delete mission
- `GET /v1/missions/:id/status` - Get job status
- `GET /v1/missions/:id/results` - Download results

### User Management
- `GET /v1/users/me` - Get current user
- `PATCH /v1/users/me` - Update user profile

### Billing
- `GET /v1/billing/usage` - Get usage statistics
- `GET /v1/billing/invoices` - List invoices

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## � Troubleshooting

### Database Not Initialized

If you get database errors about missing tables:

```bash
# Manually initialize the database
docker exec -i driftline-postgres psql -U driftline_user -d driftline < sql/init/01_schema.sql
```

### Reset Everything

To start fresh with clean volumes:

```bash
docker compose -f docker-compose.dev.yml down -v
./quick-start.sh
```

### API Connection Refused

Check if the API service is running:

```bash
docker compose -f docker-compose.dev.yml ps api
docker compose -f docker-compose.dev.yml logs api
```

### Port Already in Use

If you get port conflicts:

```bash
# Stop any conflicting services
docker compose -f docker-compose.dev.yml down

# Or change ports in docker-compose.dev.yml
```

### View Service Logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f frontend
docker compose -f docker-compose.dev.yml logs -f drift-worker
```

## �📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support, email support@driftline.io or open an issue in the repository.

## 🗺️ Roadmap

### Phase 1: MVP (Current)
- ✅ Core services setup
- ⏳ Basic web UI
- ⏳ OpenDrift integration
- ⏳ Mission management
- ⏳ Results visualization

### Phase 2: Beta
- ⏳ Billing integration (Stripe)
- ⏳ PDF report generation
- ⏳ Real-time WebSocket updates
- ⏳ Data caching service
- ⏳ Monitoring and alerting

### Phase 3: Production
- ⏳ Multi-region deployment
- ⏳ Advanced visualizations
- ⏳ Mobile-responsive UI
- ⏳ API rate limiting
- ⏳ Documentation portal

### Phase 4: Scale
- ⏳ Kubernetes migration
- ⏳ Auto-scaling
- ⏳ Machine learning enhancements
- ⏳ AIS data integration
- ⏳ Enterprise SSO

## 🙏 Acknowledgments

- OpenDrift - Open source Lagrangian particle tracking framework
- Copernicus Marine Service - Ocean data
- NOAA - Weather and wave data
- All open source contributors

---

**Built with ❤️ for Search and Rescue operations worldwide**
