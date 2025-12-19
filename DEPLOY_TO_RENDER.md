# One-Click Deployment to Render.com

**Deploy CIAL with a single click - PostgreSQL, Redis, and app automatically created!**

---

## 🚀 Option 1: One-Click Web Deploy (Easiest - 2 Minutes)

### Click This Button:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/brettleehari/BTCExpert)

**What happens when you click:**
1. Opens Render.com (sign in with GitHub)
2. Reads `render.yaml` from your repo
3. **Automatically creates:**
   - ✅ PostgreSQL 16 database (cial-postgres)
   - ✅ Redis 7 cache (cial-redis)
   - ✅ CIAL API web service (cial-api)
   - ✅ All environment variables connected
   - ✅ Auto-deploy configured
4. Starts deployment (5-10 min)
5. **Done!** Your app is live 🎉

**Cost:** FREE for 90 days, then $21/month

---

## 🚀 Option 2: One-Command CLI Deploy (3 Minutes)

### Prerequisites:
```bash
# Install Node.js (if not installed)
# macOS:
brew install node

# Linux:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows:
# Download from: https://nodejs.org/
```

### Deploy Command:

```bash
# 1. Install Render CLI
npm install -g @render/cli

# 2. Login to Render
render login
# Opens browser - sign in with GitHub

# 3. Deploy everything!
render blueprint launch
# Render reads render.yaml and creates everything
# Takes 5-10 minutes

# 4. Check status
render services list

# 5. View your app
render open cial-api
```

**That's it!** All services created automatically.

---

## 🎯 What Gets Created Automatically

When you deploy with either option above, Render automatically creates:

### 1. Web Service: `cial-api`
```
Type: Docker container
Region: Oregon (US West)
Instance: Starter (512MB RAM, 0.5 CPU)
Cost: $7/month (FREE 90 days)
URL: https://cial-api-XXXXX.onrender.com
Health Check: /health
Auto-deploy: On push to main
```

### 2. Database: `cial-postgres`
```
Type: PostgreSQL 16
Size: 1GB storage
Region: Oregon
Cost: $7/month (FREE 90 days)
Features: Daily backups, automatic patches
```

### 3. Cache: `cial-redis`
```
Type: Redis 7
Size: 256MB
Region: Oregon
Cost: $7/month (FREE 90 days)
Policy: allkeys-lru
```

### 4. Environment Variables (Auto-configured)
```
✅ DATABASE_URL → Connected to cial-postgres
✅ REDIS_URL → Connected to cial-redis
✅ SECRET_KEY → Auto-generated secure key
✅ ENVIRONMENT → production
✅ DEBUG → false
✅ All database connection details
```

**Total:** $21/month after 90-day free trial

---

## ✅ Verify Deployment

After deployment completes:

### Check Services Status:
```bash
render services list
# Should show 3 services, all "Live" (green)
```

### Test Your API:
```bash
# Get your app URL
render services list | grep cial-api

# Test health endpoint
curl https://cial-api-XXXXX.onrender.com/health

# Should return:
# {"status":"healthy","timestamp":"...","version":"1.0"}
```

### Open API Docs:
```bash
# Open in browser
render open cial-api

# Or visit manually:
# https://cial-api-XXXXX.onrender.com/docs
```

---

## 🔧 Post-Deployment (Optional)

### View Logs:
```bash
# Web service logs
render logs cial-api --tail

# Database logs
render logs cial-postgres --tail

# All services
render logs --all
```

### Shell Access:
```bash
# SSH into your app container
render shell cial-api

# Run commands:
python --version
pip list
curl localhost:8000/health
```

### Add Environment Variables:
```bash
# Add API keys or other secrets
render env set cial-api COINGECKO_API_KEY=your-key-here
render env set cial-api SENTRY_DSN=your-dsn-here

# Service auto-redeploys with new variables
```

---

## 🔄 Auto-Deploy is Active

From now on, every push to `main` branch automatically deploys:

```bash
git add .
git commit -m "Add new feature"
git push origin main

# Render automatically:
# → Detects push to main
# → Builds Docker image
# → Deploys new version
# → Runs health checks
# → Zero downtime deployment! 🚀
```

---

## 📊 Monitoring

### Dashboard:
```
1. Go to: https://dashboard.render.com
2. See all services at a glance
3. Click any service for:
   - Logs
   - Metrics (CPU, RAM, requests)
   - Deployment history
   - Shell access
```

### CLI:
```bash
# Service status
render services list

# Recent deploys
render deploys list cial-api

# Metrics
render metrics cial-api

# Events
render events cial-api
```

---

## 🐛 Troubleshooting

### Build Fails?
```bash
# Check build logs
render logs cial-api --deploy

# Common issues:
# - Docker build errors → Check Dockerfile
# - Missing dependencies → Check requirements.txt
```

### App Won't Start?
```bash
# Check runtime logs
render logs cial-api --tail

# Common issues:
# - Port not 8000 → Check Dockerfile EXPOSE
# - Missing env vars → Check render.yaml
# - Database connection → Check DATABASE_URL
```

### Database Connection Errors?
```bash
# Check database status
render services list | grep postgres

# Should show "Available" status
# If "Suspended", it auto-resumes on first connection
```

---

## 💰 Cost Breakdown

### Free Tier (90 Days):
```
Web Service:    $0
PostgreSQL:     $0
Redis:          $0
────────────────────
Total:          $0/month × 3 months = FREE!
```

### After 90 Days:
```
Web Service:    $7/month
PostgreSQL:     $7/month
Redis:          $7/month
────────────────────
Total:          $21/month
```

### Upgrade to Standard (Optional):
```
Web Service:    $25/month (2GB RAM, 2 CPU)
PostgreSQL:     $25/month (10GB storage)
Redis:          $25/month (1GB)
────────────────────
Total:          $75/month
```

---

## 🔐 Security Notes

**Automatically Configured:**
- ✅ SSL/TLS certificates (free)
- ✅ HTTPS enforcement
- ✅ Private database networking
- ✅ Secure environment variables
- ✅ DDoS protection
- ✅ Automatic security patches

**You Should:**
- ✅ Enable 2FA on Render account
- ✅ Rotate SECRET_KEY periodically
- ✅ Set up custom domain with DNS
- ✅ Enable rate limiting (already in code!)
- ✅ Add API key authentication for production

---

## 🎯 Quick Commands Reference

```bash
# Deploy
render blueprint launch

# View services
render services list

# View logs
render logs cial-api --tail

# Shell access
render shell cial-api

# Add environment variable
render env set cial-api KEY=value

# Restart service
render restart cial-api

# Rollback deployment
render rollback cial-api

# Scale instances
render scale cial-api --instances 2

# Open app in browser
render open cial-api

# Get app URL
render services get cial-api --format url
```

---

## 🚀 Alternative: Local Testing First

Want to test locally before deploying?

```bash
# Already works with one command!
cd cial
./start.sh production

# Test at:
http://localhost:8000
http://localhost:8000/docs
http://localhost:8000/health
```

---

## 📞 Need Help?

**Render Support:**
- Dashboard: Chat icon (bottom right)
- Docs: https://render.com/docs/infrastructure-as-code
- Community: https://community.render.com

**CIAL Documentation:**
- Full guide: `cial/RENDER_DEPLOYMENT.md`
- Platform comparison: `cial/PLATFORM_COMPARISON.md`
- GitHub deployment: `cial/GITHUB_DEPLOYMENT.md`

---

## ✅ Summary

**One-Click Deploy:**
```
Click button → Sign in → Wait 5-10 min → LIVE! 🎉
```

**One-Command Deploy:**
```bash
render blueprint launch
```

**What You Get:**
- ✅ Full CIAL stack deployed
- ✅ PostgreSQL 16 + Redis 7
- ✅ SSL/HTTPS automatic
- ✅ Auto-deploy from GitHub
- ✅ FREE for 90 days

**Next Deploy:**
```bash
git push origin main  # Auto-deploys! 🚀
```

---

**Last Updated:** 2025-12-14
**Questions?** Just ask!
