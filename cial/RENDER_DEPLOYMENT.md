# Render.com Deployment Guide for CIAL

**Step-by-Step Deployment to Render.com**

**Time Required:** 5-10 minutes
**Cost:** FREE for 90 days, then $21/month
**Difficulty:** ⭐ Easy

---

## 🚀 Quick Deployment Steps

### Step 1: Sign Up for Render.com (1 minute)

1. Go to **https://render.com**
2. Click **"Get Started"** or **"Sign Up"**
3. Choose **"Sign in with GitHub"** (easiest)
4. Authorize Render to access your GitHub account

---

### Step 2: Create New Web Service (2 minutes)

1. On Render dashboard, click **"New +"** (top right)
2. Select **"Web Service"**
3. You'll see a list of your GitHub repositories
4. Find **"brettleehari/BTCExpert"** and click **"Connect"**

   > **Note:** If you don't see your repo:
   > - Click "Configure account" to grant Render access to the repo
   > - Or click "+ Connect account" if repo is in different GitHub account

5. Configure the service:
   ```
   Name: cial-api
   Region: Oregon (US West) - or choose closest to you
   Branch: main
   Root Directory: cial
   Runtime: Docker

   Dockerfile Path: ./Dockerfile
   Docker Context: ./

   Instance Type: Starter ($7/month - FREE for 90 days)
   ```

6. Click **"Advanced"** to expand advanced options

7. **Auto-Deploy:** Make sure **"Auto-Deploy"** is set to **"Yes"**
   - This enables deployment on every push to main branch

8. **Health Check Path:** Set to `/health`

9. Click **"Create Web Service"**

---

### Step 3: Add PostgreSQL Database (1 minute)

1. On Render dashboard, click **"New +"**
2. Select **"PostgreSQL"**
3. Configure:
   ```
   Name: cial-postgres
   Database: cial
   User: cial (auto-generated)
   Region: Oregon (same as web service)
   PostgreSQL Version: 16
   Plan: Starter (FREE for 90 days)
   ```
4. Click **"Create Database"**

5. **Wait 2-3 minutes** for database to provision

---

### Step 4: Add Redis Database (1 minute)

1. On Render dashboard, click **"New +"**
2. Select **"Redis"**
3. Configure:
   ```
   Name: cial-redis
   Region: Oregon (same as web service)
   Plan: Starter (FREE for 90 days)
   Maxmemory Policy: allkeys-lru
   ```
4. Click **"Create Redis"**

5. **Wait 1-2 minutes** for Redis to provision

---

### Step 5: Connect Databases to Web Service (2 minutes)

1. Go back to your **"cial-api"** web service
2. Click **"Environment"** tab in left sidebar
3. Click **"Add Environment Variable"**

4. **Add PostgreSQL connection:**

   Click the dropdown to the right of "Add Environment Variable"
   - Select **"cial-postgres"**
   - It will auto-populate:
     - `DATABASE_URL` → Connection string
     - `POSTGRES_HOST` → Host
     - `POSTGRES_PORT` → Port
     - `POSTGRES_DB` → Database name
     - `POSTGRES_USER` → Username
     - `POSTGRES_PASSWORD` → Password

5. **Add Redis connection:**

   Click the dropdown again
   - Select **"cial-redis"**
   - It will auto-populate:
     - `REDIS_URL` → Connection string
     - `REDIS_HOST` → Host
     - `REDIS_PORT` → Port

6. **Add required environment variables manually:**

   Click **"Add Environment Variable"** and add each:

   ```
   ENVIRONMENT = production
   DEBUG = false
   API_VERSION = 1.0

   # Generate a secure secret key (32+ random characters)
   SECRET_KEY = [Click "Generate" button or paste your own]

   # Kafka (optional - use Upstash or CloudKarafka, or leave empty for now)
   KAFKA_BOOTSTRAP_SERVERS = (leave empty for now)

   # Rate limiting
   RATE_LIMIT_REQUESTS = 100
   RATE_LIMIT_PERIOD = 60
   ```

7. Click **"Save Changes"**

---

### Step 6: Deploy! (Automatic)

1. Render will **automatically start building and deploying** your app
2. You'll see the build logs in real-time
3. Build takes **5-10 minutes** (first time)

**What's happening:**
```
→ Cloning repository from GitHub
→ Building Docker image
→ Installing Python 3.11.6 and dependencies
→ Starting CIAL application
→ Running health checks
→ Deployment complete! ✅
```

---

### Step 7: Verify Deployment (1 minute)

1. Once deployment completes, you'll see **"Live"** status with a green dot

2. At the top of the page, you'll see your app URL:
   ```
   https://cial-api-XXXXX.onrender.com
   ```

3. **Test the API:**
   - Click the URL to open in browser
   - You should see the CIAL landing page or:
   - Add `/health` to the URL: `https://cial-api-XXXXX.onrender.com/health`
   - Should return:
     ```json
     {
       "status": "healthy",
       "timestamp": "2025-12-14T...",
       "version": "1.0"
     }
     ```

4. **Test API docs:**
   - Go to: `https://cial-api-XXXXX.onrender.com/docs`
   - You should see the FastAPI Swagger UI

---

## 🎉 Success! Your CIAL is Live

**Your app is now deployed at:** `https://cial-api-XXXXX.onrender.com`

**What happens now:**
- ✅ Every push to `main` branch auto-deploys
- ✅ SSL certificate automatically configured
- ✅ Health checks running every 30 seconds
- ✅ Logs available in Render dashboard
- ✅ FREE for 90 days!

---

## 🔧 Post-Deployment Configuration

### Optional: Add Custom Domain

1. Go to **"Settings"** tab in your web service
2. Scroll to **"Custom Domains"**
3. Click **"Add Custom Domain"**
4. Enter your domain: `api.yourdomain.com`
5. Add the CNAME record to your DNS:
   ```
   CNAME api → cial-api-XXXXX.onrender.com
   ```
6. Render will automatically provision SSL certificate

---

### Optional: Add API Keys

If you want to use external services (CoinGecko, Sentry, etc.):

1. Go to **"Environment"** tab
2. Click **"Add Environment Variable"**
3. Add:
   ```
   COINGECKO_API_KEY = your-api-key-here
   SENTRY_DSN = your-sentry-dsn-here
   ```
4. Click **"Save Changes"**
5. Service will automatically redeploy

---

### Optional: Add Kafka (for full functionality)

CIAL uses Kafka for event streaming. Render doesn't provide managed Kafka, so you have options:

#### Option 1: Upstash Kafka (Recommended - Serverless)

1. Go to **https://upstash.com**
2. Create account (free tier available)
3. Create Kafka cluster
4. Copy connection string
5. In Render, add environment variable:
   ```
   KAFKA_BOOTSTRAP_SERVERS = your-kafka-endpoint:9092
   ```

#### Option 2: CloudKarafka (Free tier)

1. Go to **https://www.cloudkarafka.com**
2. Create account
3. Create free Kafka instance
4. Copy connection details
5. Add to Render environment variables

#### Option 3: Skip Kafka (for testing)

For initial testing, you can run without Kafka. The app will log warnings but still work for basic operations.

---

## 📊 Monitoring & Debugging

### View Logs

1. Go to your **"cial-api"** service
2. Click **"Logs"** tab
3. See real-time logs streaming
4. Use search/filter to find specific logs

**CLI access:**
```bash
# Install Render CLI
npm install -g render

# View logs
render logs cial-api --tail

# Follow logs (live)
render logs cial-api --tail -f
```

---

### Shell Access

1. In your service dashboard, click **"Shell"** tab
2. Opens a terminal directly in your container
3. Run commands:
   ```bash
   # Check Python version
   python --version

   # Run migrations (if needed)
   python manage.py migrate

   # Check Redis connection
   python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"

   # Check database connection
   python -c "import asyncpg; print('DB connected')"
   ```

---

### Check Metrics

1. Click **"Metrics"** tab
2. See:
   - CPU usage
   - Memory usage
   - Request rate
   - Response times
   - Error rates

---

### Health Checks

1. Click **"Events"** tab
2. See all health check results
3. Configure alerts if health check fails

---

## 🐳 One-Command Deployments with Docker Hub Images

Our CI pipeline now publishes the `cial` image to Docker Hub. Instead of letting Render build the image from source, you can instruct Render to pull that pre-built artifact via `scripts/render-deploy.sh`.

### Why this is faster

- ✅ Avoids slow Docker builds inside Render
- ✅ Guarantees production matches the image validated in CI
- ✅ Works for multiple services at once (looped inside the script)

### One-time setup

1. In the Render dashboard, open your service → **Settings** → set **Auto Deploy** to **No** (or apply the provided `render.yaml`, which already sets `autoDeploy: false`).
2. Copy each service ID from the Render URL or from **Deploys → Manual Deploy** (`srv-xxxxxxxx` format).
3. Generate a Render API key (Dashboard → Account Settings → API Keys). Give it deploy scope.

### Running the script

```bash
export RENDER_API_KEY="<your-render-api-key>"
export RENDER_SERVICE_IDS="srv-abc123 srv-def456"  # one or multiple services
export DOCKER_IMAGE_REPO="docker.io/brettleehari/cial"
export IMAGE_TAG="$(git rev-parse --short HEAD)"   # or latest

./scripts/render-deploy.sh
```

The script will:

1. Call the Render Deploy API for each service ID.
2. Tell Render to pull `docker.io/brettleehari/cial:${IMAGE_TAG}`.
3. Leave your dashboard build logs clean—Render just pulls and runs.

Monitor progress in the Render UI exactly as before (Events → Deploys). If anything fails, logs and health checks continue to work the same way.

## 🚀 Auto-Deploy Setup (Legacy GitHub Builds)

If you still prefer Render to build from source, you can re-enable auto-deploy:

```bash
git add .
git commit -m "Update feature X"
git push origin main

# Render automatically:
# → Detects push
# → Pulls latest code
# → Builds Docker image
# → Deploys new version
# → Runs health checks
# → Switches traffic to new version
```

**Zero downtime deployments either way!**

---

## 💰 Pricing

### Starter Plan (Current)

**FREE for 90 days**, then:

```
Web Service (cial-api):      $7/month
PostgreSQL (cial-postgres):  $7/month
Redis (cial-redis):          $7/month
─────────────────────────────────────
Total:                       $21/month
```

**Included:**
- ✅ 512 MB RAM
- ✅ 0.5 CPU
- ✅ Auto-scaling (up to 1 instance)
- ✅ Free SSL
- ✅ Auto-deploy from GitHub
- ✅ 100 GB bandwidth/month

---

### Upgrade to Standard (Optional)

When you need more resources:

```
Web Service (standard):      $25/month
PostgreSQL (standard):       $25/month
Redis (standard):            $25/month
─────────────────────────────────────
Total:                       $75/month
```

**Upgrades:**
- ✅ 2 GB RAM
- ✅ 2 CPU cores
- ✅ Auto-scaling (multiple instances)
- ✅ 1 TB bandwidth/month
- ✅ Priority support

---

## 🔄 Making Updates

### Deploy Code Changes

```bash
# Make your changes locally
nano infrastructure/caching.py

# Test locally
cd cial
./start.sh development

# Commit and push
git add .
git commit -m "Improve caching layer"
git push origin main

# Render automatically deploys! 🚀
# Check status in Render dashboard
```

---

### Rollback to Previous Version

1. Go to **"Events"** tab in your service
2. Find the deployment you want to rollback to
3. Click **"Rollback"** button
4. Confirm rollback
5. Done! Takes ~1 minute

---

## 🐛 Troubleshooting

### Build Fails

**Check build logs:**
1. Go to **"Logs"** tab
2. Select the failed build
3. Look for error messages

**Common issues:**
- Missing dependencies → Check `requirements.txt`
- Docker build errors → Check `Dockerfile`
- Port conflicts → Ensure app runs on port 8000

---

### App Crashes After Deploy

**Check runtime logs:**
1. Go to **"Logs"** tab
2. Look for Python errors
3. Common issues:
   - Missing environment variables
   - Database connection errors
   - Redis connection errors

**Fix:**
- Verify all environment variables are set
- Check database connection strings
- Ensure databases are running (green status)

---

### Database Connection Errors

**Symptoms:**
- App logs show "connection refused"
- Health check fails

**Fix:**
1. Go to database service (cial-postgres or cial-redis)
2. Check status (should be green "Available")
3. If suspended (inactive), it will auto-resume
4. Verify connection strings in environment variables

---

### Slow First Request (Cold Start)

**Symptom:** First request after inactivity takes 30+ seconds

**Why:** Render spins down free-tier services after 15 min of inactivity

**Solutions:**
- Upgrade to paid plan (stays always on)
- Use health check pings to keep warm
- Set up external monitoring (UptimeRobot, etc.)

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure:

- [x] GitHub repo is accessible to Render
- [x] `render.yaml` is in repo root (✅ Already there!)
- [x] `Dockerfile` is in `cial/` directory (✅ Already there!)
- [x] Port 8000 is exposed in Dockerfile (✅ Already configured!)
- [x] Health check endpoint `/health` works (✅ Already implemented!)
- [ ] All sensitive values moved to environment variables (check .env.example)
- [ ] Database migrations are handled (if any)

---

## 🎯 Next Steps After Deployment

### 1. Test All Endpoints

Use the Swagger UI at: `https://your-app.onrender.com/docs`

Test key endpoints:
- `GET /health` - Health check
- `GET /api/v1/intelligence/sources` - List data sources
- `POST /api/v1/cache/warm` - Warm cache
- `GET /api/v1/database/health` - Check database

---

### 2. Set Up Monitoring

**Render Monitoring:**
- Already enabled! Check "Metrics" tab

**External Monitoring (optional):**
- **UptimeRobot** (free): https://uptimerobot.com
  - Monitor: `https://your-app.onrender.com/health`
  - Get alerts if down

- **Sentry** (error tracking): https://sentry.io
  - Add `SENTRY_DSN` environment variable
  - Already integrated in code!

---

### 3. Configure Alerts

1. In Render dashboard, go to **"Settings"**
2. Scroll to **"Notifications"**
3. Add your email for alerts:
   - Deploy failures
   - Service crashes
   - Health check failures

---

### 4. Set Up Backups

**PostgreSQL backups (automatic):**
- Render automatically backs up your database daily
- Retention: 7 days (free tier)
- Restore from "Backups" tab in database service

**Manual backup:**
```bash
# Get database connection string from Render
pg_dump $DATABASE_URL > backup.sql

# Restore later
psql $DATABASE_URL < backup.sql
```

---

## 🔐 Security Checklist

- [x] SSL/TLS enabled automatically by Render ✅
- [ ] Change default SECRET_KEY (Render auto-generates)
- [ ] Set up rate limiting (already configured in code)
- [ ] Enable API key authentication for production
- [ ] Review CORS settings in `main.py`
- [ ] Set up firewall rules (Render handles this)
- [ ] Enable 2FA on Render account
- [ ] Review database access (only accessible from your services)

---

## 📞 Support

**Render Support:**
- Dashboard: Chat icon (bottom right)
- Community: https://community.render.com
- Docs: https://render.com/docs
- Status: https://status.render.com

**CIAL Issues:**
- GitHub: https://github.com/brettleehari/BTCExpert/issues
- Documentation: See README.md

---

## 🎉 You're Done!

Your CIAL application is now:
- ✅ Deployed to production
- ✅ Running on Render.com
- ✅ Auto-deploying from GitHub
- ✅ Using managed PostgreSQL 16
- ✅ Using managed Redis 7
- ✅ Free for 90 days!
- ✅ Secured with SSL
- ✅ Monitored with health checks

**Your app URL:** `https://cial-api-XXXXX.onrender.com`

**API docs:** `https://cial-api-XXXXX.onrender.com/docs`

---

**Last Updated:** 2025-12-14
**Questions?** Check PLATFORM_COMPARISON.md or DEPLOYMENT_GUIDE.md
