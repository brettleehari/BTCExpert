#!/bin/bash
# CIAL Startup Script
# One-command deployment for CIAL application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  CIAL - Crypto Intelligence Abstraction Layer${NC}"
echo -e "${BLUE}  One-Command Startup Script${NC}"
echo -e "${BLUE}================================================${NC}\n"

# Parse arguments
ENVIRONMENT="${1:-production}"  # Default to production
PROFILE="${2:-}"  # Optional profile (monitoring, timescale)

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(production|development|dev)$ ]]; then
    echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
    echo -e "Valid options: production, development, dev"
    exit 1
fi

# Map 'dev' to 'development'
if [ "$ENVIRONMENT" = "dev" ]; then
    ENVIRONMENT="development"
fi

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================
echo -e "${YELLOW}📋 Step 1: Checking prerequisites...${NC}\n"

check_command() {
    if command -v "$1" &> /dev/null; then
        VERSION=$($1 --version 2>&1 | head -n 1)
        echo -e "${GREEN}✅ $1${NC} - $VERSION"
        return 0
    else
        echo -e "${RED}❌ $1 not found${NC}"
        return 1
    fi
}

MISSING_DEPS=0

# Check Docker
if ! check_command docker; then
    MISSING_DEPS=1
fi

# Check Docker Compose
if ! check_command docker-compose && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found${NC}"
    MISSING_DEPS=1
else
    echo -e "${GREEN}✅ docker-compose${NC}"
fi

# Optional: Check Python (for local development)
if [ "$ENVIRONMENT" = "development" ]; then
    if ! check_command python3; then
        echo -e "${YELLOW}⚠️  Python3 not found (optional for Docker deployment)${NC}"
    fi
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "\n${RED}❌ Missing prerequisites! Please install missing dependencies.${NC}"
    echo -e "See PREREQUISITES.md for installation instructions."
    exit 1
fi

echo -e "\n${GREEN}✅ All prerequisites met!${NC}\n"

# ============================================================================
# STEP 2: Check Docker Daemon
# ============================================================================
echo -e "${YELLOW}🐳 Step 2: Checking Docker daemon...${NC}\n"

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo -e "Please start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker daemon is running${NC}\n"

# ============================================================================
# STEP 3: Create required directories
# ============================================================================
echo -e "${YELLOW}📁 Step 3: Creating required directories...${NC}\n"

mkdir -p logs
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources

echo -e "${GREEN}✅ Directories created${NC}\n"

# ============================================================================
# STEP 4: Environment file check
# ============================================================================
echo -e "${YELLOW}⚙️  Step 4: Checking environment configuration...${NC}\n"

if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found, creating from .env.example...${NC}"

    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Please review and update .env with your settings${NC}"
    else
        echo -e "${YELLOW}⚠️  No .env.example found, using defaults${NC}"
    fi
fi

echo ""

# ============================================================================
# STEP 5: Stop existing containers
# ============================================================================
echo -e "${YELLOW}🛑 Step 5: Stopping existing containers...${NC}\n"

if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
else
    docker-compose down 2>/dev/null || true
fi

echo -e "${GREEN}✅ Existing containers stopped${NC}\n"

# ============================================================================
# STEP 6: Pull/Build Images
# ============================================================================
echo -e "${YELLOW}🔨 Step 6: Building/Pulling Docker images...${NC}\n"

if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml build
else
    docker-compose build
fi

echo -e "\n${GREEN}✅ Images ready${NC}\n"

# ============================================================================
# STEP 7: Start Services
# ============================================================================
echo -e "${YELLOW}🚀 Step 7: Starting CIAL services...${NC}\n"

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "${BLUE}Starting in DEVELOPMENT mode with hot-reload...${NC}\n"

    if [ -n "$PROFILE" ]; then
        docker-compose -f docker-compose.dev.yml --profile "$PROFILE" up -d
    else
        docker-compose -f docker-compose.dev.yml up -d
    fi
else
    echo -e "${BLUE}Starting in PRODUCTION mode...${NC}\n"

    if [ -n "$PROFILE" ]; then
        docker-compose --profile "$PROFILE" up -d
    else
        docker-compose up -d
    fi
fi

echo ""

# ============================================================================
# STEP 8: Wait for Services
# ============================================================================
echo -e "${YELLOW}⏳ Step 8: Waiting for services to be healthy...${NC}\n"

wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo -n "Waiting for $service... "

    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep "$service" | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✅ Ready${NC}"
            return 0
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ Timeout${NC}"
    return 1
}

# Wait for core services
wait_for_service "postgres" || true
wait_for_service "redis" || true
wait_for_service "kafka" || true

# Wait for CIAL app
if [ "$ENVIRONMENT" = "production" ]; then
    wait_for_service "cial-app" || true
fi

echo ""

# ============================================================================
# STEP 9: Run Health Checks
# ============================================================================
echo -e "${YELLOW}🏥 Step 9: Running health checks...${NC}\n"

sleep 5  # Give services a moment to stabilize

check_health() {
    local service=$1
    local url=$2

    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service health check failed${NC}"
        return 1
    fi
}

if [ "$ENVIRONMENT" = "production" ]; then
    check_health "CIAL API" "http://localhost:8000/health" || true
fi

check_health "Redis" "http://localhost:6379" 2>/dev/null || echo -e "${GREEN}✅ Redis is running${NC}"
check_health "PostgreSQL" "http://localhost:5432" 2>/dev/null || echo -e "${GREEN}✅ PostgreSQL is running${NC}"

echo ""

# ============================================================================
# SUCCESS!
# ============================================================================
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  ✅ CIAL Successfully Started!${NC}"
echo -e "${GREEN}================================================${NC}\n"

echo -e "${BLUE}📊 Service Status:${NC}\n"
docker-compose ps

echo -e "\n${BLUE}🌐 Access Points:${NC}\n"

if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "  • CIAL API:        ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API Docs:        ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  • Health Check:    ${GREEN}http://localhost:8000/health${NC}"
    echo -e "  • Metrics:         ${GREEN}http://localhost:8000/metrics${NC}"
else
    echo -e "  • CIAL API (dev):  ${GREEN}http://localhost:8000${NC} ${YELLOW}(with hot-reload)${NC}"
    echo -e "  • API Docs:        ${GREEN}http://localhost:8000/docs${NC}"
fi

echo -e "  • Kafka UI:        ${GREEN}http://localhost:8080${NC}"

if [[ "$PROFILE" == *"monitoring"* ]]; then
    echo -e "  • Prometheus:      ${GREEN}http://localhost:9090${NC}"
    echo -e "  • Grafana:         ${GREEN}http://localhost:3000${NC} ${YELLOW}(admin/admin)${NC}"
fi

echo -e "\n${BLUE}📝 Useful Commands:${NC}\n"
echo -e "  • View logs:       ${YELLOW}docker-compose logs -f${NC}"
echo -e "  • Stop services:   ${YELLOW}docker-compose down${NC}"
echo -e "  • Restart:         ${YELLOW}./start.sh${NC}"

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "  • Run tests:       ${YELLOW}docker-compose exec cial-dev pytest${NC}"
fi

echo -e "\n${BLUE}📖 Documentation:${NC}\n"
echo -e "  • Prerequisites:   ${YELLOW}PREREQUISITES.md${NC}"
echo -e "  • Dependencies:    ${YELLOW}DEPENDENCIES.md${NC}"
echo -e "  • Quick Start:     ${YELLOW}QUICKSTART.md${NC}"

echo -e "\n${GREEN}Happy Trading! 🚀${NC}\n"
