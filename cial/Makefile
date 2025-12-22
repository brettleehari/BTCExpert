# CIAL Makefile
# Common commands for development and deployment

.PHONY: help start start-dev start-monitoring stop restart build logs test clean install setup

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

##@ General

help: ## Display this help message
	@echo "$(BLUE)CIAL - Crypto Intelligence Abstraction Layer$(NC)"
	@echo "$(BLUE)Available commands:$(NC)\n"
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install Python dependencies (local development)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

setup: ## Initial project setup (create venv, install deps)
	@echo "$(BLUE)Setting up CIAL development environment...$(NC)"
	python3.11 -m venv venv
	@echo "$(YELLOW)Activate venv with: source venv/bin/activate$(NC)"
	@echo "$(YELLOW)Then run: make install$(NC)"

setup-pre-commit: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pip install pre-commit
	cd .. && export HOME=/tmp && pre-commit install
	@echo "$(GREEN)✅ Pre-commit hooks installed$(NC)"

##@ Code Quality

format: ## Format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ Code formatted$(NC)"

lint: ## Run linting checks (ruff)
	@echo "$(BLUE)Running linting checks...$(NC)"
	cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ Linting passed$(NC)"

lint-fix: ## Run linting checks and auto-fix issues
	@echo "$(BLUE)Running linting with auto-fix...$(NC)"
	cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ Linting issues fixed$(NC)"

security: ## Run security checks (bandit + safety)
	@echo "$(BLUE)Running security checks...$(NC)"
	cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ Security scan complete$(NC)"

check-all: ## Run all code quality checks
	@cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ All quality checks passed$(NC)"

pre-commit-run: ## Run pre-commit hooks manually on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	cd .. && ./scripts/lint-and-fix.sh
	@echo "$(GREEN)✅ Pre-commit checks complete$(NC)"

##@ Docker Operations

start: ## Start CIAL in production mode
	@./start.sh production

start-dev: ## Start CIAL in development mode (hot-reload)
	@./start.sh development

start-monitoring: ## Start CIAL with monitoring (Prometheus + Grafana)
	@./start.sh production monitoring

start-timescale: ## Start CIAL with TimescaleDB
	@./start.sh production timescale

start-all: ## Start CIAL with all optional services
	@docker-compose --profile monitoring --profile timescale up -d

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	@docker-compose down
	@docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	@echo "$(GREEN)✅ Services stopped$(NC)"

restart: stop start ## Restart all services

restart-dev: stop start-dev ## Restart in development mode

##@ Building

build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker-compose build
	@echo "$(GREEN)✅ Build complete$(NC)"

build-dev: ## Build development Docker image
	@echo "$(BLUE)Building development image...$(NC)"
	@docker-compose -f docker-compose.dev.yml build
	@echo "$(GREEN)✅ Build complete$(NC)"

rebuild: ## Rebuild images without cache
	@echo "$(BLUE)Rebuilding images (no cache)...$(NC)"
	@docker-compose build --no-cache
	@echo "$(GREEN)✅ Rebuild complete$(NC)"

##@ Logs & Monitoring

logs: ## View logs from all services
	@docker-compose logs -f

logs-app: ## View CIAL application logs only
	@docker-compose logs -f cial

logs-postgres: ## View PostgreSQL logs
	@docker-compose logs -f postgres

logs-redis: ## View Redis logs
	@docker-compose logs -f redis

logs-kafka: ## View Kafka logs
	@docker-compose logs -f kafka

ps: ## Show running containers
	@docker-compose ps

status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)\n"
	@docker-compose ps
	@echo "\n$(BLUE)Health Checks:$(NC)"
	@curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool || echo "$(YELLOW)CIAL not running$(NC)"

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@docker-compose exec -T cial pytest -v
	@echo "$(GREEN)✅ Tests complete$(NC)"

test-unit: ## Run unit tests only
	@docker-compose exec -T cial pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@docker-compose exec -T cial pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	@docker-compose exec -T cial pytest --cov=. --cov-report=html --cov-report=term

test-local: ## Run tests locally (not in Docker)
	@pytest -v --cov

lint: ## Run code linters
	@echo "$(BLUE)Running linters...$(NC)"
	@black --check .
	@ruff check .
	@mypy .

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	@black .
	@isort .
	@echo "$(GREEN)✅ Code formatted$(NC)"

##@ Database

db-shell: ## Open PostgreSQL shell
	@docker-compose exec postgres psql -U cial_user -d cial_ltm

db-migrate: ## Run database migrations
	@docker-compose exec cial alembic upgrade head

db-reset: ## Reset database (WARNING: Deletes all data!)
	@echo "$(YELLOW)⚠️  This will delete all data! Press Ctrl+C to cancel...$(NC)"
	@sleep 3
	@docker-compose down -v
	@docker-compose up -d postgres redis
	@echo "$(GREEN)✅ Database reset$(NC)"

##@ Maintenance

clean: ## Remove all containers, volumes, and images
	@echo "$(YELLOW)Removing containers, volumes, and images...$(NC)"
	@docker-compose down -v --rmi all
	@docker-compose -f docker-compose.dev.yml down -v --rmi all 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-cache: ## Remove Python cache files
	@echo "$(BLUE)Removing cache files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cache cleaned$(NC)"

prune: ## Prune unused Docker resources
	@echo "$(YELLOW)Pruning unused Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)✅ Prune complete$(NC)"

##@ Security

security-scan: ## Scan dependencies for vulnerabilities
	@echo "$(BLUE)Scanning for security vulnerabilities...$(NC)"
	@pip install safety 2>/dev/null || true
	@safety check -r requirements.txt
	@bandit -r . -ll

audit: ## Run security audit
	@echo "$(BLUE)Running security audit...$(NC)"
	@pip-audit

##@ Utilities

shell: ## Open shell in CIAL container
	@docker-compose exec cial bash

shell-dev: ## Open shell in development container
	@docker-compose -f docker-compose.dev.yml exec cial-dev bash

redis-cli: ## Open Redis CLI
	@docker-compose exec redis redis-cli

kafka-topics: ## List Kafka topics
	@docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

create-api-key: ## Create API key (interactive)
	@curl -X POST http://localhost:8000/api/v1/auth/api-key \
		-H "Content-Type: application/json" \
		-d '{"name": "Generated Key", "type": "read_write"}' | python3 -m json.tool

health: ## Check service health
	@curl -s http://localhost:8000/health | python3 -m json.tool

metrics: ## View Prometheus metrics
	@curl -s http://localhost:8000/metrics

##@ Documentation

docs: ## Build documentation
	@cd docs && mkdocs build

docs-serve: ## Serve documentation locally
	@cd docs && mkdocs serve

##@ Information

version: ## Show version information
	@echo "$(BLUE)CIAL Version Information:$(NC)"
	@echo "Python: $$(python3 --version)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"
	@echo "CIAL API: 1.0.0"

env: ## Show environment configuration
	@echo "$(BLUE)Environment Variables:$(NC)"
	@docker-compose config | grep -E "POSTGRES|REDIS|KAFKA" || true
