# CI/CD Setup Guide for LeafLoaf

## Overview
This guide explains how to set up automatic deployment from GitHub to Google Cloud Platform (GCP).

## Two Options Available

### Option 1: GitHub Actions (Recommended)
- Tests run on GitHub's infrastructure
- Deploys to GCP on successful tests
- Free for public repos, limited minutes for private
- Better integration with GitHub features (PR comments, etc.)

### Option 2: Cloud Build
- Tests and builds run on GCP
- More control over build environment
- Better for complex builds
- Costs based on build time

## Quick Setup

### Prerequisites
- GCP Project with billing enabled
- GitHub repository
- `gcloud` CLI installed locally

### Automatic Setup
```bash
# Run the setup script
./setup-cicd.sh
```

This script will:
1. Enable required GCP APIs
2. Create service accounts
3. Set up Cloud Build triggers
4. Provide instructions for GitHub secrets

## Manual Setup

### 1. Enable GCP APIs
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Create Service Account
```bash
# Create service account
gcloud iam service-accounts create leafloaf-sa \
  --display-name="LeafLoaf Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.developer"

# Create key for GitHub Actions
gcloud iam service-accounts keys create key.json \
  --iam-account=leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### 3. Set up GitHub Secrets
1. Go to GitHub repo → Settings → Secrets
2. Add these secrets:
   - `GCP_PROJECT_ID`: Your GCP project ID
   - `GCP_SA_KEY`: Contents of key.json (base64 encoded)

### 4. Choose Deployment Method

#### GitHub Actions
- Push `.github/workflows/deploy-to-gcp.yml` to repo
- Deployments trigger on push to main

#### Cloud Build
- Connect GitHub repo to Cloud Build
- Use `cloudbuild-enhanced.yaml`
- Set up triggers for main and feature branches

## Deployment Flow

### Production (main branch)
1. Push to main triggers build
2. Tests run automatically
3. If tests pass, Docker image builds
4. Canary deployment (10% traffic)
5. Monitor for 5 minutes
6. Full deployment if healthy

### Staging (feature branches)
1. Push to feature/* creates staging environment
2. Unique URL for testing
3. Automatically cleaned up on PR merge

### Pull Requests
1. Tests run on every PR
2. Staging environment created
3. URL posted as PR comment
4. Environment deleted when PR closed

## Features

### 🧪 Automatic Testing
- All 49 personalization tests run before deploy
- Deployment blocked if tests fail
- Test results uploaded as artifacts

### 🚀 Zero-Downtime Deployments
- Canary deployments for production
- Traffic gradually shifted
- Automatic rollback on errors

### 🔄 Multiple Environments
- Production: main branch
- Staging: feature branches
- PR previews: automatic URLs

### 📊 Monitoring
- Post-deployment health checks
- Performance validation
- Error monitoring

## Configuration

### Environment Variables
Set in Cloud Run deployment:
- `SPANNER_INSTANCE_ID`: Spanner instance
- `SPANNER_DATABASE_ID`: Database name
- `GCP_PROJECT_ID`: Project ID
- `ENVIRONMENT`: production/staging

### Resource Allocation
Production:
- Memory: 2Gi
- CPU: 2
- Concurrency: 100

Staging:
- Memory: 1Gi
- CPU: 1
- Concurrency: 50

## Troubleshooting

### Build Fails
1. Check Cloud Build logs:
   ```bash
   gcloud builds list --limit=5
   gcloud builds log [BUILD_ID]
   ```

2. Common issues:
   - Tests failing
   - Missing dependencies in requirements.txt
   - Docker build errors

### Deployment Fails
1. Check Cloud Run logs:
   ```bash
   gcloud run services describe leafloaf --region=us-central1
   ```

2. Common issues:
   - Service account permissions
   - Environment variables missing
   - Resource limits too low

### Slow Deployments
- Use Docker layer caching
- Optimize Docker image size
- Parallel test execution

## Best Practices

1. **Always test locally first**
   ```bash
   python run_all_personalization_tests.py
   ```

2. **Use feature branches**
   - Automatic staging deployments
   - Test before merging to main

3. **Monitor deployments**
   - Watch canary metrics
   - Check error rates
   - Validate performance

4. **Clean up resources**
   - Delete old staging environments
   - Remove unused Docker images

## Cost Optimization

1. **Cloud Build**
   - First 120 minutes/day free
   - Use smaller machine types for staging

2. **Cloud Run**
   - Scales to zero when unused
   - Use minimum instances wisely

3. **Container Registry**
   - Set up lifecycle policies
   - Delete old images regularly

## Security

1. **Service Account**
   - Minimum required permissions
   - Rotate keys regularly

2. **Secrets Management**
   - Use Secret Manager for sensitive data
   - Never commit secrets to repo

3. **Network Security**
   - Use VPC connector if needed
   - Restrict Cloud Run ingress

## Next Steps

1. Run `./setup-cicd.sh`
2. Configure GitHub secrets
3. Push to main branch
4. Monitor first deployment
5. Celebrate! 🎉

---

For help: Check Cloud Build logs or GitHub Actions tab