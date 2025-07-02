#!/bin/bash

echo "🎤 LeafLoaf Google Voice Setup Script"
echo "===================================="

# Check if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ Detected macOS"
fi

# Step 1: Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   brew install google-cloud-sdk"
    echo "   OR"
    echo "   Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
else
    echo "✅ gcloud CLI found"
fi

# Step 2: Check authentication
echo ""
echo "📋 Checking Google Cloud authentication..."

# Option 1: Use Application Default Credentials (ADC)
echo ""
echo "Option 1: Using Application Default Credentials (Recommended for development)"
echo "Run this command to authenticate:"
echo ""
echo "  gcloud auth application-default login"
echo ""
echo "This will open a browser for authentication."

# Option 2: Service Account Key
echo ""
echo "Option 2: Using Service Account Key (Recommended for production)"
echo ""
echo "1. Create a service account in Google Cloud Console"
echo "2. Download the JSON key file"
echo "3. Set the environment variable:"
echo ""
echo "  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/your/service-account-key.json'"
echo ""

# Step 3: Enable required APIs
echo "📋 Required Google Cloud APIs:"
echo "- Cloud Speech-to-Text API"
echo "- Cloud Text-to-Speech API"
echo ""
echo "Enable them with:"
echo ""
echo "  gcloud services enable speech.googleapis.com"
echo "  gcloud services enable texttospeech.googleapis.com"
echo ""

# Step 4: Test authentication
echo "📋 Testing authentication..."
python3 -c "
import os
try:
    # Try ADC first
    from google.auth import default
    credentials, project = default()
    print(f'✅ Found credentials for project: {project}')
except Exception as e:
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print(f'❌ Service account key set but invalid: {os.environ.get(\"GOOGLE_APPLICATION_CREDENTIALS\")}')
    else:
        print('❌ No authentication found. Please run: gcloud auth application-default login')
"

# Step 5: Create .env.yaml entry
echo ""
echo "📋 Add to your .env.yaml file (if using service account):"
echo ""
echo "GOOGLE_APPLICATION_CREDENTIALS: '/path/to/your/service-account-key.json'"
echo "GCP_PROJECT_ID: 'your-project-id'"
echo "GCP_LOCATION: 'us-central1'"
echo ""

# Step 6: Quick test
echo "📋 Quick voice test commands:"
echo ""
echo "# Test imports and basic functionality"
echo "python3 test_voice_google_unified.py"
echo ""
echo "# Start the server"
echo "python3 run.py"
echo ""
echo "# Then open: http://localhost:8000/static/voice_google_test.html"