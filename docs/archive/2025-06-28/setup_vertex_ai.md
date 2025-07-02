# Setting up Gemma 2 9B on Vertex AI

## Prerequisites
1. GCP Project: `leafloafai`
2. Enable Vertex AI API
3. Set up authentication

## Steps to Enable Gemma 2 9B

### 1. Enable Vertex AI API
```bash
gcloud services enable aiplatform.googleapis.com
```

### 2. Set up Application Default Credentials
```bash
gcloud auth application-default login
```

### 3. Test Gemma 2 9B Access
```bash
# Test if Gemma 2 is available in Model Garden
gcloud ai models list --region=us-central1 | grep gemma
```

### 4. Update Environment Variables
Make sure `.env.yaml` has:
```yaml
GCP_PROJECT_ID: "leafloafai"
GCP_LOCATION: "us-central1"
```

### 5. For Local Development
Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
# OR use gcloud auth
gcloud auth application-default login
```

## Testing the Integration

Run the test script:
```bash
python3 test_vertex_gemma.py
```