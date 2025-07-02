#!/bin/bash

echo "🚀 LeafLoaf Deployment Status"
echo "============================"

# Check production
echo -e "\n📦 Production:"
gcloud run services describe leafloaf --region=us-central1 --format="value(status.url)" 2>/dev/null || echo "Not deployed yet"

# Check staging environments
echo -e "\n🧪 Staging Environments:"
gcloud run services list --region=us-central1 --format="table(name,status.url)" | grep staging || echo "No staging environments"

# Check recent builds
echo -e "\n🔨 Recent Builds:"
gcloud builds list --limit=3 --format="table(id,status,createTime.date())"

# Check current git branch
echo -e "\n🌿 Current Branch:"
git branch --show-current

# Check if there are uncommitted changes
echo -e "\n📝 Git Status:"
if [[ -z $(git status -s) ]]; then
    echo "✅ Working directory clean"
else
    echo "⚠️  Uncommitted changes present"
fi

echo -e "\n---"
echo "To deploy: git push origin main"
echo "To test: git push origin feature/your-feature"