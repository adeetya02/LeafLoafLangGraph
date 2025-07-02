#!/bin/bash

echo "🚀 Deploying Dietary Intelligence Feature"
echo "========================================"

# Step 1: Authenticate with GitHub (if not already done)
echo "Step 1: Authenticating with GitHub..."
gh auth status || gh auth login --web

# Step 2: Push the feature branch
echo -e "\nStep 2: Pushing feature branch..."
git push -u origin feature/dietary-cultural-intelligence

# Step 3: Create the Pull Request
echo -e "\nStep 3: Creating Pull Request..."
gh pr create \
  --title "feat: Add Dietary & Cultural Intelligence (Feature #6)" \
  --body-file FEATURE_DIETARY_INTELLIGENCE_PR.md \
  --base main \
  --head feature/dietary-cultural-intelligence \
  --label "feature,enhancement,tested"

# Step 4: Auto-merge the PR (since you want to approve it)
echo -e "\nStep 4: Setting up auto-merge..."
# Get the PR number
PR_NUMBER=$(gh pr list --head feature/dietary-cultural-intelligence --json number -q '.[0].number')

if [ -n "$PR_NUMBER" ]; then
    echo "PR #$PR_NUMBER created successfully!"
    
    # Enable auto-merge (will merge once checks pass)
    echo "Enabling auto-merge for PR #$PR_NUMBER..."
    gh pr merge $PR_NUMBER --auto --merge
    
    # View the PR
    echo -e "\nPR URL:"
    gh pr view $PR_NUMBER --web
    
    # Monitor the deployment
    echo -e "\nMonitoring GitHub Actions..."
    gh run list --limit 1
    
    echo -e "\n✅ Done! The PR will auto-merge once all checks pass."
    echo "GitHub Actions will deploy to staging automatically."
else
    echo "❌ Failed to get PR number"
fi