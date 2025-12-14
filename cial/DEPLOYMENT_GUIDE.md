# CIAL Deployment Guide

**Version:** 1.0
**Last Updated:** 2025-12-14
**Status:** Production Ready

---

## 📦 Runtime Requirements

### What Are Runtime Requirements?

**Runtime requirements** = Dependencies needed when the application is **running in production**

**Build-time/Development requirements** = Tools only needed during development (testing, linting, docs)

### CIAL Runtime Requirements

**✅ Production Dependencies** (`requirements.txt`):
- **52 packages** - Everything needed to run CIAL in production
- Includes: FastAPI, databases, caching, observability, security, resilience
- Excludes: Testing tools, linters, documentation generators

**❌ NOT Needed at Runtime** (`requirements-dev.txt`):
- Testing: pytest, pytest-cov, fakeredis
- Code quality: black, ruff, mypy, pylint
- Documentation: mkdocs, mkdocstrings
- Debugging: ipython, ipdb
- Load testing: locust

### Minimal Runtime Stack

```yaml
# Absolute minimum to run CIAL
App: Python 3.11.6 + requirements.txt (52 packages)
Database: PostgreSQL 16 + pgvector
Cache: Redis 7.2.4
Message Queue: Kafka 7.6.0
Time-Series: TimescaleDB 2.14.2
Monitoring: Prometheus + Grafana (optional but recommended)
```

---

## 🚀 Deployment Options

### Quick Comparison

| Platform | Difficulty | Cost | Scale | Best For |
|----------|-----------|------|-------|----------|
| **Railway.app** | ⭐ Easy | $$ | Medium | Quick POC/MVP |
| **Render.com** | ⭐ Easy | $$ | Medium | Small-Medium projects |
| **DigitalOcean App Platform** | ⭐⭐ Medium | $$ | Medium-High | Production apps |
| **AWS ECS/Fargate** | ⭐⭐⭐ Hard | $$$ | High | Enterprise |
| **Google Cloud Run** | ⭐⭐ Medium | $$ | High | Serverless + autoscale |
| **Azure Container Apps** | ⭐⭐ Medium | $$$ | High | Microsoft ecosystem |
| **Kubernetes (EKS/GKE/AKS)** | ⭐⭐⭐⭐ Very Hard | $$$$ | Very High | Large-scale enterprise |
| **Self-hosted (VPS)** | ⭐⭐ Medium | $ | Medium | Full control + budget |

---

## 🎯 Recommended Deployments

### Option 1: Railway.app (Easiest - 5 Minutes)

**Best for:** Quick deployment, MVP, demos
**Cost:** ~$20-50/month
**Pros:** Zero config, auto-scaling, free SSL, managed databases
**Cons:** Limited customization, vendor lock-in

#### Steps:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Add services via Railway dashboard:
#    - PostgreSQL (with pgvector)
#    - Redis
#    - Kafka

# 5. Deploy
railway up

# 6. Set environment variables in Railway dashboard
# (Copy from .env.example)
```

**Railway automatically:**
- Detects Dockerfile
- Builds and deploys
- Provides public URL
- Manages SSL certificates
- Auto-restarts on crashes

**Estimated Cost:**
- App: $10/month (1GB RAM)
- PostgreSQL: $10/month (1GB)
- Redis: $5/month (256MB)
- Kafka: $15/month (512MB)
- **Total: ~$40/month**

---

### Option 2: DigitalOcean App Platform (Recommended for Production)

**Best for:** Production apps, growing startups
**Cost:** ~$50-150/month
**Pros:** Good price/performance, managed services, easy scaling
**Cons:** Less features than AWS/GCP

#### Steps:

**1. Create DO Account & Install CLI**
```bash
# Install doctl
brew install doctl  # macOS
# OR
wget https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz

# Authenticate
doctl auth init
```

**2. Create Managed Databases**
```bash
# PostgreSQL with pgvector
doctl databases create cial-postgres \
  --engine pg \
  --version 16 \
  --size db-s-2vcpu-4gb \
  --region nyc3

# Redis
doctl databases create cial-redis \
  --engine redis \
  --version 7 \
  --size db-s-1vcpu-1gb \
  --region nyc3
```

**3. Deploy App via Dashboard**
```yaml
# app.yaml
name: cial
services:
  - name: api
    dockerfile_path: Dockerfile
    github:
      repo: your-username/BTCExpert
      branch: main
      deploy_on_push: true
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        type: SECRET
      - key: REDIS_URL
        scope: RUN_TIME
        type: SECRET
    health_check:
      http_path: /health
    instance_size_slug: professional-xs  # 1 vCPU, 2GB RAM
    instance_count: 2
```

**4. Deploy**
```bash
doctl apps create --spec app.yaml
```

**Estimated Cost:**
- App (2 instances): $24/month
- PostgreSQL (2vCPU, 4GB): $60/month
- Redis (1vCPU, 1GB): $15/month
- Kafka (managed): $50/month (use DigitalOcean Marketplace)
- Load Balancer: $12/month
- **Total: ~$161/month**

---

### Option 3: AWS ECS Fargate (Enterprise Production)

**Best for:** Enterprise, high-scale, compliance needs
**Cost:** ~$200-500/month
**Pros:** Full AWS ecosystem, enterprise features, infinite scale
**Cons:** Complex, expensive, steep learning curve

#### Architecture:

```
Internet
   ↓
Application Load Balancer
   ↓
ECS Fargate Tasks (2-10 containers)
   ↓
RDS PostgreSQL + ElastiCache Redis + MSK (Kafka)
```

#### Steps:

**1. Install AWS CLI & ECS CLI**
```bash
aws configure
pip install aws-cli ecs-cli
```

**2. Create Infrastructure**
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier cial-postgres \
  --db-instance-class db.t4g.medium \
  --engine postgres \
  --engine-version 16.1 \
  --master-username cialadmin \
  --master-user-password <strong-password> \
  --allocated-storage 100 \
  --storage-type gp3

# Create ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id cial-redis \
  --cache-node-type cache.t4g.medium \
  --engine redis \
  --engine-version 7.1 \
  --num-cache-nodes 1

# Create MSK (Kafka)
aws kafka create-cluster \
  --cluster-name cial-kafka \
  --kafka-version 3.6.0 \
  --number-of-broker-nodes 3 \
  --broker-node-group-info instanceType=kafka.t3.small,storageInfo={ebsStorageInfo={volumeSize=100}}
```

**3. Create ECS Task Definition**
```json
{
  "family": "cial-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [{
    "name": "cial",
    "image": "your-ecr-repo/cial:latest",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"}
    ],
    "secrets": [
      {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/cial",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
```

**4. Deploy**
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t cial .
docker tag cial:latest <account>.dkr.ecr.us-east-1.amazonaws.com/cial:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/cial:latest

# Create ECS Service
aws ecs create-service \
  --cluster cial-cluster \
  --service-name cial-api \
  --task-definition cial-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=cial,containerPort=8000
```

**Estimated Cost:**
- ECS Fargate (2 tasks, 1vCPU, 2GB): $60/month
- RDS PostgreSQL (db.t4g.medium): $70/month
- ElastiCache Redis (cache.t4g.medium): $50/month
- MSK Kafka (3 brokers, t3.small): $120/month
- ALB: $23/month
- Data transfer: $20/month
- CloudWatch Logs: $10/month
- **Total: ~$353/month**

---

### Option 4: Google Cloud Run (Serverless - Best Value)

**Best for:** Cost-effective production, auto-scaling
**Cost:** ~$30-100/month (pay per use)
**Pros:** Serverless, auto-scale to zero, great pricing
**Cons:** Cold starts, stateless only

#### Steps:

**1. Install gcloud CLI**
```bash
curl https://sdk.cloud.google.com | bash
gcloud init
```

**2. Create Cloud SQL (PostgreSQL)**
```bash
gcloud sql instances create cial-postgres \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create cial --instance=cial-postgres
```

**3. Create Memorystore (Redis)**
```bash
gcloud redis instances create cial-redis \
  --size=1 \
  --region=us-central1 \
  --tier=basic
```

**4. Deploy to Cloud Run**
```bash
# Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/your-project/cial

# Deploy
gcloud run deploy cial \
  --image gcr.io/your-project/cial \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production \
  --set-cloudsql-instances your-project:us-central1:cial-postgres
```

**Estimated Cost:**
- Cloud Run (avg 2 instances): $40/month
- Cloud SQL (db-f1-micro): $10/month
- Memorystore Redis (1GB): $40/month
- Pub/Sub (instead of Kafka): $10/month
- **Total: ~$100/month**

---

### Option 5: Self-Hosted VPS (Budget Option)

**Best for:** Full control, budget-conscious, learning
**Cost:** ~$20-80/month
**Pros:** Complete control, cheapest option
**Cons:** You manage everything, no managed services

#### Recommended VPS Providers:

| Provider | Plan | Specs | Cost |
|----------|------|-------|------|
| **Hetzner** | CPX31 | 4 vCPU, 8GB RAM, 160GB SSD | €13.90/month (~$15) |
| **DigitalOcean** | Droplet | 4 vCPU, 8GB RAM, 160GB SSD | $48/month |
| **Linode** | Dedicated | 4 vCPU, 8GB RAM, 160GB SSD | $36/month |
| **Vultr** | High Frequency | 4 vCPU, 8GB RAM, 128GB SSD | $48/month |

#### Setup (Ubuntu 22.04):

```bash
# 1. Create VPS and SSH in
ssh root@your-vps-ip

# 2. Update system
apt update && apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Install Docker Compose
apt install docker-compose-plugin -y

# 5. Clone repo
git clone https://github.com/your-username/BTCExpert.git
cd BTCExpert/cial

# 6. Configure environment
cp .env.example .env
nano .env  # Edit settings

# 7. Start CIAL
./start.sh production

# 8. Setup Nginx reverse proxy
apt install nginx certbot python3-certbot-nginx -y

cat > /etc/nginx/sites-available/cial <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support
    location /api/v1/websocket {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -s /etc/nginx/sites-available/cial /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# 9. Get SSL certificate
certbot --nginx -d your-domain.com

# 10. Setup auto-start
cat > /etc/systemd/system/cial.service <<EOF
[Unit]
Description=CIAL - Crypto Intelligence Abstraction Layer
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/BTCExpert/cial
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl enable cial
systemctl start cial
```

**Estimated Cost:**
- VPS (4 vCPU, 8GB RAM): $15-48/month
- Domain name: $12/year (~$1/month)
- **Total: ~$16-49/month**

---

## 📊 Resource Requirements

### Minimum Requirements (Development/Testing)

```yaml
CPU: 2 cores
RAM: 4GB
Disk: 20GB
Services:
  - PostgreSQL: 512MB RAM
  - Redis: 256MB RAM
  - Kafka: 512MB RAM
  - CIAL App: 512MB RAM
```

### Recommended (Production - Low Traffic)

```yaml
CPU: 4 cores
RAM: 8GB
Disk: 40GB SSD
Services:
  - PostgreSQL: 2GB RAM, 20GB SSD
  - Redis: 1GB RAM
  - Kafka: 2GB RAM, 10GB SSD
  - CIAL App: 2GB RAM (2 instances)
  - Prometheus: 512MB RAM
  - Grafana: 512MB RAM
```

### High Performance (Production - High Traffic)

```yaml
CPU: 16+ cores
RAM: 32GB+
Disk: 200GB+ SSD
Services:
  - PostgreSQL: 8GB RAM, 100GB SSD (with replicas)
  - Redis: 4GB RAM (with replication)
  - Kafka: 8GB RAM, 50GB SSD (3 brokers)
  - CIAL App: 4GB RAM (4-8 instances)
  - TimescaleDB: 8GB RAM, 100GB SSD
  - Prometheus: 2GB RAM
  - Grafana: 1GB RAM
Load Balancer: Required
Auto-scaling: Enabled
```

---

## 🔐 Production Checklist

### Security

- [ ] Change all default passwords
- [ ] Set strong `SECRET_KEY` (min 32 chars)
- [ ] Enable SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up VPC/private networking for databases
- [ ] Enable database encryption at rest
- [ ] Configure rate limiting
- [ ] Set up API key authentication
- [ ] Enable CORS properly
- [ ] Use environment variables (never hardcode secrets)

### Monitoring

- [ ] Configure Prometheus metrics
- [ ] Set up Grafana dashboards
- [ ] Enable application logging (structlog)
- [ ] Set up error tracking (Sentry)
- [ ] Configure health checks
- [ ] Set up uptime monitoring
- [ ] Enable database query monitoring
- [ ] Configure alerts for critical events

### Performance

- [ ] Enable Redis caching
- [ ] Configure connection pooling
- [ ] Set up database indexes (use `/api/v1/database/optimize/indexes`)
- [ ] Enable materialized views (use `/api/v1/database/optimize/views`)
- [ ] Configure rate limiting per endpoint
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets (if any)
- [ ] Configure proper worker count (4-8 workers)

### Reliability

- [ ] Enable auto-restart on crash
- [ ] Configure health checks
- [ ] Set up database backups (daily)
- [ ] Configure Redis persistence
- [ ] Set up multi-instance deployment
- [ ] Enable circuit breakers
- [ ] Configure retry logic
- [ ] Set up disaster recovery plan

### Compliance

- [ ] Set up audit logging
- [ ] Configure data retention policies
- [ ] Enable encryption in transit (TLS)
- [ ] Enable encryption at rest
- [ ] Set up access controls
- [ ] Configure GDPR compliance (if applicable)
- [ ] Set up SOC2 compliance (if applicable)

---

## 🎯 Deployment Recommendations by Use Case

### Use Case 1: MVP / Demo
**Recommendation:** Railway or Render
**Cost:** $20-40/month
**Time to Deploy:** 5-15 minutes

### Use Case 2: Small Production App (<1000 users)
**Recommendation:** DigitalOcean App Platform or Google Cloud Run
**Cost:** $50-150/month
**Time to Deploy:** 1-2 hours

### Use Case 3: Growing Startup (1K-100K users)
**Recommendation:** DigitalOcean or Google Cloud Run
**Cost:** $150-500/month
**Time to Deploy:** 2-4 hours

### Use Case 4: Enterprise (100K+ users)
**Recommendation:** AWS ECS/Fargate or Kubernetes
**Cost:** $500-5000+/month
**Time to Deploy:** 1-2 weeks

### Use Case 5: Budget / Learning
**Recommendation:** Self-hosted VPS (Hetzner)
**Cost:** $15-50/month
**Time to Deploy:** 2-3 hours

---

## 🚀 Quick Start Deployment

### Fastest: Railway.app (5 minutes)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and init
railway login
railway init

# 3. Add PostgreSQL, Redis, Kafka via dashboard

# 4. Deploy
railway up

# Done! Your app is live 🎉
```

### Best Value: Google Cloud Run (30 minutes)

```bash
# 1. Install gcloud
curl https://sdk.cloud.google.com | bash

# 2. Create services
gcloud sql instances create cial-pg --database-version=POSTGRES_16 --tier=db-f1-micro
gcloud redis instances create cial-redis --size=1 --region=us-central1

# 3. Deploy
gcloud builds submit --tag gcr.io/your-project/cial
gcloud run deploy cial --image gcr.io/your-project/cial --platform managed

# Done! Auto-scaling serverless deployment 🎉
```

---

## 📞 Support & Resources

- **CIAL Documentation:** See README.md, QUICKSTART.md, PREREQUISITES.md
- **Docker Documentation:** https://docs.docker.com
- **Railway:** https://docs.railway.app
- **DigitalOcean:** https://docs.digitalocean.com
- **AWS:** https://docs.aws.amazon.com/ecs
- **Google Cloud:** https://cloud.google.com/run/docs
- **Kubernetes:** https://kubernetes.io/docs

---

**Last Updated:** 2025-12-14
**Maintained By:** CIAL Team
**License:** See LICENSE file
