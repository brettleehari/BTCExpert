# Render Deployment Troubleshooting Guide

## Current Issue: Secret Name Conflict

### Error Details
```
Create database cial-redis: ❌ (secret name already in use: user-gcs-key)
Create web service cial-api: ❌ (canceled: another action failed)
Create database cial-postgres: ⏳ (running)
```

### Root Cause
Render has leftover resources (secrets) from a previous Blueprint deployment attempt. The Blueprint is trying to create resources that already exist.

---

## Solution 1: Fresh Blueprint Deployment (Recommended)

### Step 1: Delete Existing Blueprint
1. Go to https://dashboard.render.com/
2. Click on **Blueprints** in the left sidebar
3. Find the **CIAL** blueprint (ID: `exs-d52n2omr433s73cbjok0`)
4. Click the **⋮** (three dots) menu
5. Select **Delete Blueprint**
6. Confirm deletion

### Step 2: Clean Up Orphaned Resources
1. Go to **Dashboard** → **Services**
2. Delete any orphaned services:
   - `cial-api` (if exists)
   - `cial-postgres` (if exists)
   - `cial-redis` (if exists)

### Step 3: Deploy Fresh Blueprint
Click the deploy button:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/brettleehari/BTCExpert)

**Or** use the Render Dashboard:
1. Go to **Blueprints** → **New Blueprint**
2. Connect to repository: `brettleehari/BTCExpert`
3. Branch: `main`
4. Render will automatically detect `render.yaml`
5. Click **Apply**

---

## Solution 2: Manual Secret Cleanup (Alternative)

If you want to keep the existing Blueprint:

### Step 1: Delete Conflicting Secret
1. Go to https://dashboard.render.com/
2. Click **Environment** in the left sidebar
3. Find and delete the secret: `user-gcs-key`

### Step 2: Retry Blueprint Sync
1. Go to **Blueprints** → **CIAL**
2. Click **Manual sync** button (top right)
3. This will retry creating the failed resources

---

## Solution 3: Use Existing Resources (Advanced)

If you have existing databases you want to reuse:

### Step 1: Identify Existing Resources
```bash
# List all your Render services
curl -H "Authorization: Bearer $RENDER_API_KEY" \
  https://api.render.com/v1/services
```

### Step 2: Update render.yaml to Reference Existing Resources
Instead of creating new databases, reference existing ones:

```yaml
services:
  - type: web
    name: cial-api
    envVars:
      - key: DATABASE_URL
        fromService:
          type: pserv
          name: existing-postgres-service-id  # Replace with actual ID
          property: connectionString
```

---

## Prevention: Avoid Duplicate Deployments

### Best Practices
1. **One Blueprint per Repository**: Only create one Blueprint for BTCExpert
2. **Use Manual Sync**: Use "Manual sync" button instead of creating new Blueprints
3. **Check Existing Resources**: Before deploying, check if resources already exist
4. **Clean Up Failed Deployments**: Always delete failed Blueprints completely

---

## Verification After Deployment

### Step 1: Check All Services Are Running
```bash
# Check web service
curl https://cial-api.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0",
  "timestamp": "2025-12-19T15:30:00Z"
}
```

### Step 2: Check Database Connections
1. Go to **Blueprints** → **CIAL**
2. Click on **cial-postgres** → should show "Available"
3. Click on **cial-redis** → should show "Available"
4. Click on **cial-api** → should show "Live"

### Step 3: Check Logs
```bash
# View service logs
1. Dashboard → Services → cial-api
2. Click **Logs** tab
3. Look for:
   ✅ "Application startup complete"
   ✅ "Connected to PostgreSQL"
   ✅ "Connected to Redis"
   ❌ Any ERROR or CRITICAL messages
```

---

## Common Errors and Fixes

### Error: "Branch main could not be found"
**Fix**: Create main branch or update render.yaml to use existing branch
```bash
git checkout -b main
git push -u origin main
```

### Error: "Plans require payment"
**Fix**: Ensure all plans are set to `free` in render.yaml
```yaml
plan: free  # NOT 'starter' or 'standard'
```

### Error: "Dockerfile not found at ./cial/Dockerfile"
**Fix**: Verify Dockerfile exists
```bash
ls -la cial/Dockerfile
```

### Error: "Health check failed"
**Fix**: Check application logs for startup errors
1. Verify DATABASE_URL and REDIS_URL are set correctly
2. Check application is binding to `0.0.0.0:8000` (not localhost)
3. Ensure /health endpoint exists and returns 200

---

## Getting Help

### Render Support
- Documentation: https://render.com/docs
- Community: https://community.render.com/
- Support: support@render.com

### Check Render Status
- Status page: https://status.render.com/
- Incidents may affect deployments

### Debug Checklist
- [ ] Blueprint deleted completely
- [ ] All orphaned services deleted
- [ ] No conflicting secrets exist
- [ ] render.yaml is valid (check syntax)
- [ ] Branch 'main' exists in repository
- [ ] Dockerfile exists at cial/Dockerfile
- [ ] All plans set to 'free'
- [ ] Health check endpoint exists (/health)

---

## Next Steps After Successful Deployment

1. **Test API Endpoints**
   ```bash
   curl https://cial-api.onrender.com/docs
   ```

2. **Set Up Custom Domain** (Optional)
   - Dashboard → Services → cial-api → Settings → Custom Domains

3. **Enable Monitoring** (Optional)
   - Add Sentry DSN to environment variables
   - Set up UptimeRobot to prevent service sleep

4. **Upgrade to Paid Plans** (When Ready)
   - Update render.yaml plans to 'starter'
   - Commit and push to trigger auto-deploy

---

**Last Updated**: 2025-12-19
**Render Blueprint ID**: exs-d52n2omr433s73cbjok0
**Repository**: brettleehari/BTCExpert
**Branch**: main
