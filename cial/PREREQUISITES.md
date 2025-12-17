# Prerequisites & System Requirements

**Last Updated:** 2025-12-13

This document lists all prerequisites and dependencies required to run CIAL.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Required Software](#required-software)
3. [Optional Software](#optional-software)
4. [Installation Guides](#installation-guides)
5. [Port Requirements](#port-requirements)
6. [Verification](#verification)

---

## System Requirements

### Minimum Requirements (Development)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 20 GB free | 50 GB free (SSD preferred) |
| **OS** | Linux, macOS, Windows 10+ | Linux (Ubuntu 22.04+) |

### Production Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 16 GB | 32+ GB |
| **Disk** | 100 GB | 500 GB (NVMe SSD) |
| **OS** | Linux | Ubuntu 22.04 LTS or RHEL 8+ |

---

## Required Software

### 1. Docker & Docker Compose

**Required:** Yes (for containerized deployment)
**Version:** Docker 24.0+, Docker Compose 2.0+

Docker is the **primary** way to run CIAL. All services run in containers.

**Installation:**

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify
docker --version
docker compose version
```

#### macOS
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop/

# Or using Homebrew:
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app

# Verify
docker --version
docker compose version
```

#### Windows
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop/

# Install and restart
# Enable WSL 2 backend (recommended)

# Verify in PowerShell:
docker --version
docker compose version
```

### 2. Git

**Required:** Yes (for cloning repository)
**Version:** 2.0+

```bash
# Linux
sudo apt-get install git

# macOS
brew install git

# Windows
# Download from: https://git-scm.com/download/win

# Verify
git --version
```

### 3. Python (Optional for local development)

**Required:** No (Docker includes Python)
**Version:** 3.11.6 (exact)

Only needed if you want to run CIAL outside Docker.

```bash
# Using pyenv (recommended)
curl https://pyenv.run | bash

# Add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

# Install Python 3.11.6
pyenv install 3.11.6
pyenv local 3.11.6

# Verify
python --version  # Should show 3.11.6
```

**Alternative:**
```bash
# Linux
sudo apt-get install python3.11 python3.11-venv

# macOS
brew install python@3.11

# Windows
# Download from: https://www.python.org/downloads/
```

---

## Optional Software

### 1. Make

**Purpose:** Convenient command runner (Makefile support)
**Installation:**

```bash
# Linux
sudo apt-get install build-essential

# macOS (already installed)
xcode-select --install

# Windows
# Download Make for Windows: http://gnuwin32.sourceforge.net/packages/make.htm
# Or use WSL
```

### 2. curl & jq

**Purpose:** API testing and JSON parsing
**Installation:**

```bash
# Linux
sudo apt-get install curl jq

# macOS
brew install curl jq

# Windows
# curl is built-in (PowerShell)
# jq: choco install jq
```

### 3. HTTPie (Better than curl)

**Purpose:** User-friendly HTTP client
**Installation:**

```bash
# All platforms
pip install httpie

# Verify
http --version
```

---

## External Dependencies (Handled by Docker)

These are **automatically installed** via Docker Compose:

| Service | Version | Purpose | Port |
|---------|---------|---------|------|
| PostgreSQL | 16 + pgvector | Long-term memory & vector search | 5432 |
| Redis | 7.2.4 | Short-term memory & caching | 6379 |
| Kafka | 7.6.0 | Event streaming | 9092, 9093 |
| Zookeeper | 7.6.0 | Kafka coordination | 2181 |
| TimescaleDB | 2.14.2 | Time-series data (optional) | 5433 |

**You don't need to install these manually!** Docker handles everything.

---

## Port Requirements

### Required Ports (Must be free)

| Port | Service | Can Change? |
|------|---------|-------------|
| **8000** | CIAL API | Yes (via .env) |
| **5432** | PostgreSQL | Yes (via docker-compose.yml) |
| **6379** | Redis | Yes (via docker-compose.yml) |
| **9092** | Kafka (internal) | Yes |
| **9093** | Kafka (external) | Yes |
| **2181** | Zookeeper | Yes |

### Optional Ports

| Port | Service | Profile |
|------|---------|---------|
| **8080** | Kafka UI | monitoring |
| **5433** | TimescaleDB | timescale |
| **9090** | Prometheus | monitoring |
| **3000** | Grafana | monitoring |

### Check if Ports are Available

```bash
# Linux/macOS
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :6379

# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5432
```

**If ports are in use:**
1. Stop the conflicting service
2. Or change ports in `docker-compose.yml`

---

## Installation Guides

### Quick Start (Docker Only)

```bash
# 1. Install Docker & Docker Compose (see above)

# 2. Clone repository
git clone https://github.com/yourusername/BTCExpert.git
cd BTCExpert/cial

# 3. Start CIAL
./start.sh production

# OR using Make
make start
```

**That's it!** No other dependencies needed.

### Local Development (Without Docker)

```bash
# 1. Install Python 3.11.6
pyenv install 3.11.6
pyenv local 3.11.6

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt

# 4. Install and start services manually
# PostgreSQL, Redis, Kafka (see OS-specific guides)

# 5. Create .env file
cp .env.example .env
# Edit .env with your settings

# 6. Run CIAL
python main.py
```

---

## Environment Variables

Create a `.env` file in the `cial/` directory:

```bash
# Copy example
cp .env.example .env

# Edit with your settings
vim .env
```

**Minimum required variables:**
```env
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-very-secure-secret-key-min-32-chars

# PostgreSQL (if not using Docker defaults)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cial_ltm
POSTGRES_USER=cial_user
POSTGRES_PASSWORD=cial_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# API Keys (optional)
COINGECKO_API_KEY=your-api-key
```

---

## Verification

### Verify Installation

```bash
# Check Docker
docker --version
docker compose version
docker info

# Check Git
git --version

# Check Python (if installed)
python3 --version
python3 -m venv --help

# Check Make (if installed)
make --version

# Check ports
sudo lsof -i :8000  # Should be free
sudo lsof -i :5432  # Should be free
sudo lsof -i :6379  # Should be free
```

### Test Docker Setup

```bash
# Test Docker
docker run hello-world

# Test Docker Compose
cd BTCExpert/cial
docker-compose config  # Should show no errors
```

### System Information

```bash
# Linux
uname -a
free -h
df -h

# macOS
sw_vers
sysctl -n hw.memsize
df -h

# Windows (PowerShell)
systeminfo
Get-WmiObject -Class Win32_ComputerSystem
```

---

## Troubleshooting

### Docker Daemon Not Running

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# macOS
open /Applications/Docker.app

# Windows
# Start Docker Desktop from Start Menu
```

### Permission Denied

**Error:** `Got permission denied while trying to connect to the Docker daemon socket`

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo docker-compose up
```

### Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Out of Memory

**Error:** `Cannot allocate memory`

**Solution:**
1. Increase Docker Desktop memory limit (Settings → Resources)
2. Close other applications
3. Restart Docker

### Slow Performance

**Causes & Solutions:**

1. **Insufficient RAM**
   - Increase Docker memory limit
   - Close other applications
   - Add swap space

2. **Slow disk**
   - Use SSD instead of HDD
   - Clear Docker cache: `docker system prune -a`

3. **Too many containers**
   - Stop unused services: `docker-compose stop kafka-ui timescaledb`
   - Use profiles: `docker-compose up -d` (without --profile)

---

## Operating System Specific Notes

### Linux (Ubuntu 22.04)

**Recommended** - Best performance

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install build essentials
sudo apt-get install build-essential git curl

# Reboot
sudo reboot
```

### macOS (12.0+)

**Recommended** - Good performance

- Use Docker Desktop (simplest)
- Allocate at least 8GB RAM to Docker
- Enable "Use Rosetta for x86/amd64 emulation" (Apple Silicon)

### Windows 10/11

**Supported** - Use WSL 2

1. Enable WSL 2:
   ```powershell
   wsl --install
   ```

2. Install Docker Desktop with WSL 2 backend

3. Run CIAL from within WSL 2:
   ```bash
   wsl
   cd /mnt/c/Users/YourName/BTCExpert/cial
   ./start.sh
   ```

---

## Cloud Deployment

### AWS

**Recommended Instance:** t3.xlarge or larger
- 4 vCPUs
- 16 GB RAM
- Amazon Linux 2 or Ubuntu 22.04

### Google Cloud

**Recommended Instance:** n2-standard-4 or larger
- 4 vCPUs
- 16 GB RAM
- Ubuntu 22.04 LTS

### Azure

**Recommended Instance:** Standard_D4s_v3 or larger
- 4 vCPUs
- 16 GB RAM
- Ubuntu 22.04 LTS

### DigitalOcean

**Recommended Droplet:** CPU-Optimized, 8GB
- 4 vCPUs
- 8 GB RAM
- Ubuntu 22.04

---

## Summary Checklist

Before running CIAL, ensure:

- [ ] Docker installed (24.0+)
- [ ] Docker Compose installed (2.0+)
- [ ] Docker daemon running
- [ ] Git installed
- [ ] 8GB+ RAM available
- [ ] 20GB+ disk space available
- [ ] Ports 8000, 5432, 6379 available
- [ ] `.env` file created (from `.env.example`)
- [ ] User added to docker group (Linux)

**Then run:**
```bash
./start.sh production
# or
make start
```

---

**Need Help?**
- 📖 See `QUICKSTART.md` for usage
- 🐛 Report issues at: https://github.com/yourusername/BTCExpert/issues
- 📚 Read documentation at: https://cial.readthedocs.io
