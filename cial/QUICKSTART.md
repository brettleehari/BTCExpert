# Quick Start Guide

Get CIAL up and running in 5 minutes!

---

## One-Command Start 🚀

### Prerequisites Check

Do you have Docker installed?

```bash
docker --version
```

**Yes?** Great! Continue below.  
**No?** See [PREREQUISITES.md](PREREQUISITES.md) for installation.

---

## Start CIAL

### Option 1: Production Mode (Recommended)

```bash
./start.sh production
```

**What this does:**
- ✅ Checks prerequisites
- ✅ Builds Docker images
- ✅ Starts all services (PostgreSQL, Redis, Kafka, CIAL)
- ✅ Runs health checks
- ✅ Shows access URLs

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Option 2: Development Mode (Hot-Reload)

```bash
./start.sh development
```

Code changes automatically reload! Perfect for development.

### Option 3: With Monitoring

```bash
./start.sh production monitoring
```

**Includes:**
- Prometheus (http://localhost:9090)
- Grafana (http://localhost:3000)
- Kafka UI (http://localhost:8080)

---

## Using Make (Alternative)

```bash
# Start production
make start

# Start development
make start-dev

# Start with monitoring
make start-monitoring

# View logs
make logs

# Run tests
make test

# Stop all services
make stop

# See all commands
make help
```

---

## First API Request

### Test Health Endpoint

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "CIAL",
  "version": "1.0.0",
  "components": {
    "api": "operational",
    "redis": "connected",
    "postgres": "connected",
    "kafka": "connected"
  }
}
```

### Get API Documentation

Open browser to: http://localhost:8000/docs

Interactive Swagger UI with all endpoints!

### Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-key \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Key",
    "type": "read_write",
    "rate_limit": 100
  }'
```

**⚠️ Save the API key!** It's only shown once.

### Make Authenticated Request

```bash
# Using your API key from above
API_KEY="cial_abc123..."

# Get price intelligence
curl http://localhost:8000/api/v1/intelligence/price \
  -H "Authorization: Bearer $API_KEY"
```

---

## Quick Command Reference

### Start/Stop

```bash
./start.sh production    # Start
docker-compose down      # Stop
docker-compose restart   # Restart
```

### View Logs

```bash
docker-compose logs -f              # All services
docker-compose logs -f cial         # CIAL only
docker-compose logs -f postgres     # PostgreSQL only
```

### Check Status

```bash
docker-compose ps                   # Container status
curl http://localhost:8000/health   # Health check
curl http://localhost:8000/metrics  # Prometheus metrics
```

### Database Access

```bash
# PostgreSQL shell
docker-compose exec postgres psql -U cial_user -d cial_ltm

# Redis CLI
docker-compose exec redis redis-cli
```

### Testing

```bash
make test              # All tests
make test-unit         # Unit tests only
make test-cov          # With coverage
```

---

## Common Use Cases

### 1. Get Bitcoin Price

```bash
curl http://localhost:8000/api/v1/intelligence/price/bitcoin
```

### 2. Subscribe to Real-Time Updates (WebSocket)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/websocket/stream');

ws.onopen = () => {
  // Subscribe to price alerts
  ws.send(JSON.stringify({
    type: 'subscribe',
    subscriptions: ['price.critical']
  }));
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Intelligence update:', update);
};
```

### 3. Query Time-Series Data

```bash
# Get hourly price statistics
curl "http://localhost:8000/api/v1/timeseries/hourly?symbol=bitcoin&hours=24"
```

### 4. Cache Warm for Better Performance

```bash
curl -X POST http://localhost:8000/api/v1/cache/warm
```

### 5. Database Optimization

```bash
# Create performance indexes
curl -X POST http://localhost:8000/api/v1/database/optimize/indexes

# Create materialized views
curl -X POST http://localhost:8000/api/v1/database/optimize/materialized-views
```

---

## Troubleshooting

### Ports Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed`

**Solution:**
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Rebuild images
docker-compose build --no-cache

# Reset everything
docker-compose down -v
./start.sh
```

### Docker Daemon Not Running

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
```bash
# Start Docker
sudo systemctl start docker  # Linux
open /Applications/Docker.app  # macOS
# Start Docker Desktop  # Windows
```

---

## Next Steps

### 1. Explore API Documentation
http://localhost:8000/docs

### 2. Set Up Monitoring
```bash
./start.sh production monitoring
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### 3. Configure External APIs

Edit `.env` file:
```env
COINGECKO_API_KEY=your-key-here
NEWS_API_KEY=your-key-here
```

### 4. Run Tests

```bash
make test
```

### 5. Read Full Documentation

- [Prerequisites](PREREQUISITES.md)
- [Dependencies](DEPENDENCIES.md)
- [Session Documentation](docs/)

---

## Production Deployment

For production deployment:

1. **Update .env**
   ```env
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=<generate-secure-key>
   ```

2. **Generate secure secret**
   ```bash
   openssl rand -hex 32
   ```

3. **Configure HTTPS**
   - Use reverse proxy (nginx, traefik)
   - Install SSL certificate (Let's Encrypt)

4. **Scale services**
   ```bash
   docker-compose up -d --scale cial=3
   ```

5. **Enable monitoring**
   ```bash
   ./start.sh production monitoring
   ```

6. **Set up backups**
   - PostgreSQL: pg_dump daily
   - Redis: AOF persistence
   - Volumes: rsync or AWS EBS snapshots

---

## Help & Support

- 📖 **Documentation:** [Session Docs](docs/)
- 🐛 **Issues:** https://github.com/yourusername/BTCExpert/issues
- 💬 **Discussions:** https://github.com/yourusername/BTCExpert/discussions
- 📧 **Email:** support@cial.io

---

**Happy Trading! 🚀**
