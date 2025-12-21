# CI/CD Pipeline Setup Guide
## Docker Hub + GitHub Actions + Render --- Flow

This guide sets up a complete CI/CD pipeline that builds Docker images in GitHub Actions, pushes to Docker Hub, and deploys to Render.

---

## Architecture

```
PR Merge to main
    ↓
GitHub Actions
    ├── Build Docker Image
    ├── Test Imports (catch errors early!)
    ├── Security Scan (Trivy)
    ├── Push to Docker Hub
    └── Trigger Render Deploy
        ↓
Render pulls image from Docker Hub
    ↓
Deployment Success ✅
```

---

## Setup Steps

### 1. Create Docker Hub Account & Repository

1. Go to https://hub.docker.com/
2. Create account (if you don't have one)
3. Create repository: **Settings** → **Repositories** → **Create Repository**
   - Name: `cial`
   - Visibility: Public (or Private if you have Pro)
4. Create Access Token:
   - Click your profile → **Account Settings** → **Security**
   - **New Access Token**
   - Name: `github-actions`
   - Permissions: **Read, Write, Delete**
   - **Copy the token** (you won't see it again!)

---

### 2. Add GitHub Secrets

1. Go to your GitHub repository: `https://github.com/brettleehari/BTCExpert`
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add these:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | e.g., `brettleehari` |
| `DOCKERHUB_TOKEN` | Token from step 1 | e.g., `dckr_pat_...` |
| `RENDER_DEPLOY_HOOK_URL` | (Optional) From Render dashboard | Triggers deploy |

**To get Render Deploy Hook**:
- Render Dashboard → Service → **Settings** → **Deploy Hook**
- Copy the URL

---

### 3. Update Render Configuration

**Option A: Keep Building on Render** (Current - simpler)
- Keep using current `render.yaml`
- GitHub Actions just tests the build
- Render still builds from source

**Option B: Use Docker Hub Image** (Recommended - faster, more reliable)
- Use `render-dockerhub.yaml` instead of `render.yaml`
- Update Docker Hub username in the file
- Rename: `mv render-dockerhub.yaml render.yaml`
- Render pulls pre-built image (no build on Render!)

---

### 4. Test the Pipeline

1. **Make a change** (e.g., update README.md)
2. **Create PR**:
   ```bash
   git checkout -b test-cicd
   echo "# CI/CD Test" >> README.md
   git add README.md
   git commit -m "Test CI/CD pipeline"
   git push origin test-cicd
   ```
3. **Create Pull Request** on GitHub
4. **Merge PR** to main
5. **Watch GitHub Actions**:
   - Go to **Actions** tab
   - See "Build and Push Docker Image" workflow running
   - Check each step:
     - ✅ Build Docker image
     - ✅ Test imports (catches logging errors!)
     - ✅ Security scan
     - ✅ Push to Docker Hub
     - ✅ Trigger Render deploy

---

## What This Solves

### Before (Problems):
❌ Build errors discovered during Render deployment (too late!)
❌ Import errors crash at runtime
❌ No version control of Docker images
❌ Slow deployments (build every time)
❌ Hard to debug build issues

### After (Benefits):
✅ Build tested in CI before deployment
✅ Import errors caught immediately (in GitHub Actions)
✅ Versioned Docker images on Docker Hub
✅ Fast deployments (pull pre-built image)
✅ Easy to rollback (just use old image tag)
✅ Security scanning built-in
✅ Can test locally with same image

---

## How It Catches Errors Early

### Example: The Logging Error We Had

**Before CI/CD**:
```
1. Merge code to main
2. Render starts building
3. Build succeeds
4. App starts
5. ❌ Import fails: AttributeError: 'BoundLogger' object has no attribute 'WARNING'
6. Deployment fails after 10 minutes
```

**With CI/CD**:
```
1. Create PR
2. GitHub Actions builds Docker image
3. ❌ Import test fails immediately
4. PR shows red X - don't merge!
5. Fix the error
6. Push fix
7. GitHub Actions green ✅
8. Merge PR
9. Render deploys successfully
```

---

## Docker Image Tags

The workflow creates multiple tags for each build:

| Tag | Description | Example |
|-----|-------------|---------|
| `latest` | Latest main branch | `cial:latest` |
| `main-abc1234` | Main branch + SHA | `cial:main-a1b2c3d` |
| `v1.0.0` | Semantic version | `cial:v1.0.0` |

**Usage**:
```bash
# Pull latest
docker pull YOUR_USERNAME/cial:latest

# Pull specific version
docker pull YOUR_USERNAME/cial:main-abc1234

# Run locally
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  YOUR_USERNAME/cial:latest
```

---

## Monitoring

### GitHub Actions Logs
- **Actions** tab → **Build and Push Docker Image**
- See detailed logs for each step
- Download artifacts if needed

### Docker Hub
- https://hub.docker.com/r/YOUR_USERNAME/cial
- See all image versions
- Check image size, last pushed, etc.

### Render
- Dashboard → Service → **Events**
- See deployment triggered by webhook
- Logs show: "Pulling image from Docker Hub"

---

## Troubleshooting

### Build Fails in GitHub Actions

**Check the logs**:
1. GitHub → **Actions** → Failed workflow
2. Click failed job
3. Expand failing step
4. See error details

**Common issues**:
- Missing dependency in requirements.txt → Add it
- Import error → Fix import
- Docker build error → Check Dockerfile

### Image Push Fails

**Check Docker Hub credentials**:
```bash
# Test locally
docker login
docker tag cial YOUR_USERNAME/cial:test
docker push YOUR_USERNAME/cial:test
```

**Check GitHub secrets**:
- Settings → Secrets → Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`

### Render Doesn't Auto-Deploy

**Option 1: Manual Deploy Hook**
```bash
curl -X POST "https://api.render.com/deploy/srv-..."
```

**Option 2: Manual Deploy**
- Render Dashboard → Service → **Manual Deploy** → **Deploy latest commit**

---

## Cost Comparison

| Platform | Current (Build on Render) | With Docker Hub |
|----------|---------------------------|-----------------|
| GitHub Actions | Free (2000 min/month) | Free (2000 min/month) |
| Docker Hub | N/A | Free (1 private repo) |
| Render Build Time | ~5 minutes | ~10 seconds (pull image) |
| Render Bandwidth | 100GB/month (free tier) | 100GB/month (free tier) |

**Total Cost**: Still FREE! ✅

**Benefits**:
- 30x faster deployments (pull vs build)
- Catch errors earlier
- Better version control

---

## Rollback Procedure

### With Docker Hub (Easy!)

**Render Dashboard**:
1. Settings → **Image**
2. Change tag from `latest` to previous version: `main-abc1234`
3. Save → Deploys old version instantly

**Or via render.yaml**:
```yaml
image:
  url: docker.io/YOUR_USERNAME/cial:main-abc1234  # Old working version
```

### Without Docker Hub (Current)
1. Git revert
2. Wait for build (~5 minutes)
3. Deploy

---

## Next Steps

1. ✅ **Set up Docker Hub account**
2. ✅ **Add GitHub secrets**
3. ✅ **Merge code to main** (triggers first build)
4. ✅ **Watch GitHub Actions** (see the magic happen!)
5. ✅ **Optional: Switch to Docker Hub deployment** (update render.yaml)

---

## FAQ

**Q: Do I need to pay for Docker Hub?**
A: No! Free plan includes unlimited public repositories and 1 private repository.

**Q: Will GitHub Actions cost money?**
A: No! Free plan includes 2000 minutes/month. Our builds use ~2 minutes each.

**Q: Can I still build locally?**
A: Yes! The Dockerfile hasn't changed. `docker build -t cial .` still works.

**Q: What if I want to test before merging?**
A: The workflow runs on PR merge. You can also trigger it manually:
   - GitHub → Actions → Build and Push → Run workflow

**Q: Can I use GitLab CI or other CI/CD?**
A: Yes! The concepts are the same. Just adapt the `.github/workflows/` file to your CI platform.

---

## File Structure

```
BTCExpert/
├── .github/
│   └── workflows/
│       └── docker-build-push.yml    # ← GitHub Actions workflow
├── cial/
│   ├── Dockerfile                   # ← Same Dockerfile
│   └── ...
├── render.yaml                      # ← Current (builds from source)
├── render-dockerhub.yaml            # ← Alternative (uses Docker Hub)
└── CI_CD_SETUP_GUIDE.md            # ← This file
```

---

**Ready to Deploy**: ✅ Yes - Just add GitHub secrets and merge!

**Support**: If you have issues, check GitHub Actions logs first - they're very detailed.
