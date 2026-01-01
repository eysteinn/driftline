#!/bin/bash
# Driftline Quick Start Script

set -e

echo "==================================="
echo "Driftline - Quick Start Setup"
echo "==================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  Please edit .env file and update the configuration values!"
    echo "   Especially change all passwords and secrets before production use."
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Ask user if they want to start the services
read -p "Do you want to start the development environment now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting Driftline services..."
    echo ""
    
    docker compose -f docker-compose.dev.yml up --build -d
    
    echo ""
    echo "⏳ Waiting for database to be ready..."
    sleep 5
    
    # Check if database tables exist
    TABLE_COUNT=$(docker exec driftline-postgres psql -U driftline_user -d driftline -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs || echo "0")
    
    if [ "$TABLE_COUNT" -eq "0" ]; then
        echo "📊 Initializing database schema..."
        docker exec -i driftline-postgres psql -U driftline_user -d driftline < sql/init/01_schema.sql
        echo "✅ Database schema initialized!"
    else
        echo "✅ Database schema already exists ($TABLE_COUNT tables found)"
    fi
    
    echo ""
    echo "✅ Services are running!"
    echo ""
    echo "📊 Service URLs:"
    echo "   - Frontend:        http://localhost:3000"
    echo "   - API Server:      http://localhost:8000"
    echo "   - API Docs:        http://localhost:8000/health"
    echo "   - MinIO Console:   http://localhost:9001 (minioadmin/minioadmin)"
    echo ""
    echo "📝 To view logs:"
    echo "   docker compose -f docker-compose.dev.yml logs -f"
    echo ""
    echo "🛑 To stop services:"
    echo "   docker compose -f docker-compose.dev.yml down"
    echo ""
    echo "🗑️  To reset database and volumes:"
    echo "   docker compose -f docker-compose.dev.yml down -v"
    echo ""
else
    echo ""
    echo "👍 Setup complete! You can start the services later with:"
    echo "   docker compose -f docker-compose.dev.yml up --build"
    echo ""
fi
