# GitHub to Cloud Deployment Guide

**Automated Deployment from GitHub Repository**

---

## ✅ Platforms with GitHub Integration

All major platforms support **direct GitHub deployment**:

| Platform | GitHub Integration | Auto-Deploy on Push | Setup Difficulty |
|----------|-------------------|---------------------|------------------|
| **Railway.app** | ✅ Native | ✅ Yes | ⭐ Very Easy |
| **Render.com** | ✅ Native | ✅ Yes | ⭐ Very Easy |
| **DigitalOcean App Platform** | ✅ Native | ✅ Yes | ⭐ Easy |
| **Google Cloud Run** | ✅ Via Cloud Build | ✅ Yes | ⭐⭐ Medium |
| **AWS (ECS/Fargate)** | ✅ Via CodePipeline | ✅ Yes | ⭐⭐⭐ Hard |
| **Azure Container Apps** | ✅ Native | ✅ Yes | ⭐⭐ Medium |
| **Vercel** | ✅ Native | ✅ Yes | ⭐ Very Easy (for frontends) |
| **Fly.io** | ✅ Via GitHub Actions | ✅ Yes | ⭐⭐ Medium |

---

## 🚀 Quick Setup by Platform

### 🥇 #1 Railway.app (Easiest - 2 Minutes)

**Setup:**
1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select `brettleehari/BTCExpert` repository
6. Railway auto-detects Dockerfile and deploys!

**Auto-Deploy Configuration:**
```yaml
# Railway automatically deploys on every push to main branch
# No configuration needed! 🎉
```

**Add Services:**
- In Railway dashboard, click "New" → "Database" → "Add PostgreSQL"
- Click "New" → "Database" → "Add Redis"
- Environment variables are automatically injected

**Branch Deployments:**
- Railway can deploy multiple branches (staging, production)
- Each branch gets its own URL
- Set in Railway dashboard: Settings → Environment

---

### 🥈 #2 Render.com (Very Easy - 3 Minutes)

**Setup:**
1. Go to [render.com](https://render.com)
2. Click "New" → "Web Service"
3. Connect GitHub account
4. Select `brettleehari/BTCExpert` repository
5. Configure:
   ```yaml
   Name: cial
   Region: Oregon (US West)
   Branch: main
   Root Directory: cial
   Runtime: Docker
   Plan: Starter ($7/month)
   ```
6. Click "Create Web Service"

**Auto-Deploy:** Enabled by default on push to main

**Add Databases:**
```yaml
# In Render dashboard:
New → PostgreSQL → Name: cial-postgres → Create
New → Redis → Name: cial-redis → Create
```

**Environment Variables:**
```yaml
# In Web Service → Environment tab:
DATABASE_URL: [Copy from PostgreSQL instance]
REDIS_URL: [Copy from Redis instance]
SECRET_KEY: [Generate random 32 chars]
ENVIRONMENT: production
```

**Advanced: render.yaml (Infrastructure as Code)**
```yaml
# Create render.yaml in repo root
services:
  - type: web
    name: cial
    runtime: docker
    repo: https://github.com/brettleehari/BTCExpert
    branch: main
    dockerfilePath: ./cial/Dockerfile
    dockerContext: ./cial
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: cial-postgres
          property: connectionString
      - key: REDIS_URL
        fromDatabase:
          name: cial-redis
          property: connectionString
    healthCheckPath: /health
    autoDeploy: true

databases:
  - name: cial-postgres
    databaseName: cial
    plan: starter

  - name: cial-redis
    plan: starter
```

---

### 🥉 #3 DigitalOcean App Platform (Easy - 5 Minutes)

**Setup via Dashboard:**
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Choose "GitHub" as source
4. Authorize DigitalOcean
5. Select `brettleehari/BTCExpert` repository
6. Select branch: `main`
7. Auto-detected settings:
   ```yaml
   Source Directory: /cial
   Dockerfile: /cial/Dockerfile
   HTTP Port: 8000
   ```
8. Click "Next" → Configure resources → "Launch App"

**Auto-Deploy:** Enabled by default

**Setup via CLI (Faster):**
```bash
# Install doctl
brew install doctl  # macOS
# OR
snap install doctl  # Linux

# Authenticate
doctl auth init

# Create app.yaml
cat > app.yaml <<EOF
name: cial
region: nyc

services:
  - name: api
    github:
      repo: brettleehari/BTCExpert
      branch: main
      deploy_on_push: true
    source_dir: /cial
    dockerfile_path: Dockerfile
    http_port: 8000
    instance_size_slug: professional-xs
    instance_count: 2
    health_check:
      http_path: /health
    envs:
      - key: ENVIRONMENT
        value: production
      - key: SECRET_KEY
        value: your-secret-key-min-32-chars-here
        type: SECRET

databases:
  - name: cial-postgres
    engine: PG
    version: "16"
    size: db-s-1vcpu-1gb

  - name: cial-redis
    engine: REDIS
    version: "7"
    size: db-s-1vcpu-1gb
EOF

# Deploy
doctl apps create --spec app.yaml
```

**Multi-Branch Deployments:**
```yaml
# In app.yaml, add multiple services:
services:
  - name: api-production
    github:
      repo: brettleehari/BTCExpert
      branch: main
      deploy_on_push: true

  - name: api-staging
    github:
      repo: brettleehari/BTCExpert
      branch: develop
      deploy_on_push: true
```

---

### #4 Google Cloud Run (Medium - 10 Minutes)

**Setup via Cloud Build (GitHub Triggers):**

**1. Enable APIs:**
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

**2. Connect GitHub:**
```bash
# Go to: https://console.cloud.google.com/cloud-build/triggers
# Click "Connect Repository"
# Select "GitHub" → Authorize → Select BTCExpert repo
```

**3. Create Build Trigger:**
```bash
# In Cloud Build → Triggers → Create Trigger:
Name: deploy-cial-production
Event: Push to a branch
Source: brettleehari/BTCExpert
Branch: ^main$
Configuration: Cloud Build configuration file
Location: cial/cloudbuild.yaml
```

**4. Create cloudbuild.yaml:**
```yaml
# Create cial/cloudbuild.yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/cial:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/cial:latest'
      - '.'
    dir: 'cial'

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/cial:$COMMIT_SHA'

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/cial:latest'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'cial'
      - '--image'
      - 'gcr.io/$PROJECT_ID/cial:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'
      - '--min-instances'
      - '1'
      - '--max-instances'
      - '10'

options:
  machineType: 'N1_HIGHCPU_8'

timeout: '1200s'
```

**5. Set Secrets:**
```bash
# Store secrets in Secret Manager
echo -n "your-secret-key" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "postgresql://..." | gcloud secrets create DATABASE_URL --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding SECRET_KEY \
  --member=serviceAccount:YOUR-PROJECT@appspot.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

**Auto-Deploy:** Every push to `main` triggers automatic deployment! 🎉

---

### #5 AWS (Hard - 30 Minutes)

**Setup via CodePipeline:**

**1. Create GitHub Connection:**
```bash
# Go to: AWS Console → CodePipeline → Settings → Connections
# Create connection → Select GitHub → Authorize AWS
```

**2. Create ECR Repository:**
```bash
aws ecr create-repository --repository-name cial
```

**3. Create buildspec.yml:**
```yaml
# Create cial/buildspec.yml
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      - REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cial
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}

  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - cd cial
      - docker build -t $REPOSITORY_URI:latest .
      - docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG

  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker images...
      - docker push $REPOSITORY_URI:latest
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo Writing image definitions file...
      - printf '[{"name":"cial","imageUri":"%s"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files: imagedefinitions.json
```

**4. Create CodePipeline:**
```bash
# Go to: AWS CodePipeline → Create Pipeline
Source: GitHub (via connection created above)
Repository: brettleehari/BTCExpert
Branch: main
Build: AWS CodeBuild → Create new project
Deploy: Amazon ECS → Select your ECS cluster and service
```

**Auto-Deploy:** Every push to `main` triggers CodePipeline! 🎉

---

## 🔄 GitHub Actions (Universal Solution)

**Works with ANY platform!**

### Create Workflow File:

```yaml
# Create .github/workflows/deploy.yml
name: Deploy CIAL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11.6'

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          cd cial
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          cd cial
          pytest -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./cial/coverage.xml

  deploy-railway:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        run: railway up --service cial
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  deploy-gcp:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Build and Deploy to Cloud Run
        run: |
          gcloud builds submit --config cial/cloudbuild.yaml cial/

  deploy-digitalocean:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Install doctl
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}

      - name: Deploy to DigitalOcean App Platform
        run: |
          doctl apps create --spec cial/app.yaml

  deploy-aws:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: cial
          IMAGE_TAG: ${{ github.sha }}
        run: |
          cd cial
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster cial-cluster --service cial-api --force-new-deployment
```

### Required GitHub Secrets:

```bash
# Add these in: GitHub Repo → Settings → Secrets and variables → Actions

# For Railway:
RAILWAY_TOKEN

# For Google Cloud:
GCP_SA_KEY  # Service account JSON key

# For DigitalOcean:
DIGITALOCEAN_ACCESS_TOKEN

# For AWS:
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

---

## 🎯 Recommended GitHub Workflow

### Multi-Environment Setup:

```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # 1. Lint and format check
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11.6'
      - run: |
          cd cial
          pip install black ruff mypy
          black --check .
          ruff check .
          mypy .

  # 2. Run tests
  test:
    runs-on: ubuntu-latest
    needs: lint

    services:
      postgres:
        image: pgvector/pgvector:pg16-v0.7.4
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7.2.4-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11.6'
      - run: |
          cd cial
          pip install -r requirements-dev.txt
          pytest -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3

  # 3. Build Docker image
  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: |
          cd cial
          docker build -t cial:${{ github.sha }} .

  # 4. Deploy to staging (develop branch)
  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Staging
        run: |
          # Deploy to staging environment
          echo "Deploying to staging..."

  # 5. Deploy to production (main branch)
  deploy-production:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Production
        run: |
          # Deploy to production environment
          echo "Deploying to production..."
```

---

## 📋 Deployment Comparison

| Feature | Railway | Render | DigitalOcean | Cloud Run | AWS |
|---------|---------|--------|-------------|-----------|-----|
| **Setup Time** | 2 min | 3 min | 5 min | 10 min | 30 min |
| **GitHub UI** | ✅ Excellent | ✅ Excellent | ✅ Good | ⚠️ Manual | ⚠️ Manual |
| **Auto-Deploy** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Preview Deploys** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Manual | ⚠️ Manual |
| **Rollback** | ✅ 1-click | ✅ 1-click | ✅ 1-click | ✅ CLI | ⚠️ Complex |
| **Branch Deploys** | ✅ Easy | ✅ Easy | ✅ Easy | ⚠️ Manual | ⚠️ Manual |
| **Config File** | ❌ Optional | ✅ render.yaml | ✅ app.yaml | ✅ cloudbuild.yaml | ✅ buildspec.yml |

---

## 🎯 Recommendation

**Best GitHub Integration:**

1. **Easiest:** Railway or Render (Zero config, 2-3 minutes)
2. **Best Balance:** DigitalOcean App Platform (Good features, easy setup)
3. **Most Flexible:** GitHub Actions (Works everywhere, full control)
4. **Enterprise:** AWS CodePipeline (Complex but powerful)

**My Suggestion for You:**

```bash
# Option 1: Railway (Fastest)
1. Go to railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select BTCExpert repo
4. Done! Auto-deploys on every push to main

# Option 2: Render (Best Free Tier)
1. Go to render.com
2. New → Web Service → Connect GitHub
3. Select BTCExpert repo
4. Done! Auto-deploys on every push

# Option 3: DigitalOcean (Production)
1. Add app.yaml to repo (I'll create it below)
2. Go to cloud.digitalocean.com/apps
3. Create App → Select GitHub repo
4. Done! Auto-deploys from app.yaml config
```

---

## 📝 Ready-to-Use Config Files

I can create these config files for your repo to enable instant GitHub deployment:

1. `render.yaml` - For Render.com
2. `app.yaml` - For DigitalOcean
3. `cloudbuild.yaml` - For Google Cloud Run
4. `.github/workflows/deploy.yml` - For GitHub Actions
5. `railway.json` - For Railway (optional)

Would you like me to create these files so you can deploy with just one click from GitHub?

---

**Last Updated:** 2025-12-14
