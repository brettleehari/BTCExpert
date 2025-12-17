# CIAL Runtime Requirements

**Quick Reference for Production Deployment**

---

## What Are Runtime Requirements?

**Runtime Requirements** = What you need when the app is **running in production**

**NOT Runtime** = What you only need during development (testing, linting, docs)

---

## 📦 CIAL Runtime Stack

### Required Services

```
┌─────────────────────────────────────────┐
│         CIAL Application                │
│   Python 3.11.6 + 52 packages          │
│   (from requirements.txt)               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Infrastructure Services          │
├─────────────────────────────────────────┤
│  PostgreSQL 16 + pgvector (database)   │
│  Redis 7.2.4 (cache + pubsub)          │
│  Kafka 7.6.0 (message queue)           │
│  TimescaleDB 2.14.2 (time-series)      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│    Monitoring (Recommended)             │
├─────────────────────────────────────────┤
│  Prometheus (metrics)                   │
│  Grafana (dashboards)                   │
└─────────────────────────────────────────┘
```

### Dependencies Breakdown

**Production Only** (`requirements.txt` - 52 packages):
- ✅ FastAPI framework
- ✅ Database drivers (PostgreSQL, Redis, Kafka)
- ✅ Caching (aiocache)
- ✅ Security (JWT, API keys, rate limiting)
- ✅ Resilience (circuit breaker, retry)
- ✅ Observability (OpenTelemetry, Prometheus)
- ✅ WebSocket support
- ✅ Background tasks (Celery)

**Development Only** (`requirements-dev.txt` - +20 packages):
- ❌ pytest (testing)
- ❌ black, ruff, mypy (code quality)
- ❌ mkdocs (documentation)
- ❌ ipython, ipdb (debugging)
- ❌ locust (load testing)

---

## 💰 Minimum Resource Requirements

### Development / Testing
```yaml
CPU: 2 cores
RAM: 4GB
Disk: 20GB
Cost: $0 (local) or $10-20/month (cloud)
```

### Production (Small - <1000 users)
```yaml
CPU: 4 cores
RAM: 8GB
Disk: 40GB SSD
Cost: $50-150/month
```

### Production (Medium - 1K-100K users)
```yaml
CPU: 8 cores
RAM: 16GB
Disk: 100GB SSD
Cost: $150-500/month
```

### Production (Large - 100K+ users)
```yaml
CPU: 16+ cores
RAM: 32GB+
Disk: 200GB+ SSD
Cost: $500-5000+/month
```

---

## 🚀 Top 3 Deployment Options

### 🥇 #1 Railway.app (Easiest)

**Best for:** Quick deployment, MVP, demos
**Time:** 5 minutes
**Cost:** ~$40/month

```bash
npm install -g @railway/cli
railway login
railway init
railway up  # Done! 🎉
```

**Pros:**
- ✅ Zero configuration
- ✅ Auto-scaling
- ✅ Free SSL
- ✅ Managed databases included

**Cons:**
- ❌ Higher cost at scale
- ❌ Less customization

---

### 🥈 #2 Google Cloud Run (Best Value)

**Best for:** Production, auto-scaling, cost-effective
**Time:** 30 minutes
**Cost:** ~$30-100/month (pay per use)

```bash
gcloud builds submit --tag gcr.io/your-project/cial
gcloud run deploy cial --image gcr.io/your-project/cial --platform managed
```

**Pros:**
- ✅ Serverless (auto-scale to zero)
- ✅ Pay only for what you use
- ✅ Great pricing
- ✅ Fast deployments

**Cons:**
- ❌ Cold starts (mitigated with min-instances)
- ❌ Stateless only

---

### 🥉 #3 DigitalOcean App Platform (Recommended)

**Best for:** Production, growing startups, balanced features
**Time:** 1-2 hours
**Cost:** ~$160/month

```bash
doctl apps create --spec app.yaml
```

**Pros:**
- ✅ Great price/performance
- ✅ Managed databases
- ✅ Easy scaling
- ✅ Good documentation

**Cons:**
- ❌ Fewer features than AWS/GCP
- ❌ Smaller ecosystem

---

### 💎 Bonus: Self-Hosted VPS (Budget)

**Best for:** Full control, learning, budget-conscious
**Time:** 2-3 hours
**Cost:** ~$15-50/month

```bash
# On Ubuntu 22.04 VPS
git clone https://github.com/your-username/BTCExpert.git
cd BTCExpert/cial
./start.sh production  # Done! 🎉
```

**Providers:**
- **Hetzner:** €13.90/month (4 vCPU, 8GB RAM) - Best value
- **DigitalOcean:** $48/month (4 vCPU, 8GB RAM)
- **Linode:** $36/month (4 vCPU, 8GB RAM)

---

## 📋 Production Deployment Checklist

### Before Deployment

- [ ] Copy `.env.example` to `.env`
- [ ] Set `SECRET_KEY` (min 32 random characters)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure database URLs
- [ ] Set API keys (CoinGecko, etc.)
- [ ] Review CORS settings

### Security

- [ ] Enable SSL/TLS certificates
- [ ] Change all default passwords
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up API key authentication
- [ ] Review security settings

### Performance

- [ ] Enable Redis caching
- [ ] Create database indexes: `POST /api/v1/database/optimize/indexes`
- [ ] Create materialized views: `POST /api/v1/database/optimize/views`
- [ ] Set worker count (4-8 workers recommended)
- [ ] Enable connection pooling

### Monitoring

- [ ] Configure Prometheus
- [ ] Set up Grafana dashboards
- [ ] Enable Sentry error tracking
- [ ] Set up health check alerts
- [ ] Configure logging level

### Reliability

- [ ] Enable auto-restart on crash
- [ ] Set up database backups
- [ ] Configure multi-instance deployment (2+ instances)
- [ ] Test circuit breakers
- [ ] Verify retry logic

---

## 🎯 Quick Deployment by Use Case

| Use Case | Recommended Platform | Cost/Month | Setup Time |
|----------|---------------------|-----------|------------|
| **MVP/Demo** | Railway.app | $20-40 | 5 min |
| **Small Production** | Google Cloud Run | $30-100 | 30 min |
| **Growing Startup** | DigitalOcean | $150-500 | 2 hours |
| **Enterprise** | AWS ECS/Kubernetes | $500+ | 1-2 weeks |
| **Budget/Learning** | Hetzner VPS | $15-50 | 2 hours |

---

## 📊 Full Comparison Matrix

| Feature | Railway | Cloud Run | DigitalOcean | AWS ECS | VPS |
|---------|---------|-----------|--------------|---------|-----|
| **Setup Difficulty** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐⭐⭐ Hard | ⭐⭐ Medium |
| **Monthly Cost** | $40 | $30-100 | $160 | $350+ | $15-50 |
| **Auto-Scaling** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Managed DB** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Free SSL** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Extra cost | ⚠️ DIY |
| **Max Scale** | Medium | Very High | High | Very High | Medium |
| **Customization** | Low | Medium | Medium | Very High | Very High |
| **Control** | Low | Medium | Medium | High | Full |

---

## 🔗 Additional Resources

- **Full Deployment Guide:** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Quick Start:** See [QUICKSTART.md](QUICKSTART.md)
- **Prerequisites:** See [PREREQUISITES.md](PREREQUISITES.md)
- **Dependencies:** See [DEPENDENCIES.md](DEPENDENCIES.md)

---

## 💡 Need Help?

**Quick Questions:**
- "How do I deploy quickly?" → Use Railway.app (5 minutes)
- "What's the cheapest option?" → Hetzner VPS ($15/month)
- "What's the best value?" → Google Cloud Run ($30-100/month)
- "What for enterprise?" → AWS ECS or Kubernetes

**Detailed Guidance:**
- Read full [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions
- Check [PREREQUISITES.md](PREREQUISITES.md) for system requirements
- Review [QUICKSTART.md](QUICKSTART.md) for local testing first

---

**Last Updated:** 2025-12-14
**Status:** Production Ready ✅
