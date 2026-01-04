# Makefile for Driftline

.PHONY: help dev prod stop clean build test lint logs status

help: ## Show this help message
	@echo "Driftline - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment
	docker-compose -f docker-compose.dev.yml up --build

dev-detached: ## Start development environment in background
	docker-compose -f docker-compose.dev.yml up --build -d

prod: ## Start production environment
	docker-compose -f docker-compose.prod.yml up -d

stop: ## Stop all services
	docker-compose -f docker-compose.dev.yml down
	docker-compose -f docker-compose.prod.yml down

clean: ## Clean up containers, volumes, and images
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose -f docker-compose.prod.yml down -v

build: ## Build all services
	docker-compose -f docker-compose.dev.yml build

rebuild: ## Rebuild all services from scratch
	docker-compose -f docker-compose.dev.yml build --no-cache

logs: ## Show logs from all services
	docker-compose -f docker-compose.dev.yml logs -f

logs-api: ## Show API server logs
	docker-compose -f docker-compose.dev.yml logs -f api

logs-data-service: ## Show data service logs
	docker-compose -f docker-compose.dev.yml logs -f data-service

logs-worker: ## Show drift worker logs
	docker-compose -f docker-compose.dev.yml logs -f drift-worker

logs-frontend: ## Show frontend logs
	docker-compose -f docker-compose.dev.yml logs -f frontend

status: ## Show status of all services
	docker-compose -f docker-compose.dev.yml ps

restart: ## Restart all services
	docker-compose -f docker-compose.dev.yml restart

restart-api: ## Restart API server
	docker-compose -f docker-compose.dev.yml restart api

restart-data-service: ## Restart data service
	docker-compose -f docker-compose.dev.yml restart data-service

restart-worker: ## Restart drift worker
	docker-compose -f docker-compose.dev.yml restart drift-worker

test: ## Run all tests
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "Running API tests..."
	cd services/api && go test ./...
	@echo "Running worker tests..."
	cd services/drift-worker && pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

test-api: ## Run API tests
	cd services/api && go test ./...

test-worker: ## Run worker tests
	cd services/drift-worker && pytest

test-data-service: ## Run data service tests
	cd services/data-service && pytest tests/

lint: ## Run linters
	@echo "Linting Go code..."
	cd services/api && go vet ./...
	@echo "Linting Python code..."
	cd services/data-service && python -m flake8 app/ --max-line-length=100 --ignore=E501,W503 || true
	cd services/drift-worker && python -m flake8 . --max-line-length=100 --ignore=E501,W503 || true
	@echo "Linting TypeScript code..."
	cd frontend && npm run lint

db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@./migrate.sh

db-init: ## Initialize database schema (for fresh databases only)
	docker-compose -f docker-compose.dev.yml exec postgres psql -U driftline_user -d driftline -f /docker-entrypoint-initdb.d/01_schema.sql

db-shell: ## Open PostgreSQL shell
	docker-compose -f docker-compose.dev.yml exec postgres psql -U driftline_user -d driftline

redis-cli: ## Open Redis CLI
	docker-compose -f docker-compose.dev.yml exec redis redis-cli

minio-shell: ## Open MinIO shell
	@echo "MinIO Console: http://localhost:9001"
	@echo "User: minioadmin"
	@echo "Password: minioadmin"

install-deps: ## Install all dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing Go dependencies..."
	cd services/api && go mod download
	@echo "Installing Python dependencies..."
	cd services/drift-worker && pip install -r requirements.txt
	cd services/results-processor && pip install -r requirements.txt
	cd services/data-service && pip install -r requirements.txt

setup: install-deps ## Initial setup
	@echo "Creating .env file..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Setup complete! Edit .env file and run 'make dev' to start."
