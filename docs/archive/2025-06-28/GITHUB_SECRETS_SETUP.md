# GitHub Secrets Setup Instructions

## Step 1: Add GitHub Secrets

Go to: https://github.com/adeetya02/LeafLoafLangGraph/settings/secrets/actions

Click "New repository secret" and add these two secrets:

### Secret 1: GCP_PROJECT_ID
**Name:** `GCP_PROJECT_ID`  
**Value:** `leafloafai`

### Secret 2: GCP_SA_KEY
**Name:** `GCP_SA_KEY`  
**Value:** Run this command in your terminal and copy the ENTIRE output:
```bash
cat /tmp/leafloaf-key.json | base64
```

## Step 2: Create GitHub Personal Access Token (for Cloud Build)

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "LeafLoaf Cloud Build"
4. Select scopes:
   - repo (all)
   - write:repo_hook
5. Generate token and SAVE IT (you won't see it again)

## Step 3: Connect GitHub to Cloud Build

Run this command with your token:
```bash
gcloud builds repositories create github \
  --connection=leafloaf-github \
  --region=us-central1 \
  --github-token=YOUR_GITHUB_TOKEN_HERE \
  --repository=https://github.com/adeetya02/LeafLoafLangGraph \
  --name=LeafLoafLangGraph
```

## Step 4: Verify Setup

### Test GitHub Actions (Recommended)
```bash
# Create a test branch
git checkout -b test/cicd-setup
git push origin test/cicd-setup

# This should trigger:
# 1. Tests in GitHub Actions
# 2. Staging deployment
# 3. You'll see the staging URL in GitHub Actions logs
```

### Test Cloud Build (Alternative)
```bash
# Manually trigger a build
gcloud builds submit --config=cloudbuild-enhanced.yaml
```

## Step 5: First Production Deployment

```bash
# After testing, merge to main
git checkout main
git merge test/cicd-setup
git push origin main

# This triggers:
# 1. All tests run
# 2. Docker image builds
# 3. Canary deployment (10% traffic)
# 4. Wait 5 minutes
# 5. Full deployment (100% traffic)
```

## Deployment URLs

### Production
- Main URL: https://leafloaf-xxx.run.app
- Canary URL: https://canary---leafloaf-xxx.run.app

### Staging (Feature Branches)
- Pattern: https://leafloaf-staging-{branch-name}-xxx.run.app
- Example: https://leafloaf-staging-feature-personalization-xxx.run.app

## Monitoring Deployments

### GitHub Actions
- Go to: https://github.com/adeetya02/LeafLoafLangGraph/actions
- Click on the workflow run to see progress

### Cloud Build
```bash
# List recent builds
gcloud builds list --limit=5

# Watch a build in progress
gcloud builds log [BUILD_ID] --stream
```

### Cloud Run
```bash
# Check production status
gcloud run services describe leafloaf --region=us-central1

# Check staging environments
gcloud run services list --region=us-central1 | grep staging
```

## Rollback Instructions

### Quick Rollback (Traffic Switch)
```bash
# List all revisions
gcloud run revisions list --service=leafloaf --region=us-central1

# Switch traffic to previous revision
gcloud run services update-traffic leafloaf \
  --region=us-central1 \
  --to-revisions=leafloaf-00002-abc=100
```

### Deploy Previous Version
```bash
# Find the commit SHA you want
git log --oneline -10

# Deploy that specific version
gcloud run deploy leafloaf \
  --image=gcr.io/leafloafai/leafloaf:COMMIT_SHA \
  --region=us-central1
```

## Cleanup Old Staging Environments

```bash
# List all services
gcloud run services list --region=us-central1

# Delete old staging services
gcloud run services delete leafloaf-staging-old-feature \
  --region=us-central1 \
  --quiet
```

## Troubleshooting

### If deployment fails:
1. Check GitHub Actions logs
2. Check Cloud Build logs: `gcloud builds list`
3. Check Cloud Run logs: `gcloud run services describe leafloaf`

### Common issues:
- **Tests failing**: Fix tests locally first
- **Permission denied**: Check service account permissions
- **Image not found**: Check Container Registry
- **Timeout**: Increase timeout in cloudbuild.yaml

---

Ready to deploy! 🚀