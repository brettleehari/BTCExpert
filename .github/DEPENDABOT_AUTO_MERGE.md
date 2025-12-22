# Dependabot Auto-Merge Configuration

This repository is configured with **automated Dependabot PR merging** for safe dependency updates.

## How It Works

### 1. **Dependabot Creates PRs** (`dependabot.yml`)
- Runs weekly every Monday at 9:00 AM
- Checks for updates to:
  - Python dependencies (`/cial`)
  - Docker images (`/cial`)
  - GitHub Actions (root directory)
- Groups minor/patch updates together to reduce PR noise

### 2. **Auto-Merge Workflow** (`dependabot-auto-merge.yml`)

When Dependabot opens a PR, the workflow automatically:

#### ✅ **Auto-Approval**
- Automatically approves the PR using GitHub's auto-approve action

#### 🔄 **Auto-Merge Logic**
The workflow enables auto-merge with smart rules:

| Update Type | Auto-Merge | Behavior |
|------------|-----------|----------|
| **Patch** (1.2.3 → 1.2.4) | ✅ Yes | Merges automatically after CI passes |
| **Minor** (1.2.3 → 1.3.0) | ✅ Yes | Merges automatically after CI passes |
| **Major** (1.2.3 → 2.0.0) | ⚠️ No | Requires manual review, adds comment |
| **Security** | ✅ Yes | Merges with high priority label |

#### 🏷️ **Automatic Labeling**
- `auto-mergeable` - Safe for automatic merge
- `major-update` - Requires manual review
- `needs-review` - Major version changes
- `security` - Security vulnerability fixes
- `priority: high` - Security-related updates

### 3. **Merge After CI Passes**
- PRs only merge after **all CI checks pass**:
  - ✅ Linting (Black, Ruff)
  - ✅ Security scan (Bandit)
  - ✅ Tests (pytest with 50% coverage)
  - ✅ Docker build
- If CI fails, PR remains open for manual inspection

## Configuration Files

### `.github/dependabot.yml`
```yaml
# Configures what Dependabot monitors
- Python packages in /cial
- Docker images in /cial
- GitHub Actions in root
```

### `.github/workflows/dependabot-auto-merge.yml`
```yaml
# Workflow that handles auto-merge logic
- Auto-approves Dependabot PRs
- Enables auto-merge for safe updates
- Adds labels for tracking
```

## Customization Options

### To Disable Auto-Merge

**Option 1: Disable entire workflow**
```bash
# Rename or delete the workflow file
mv .github/workflows/dependabot-auto-merge.yml \
   .github/workflows/dependabot-auto-merge.yml.disabled
```

**Option 2: Disable for specific packages**
Add to `dependabot.yml`:
```yaml
- package-ecosystem: "pip"
  directory: "/cial"
  ignore:
    - dependency-name: "package-name"
      update-types: ["version-update:semver-major"]
```

### To Change Merge Strategy

Edit `.github/workflows/dependabot-auto-merge.yml`:
```yaml
# Current: Squash merge
gh pr merge "$PR_NUMBER" --auto --squash --delete-branch

# Options:
# --merge     (creates merge commit)
# --rebase    (rebases and merges)
# --squash    (squashes commits, default)
```

### To Adjust Security

For more control, update the workflow to:
1. Require specific CI jobs to pass
2. Wait for additional approvals
3. Add Slack/email notifications

Example:
```yaml
- name: Wait for required checks
  uses: lewagon/wait-on-check-action@v1.3.1
  with:
    ref: ${{ github.event.pull_request.head.sha }}
    check-name: 'lint,security,test'
    repo-token: ${{ secrets.GITHUB_TOKEN }}
```

## Security Considerations

### ✅ **Safe**
- Only runs on PRs from `dependabot[bot]` (verified GitHub actor)
- Requires all CI checks to pass before merging
- Major version updates require manual review
- You can always override by manually reviewing/merging

### ⚠️ **Important Notes**
1. **Review major updates manually** - Breaking changes may occur
2. **Monitor the first few auto-merges** - Verify CI catches issues
3. **Security updates merge automatically** - This is intentional for fast patching
4. **Branch protection rules apply** - Auto-merge respects repository settings

## Monitoring

### View Auto-Merged PRs
```bash
# List merged Dependabot PRs
gh pr list --state merged --label dependabot --limit 20

# View auto-merge workflow runs
gh run list --workflow=dependabot-auto-merge.yml
```

### Check for Failed Auto-Merges
```bash
# PRs that couldn't auto-merge (likely CI failures)
gh pr list --label dependabot --state open
```

## Troubleshooting

### Auto-Merge Not Working?

1. **Check workflow permissions**
   ```yaml
   # Ensure these are set in dependabot-auto-merge.yml
   permissions:
     contents: write
     pull-requests: write
   ```

2. **Verify branch protection**
   - Go to: Settings → Branches → Branch protection rules
   - Ensure "Allow auto-merge" is enabled
   - Check required status checks are passing

3. **Check actor identity**
   ```bash
   # Workflow only runs for dependabot[bot]
   if: github.actor == 'dependabot[bot]'
   ```

4. **Review workflow logs**
   ```bash
   gh run list --workflow=dependabot-auto-merge.yml --limit 5
   gh run view <run-id> --log
   ```

### Manual Override

To prevent a specific PR from auto-merging:
```bash
# Disable auto-merge for a PR
gh pr merge <PR-NUMBER> --disable-auto

# Or add the "needs-review" label
gh pr edit <PR-NUMBER> --add-label "needs-review"
```

## Best Practices

1. **Start Conservative**
   - First few weeks: Monitor auto-merges closely
   - Gradually increase trust as CI proves reliable

2. **Keep CI Fast**
   - Auto-merge works best with quick CI (<10 min)
   - Slow CI delays security updates

3. **Regular Audits**
   ```bash
   # Weekly: Review what got auto-merged
   gh pr list --state merged --label dependabot \
     --search "merged:>=$(date -d '7 days ago' +%Y-%m-%d)"
   ```

4. **Emergency Rollback**
   ```bash
   # If an auto-merged update breaks production
   git revert <commit-sha>
   git push origin main
   ```

## Resources

- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [Auto-merge PRs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)
- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication)

## Questions?

- **Why auto-merge?** Keeps dependencies up-to-date automatically, reducing security vulnerabilities
- **Is it safe?** Yes, with proper CI coverage (tests, linting, security scans)
- **Can I disable it?** Yes, rename/delete the workflow or disable per-package
- **What if CI fails?** PR stays open for manual review
- **Major updates?** Never auto-merge, always require manual review

---

**Status**: ✅ Active and monitoring
**Last Updated**: 2025-12-22
