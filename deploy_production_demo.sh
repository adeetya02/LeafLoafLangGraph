#!/bin/bash

# LeafLoaf Production Deployment Script
# Deploys both backend and frontend to Google Cloud Run

set -e

echo "🚀 Starting LeafLoaf Production Deployment..."

# Configuration
PROJECT_ID="leafloafai"
REGION="us-central1"
BACKEND_SERVICE="leafloaf-api-prod"
FRONTEND_SERVICE="leafloaf-frontend-prod"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Building Backend Docker Image...${NC}"
gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/${BACKEND_SERVICE} \
  --project ${PROJECT_ID} \
  .

echo -e "${GREEN}✅ Backend image built successfully${NC}"

echo -e "${BLUE}📦 Building Frontend Docker Image...${NC}"
cd frontend
gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE} \
  --project ${PROJECT_ID} \
  .
cd ..

echo -e "${GREEN}✅ Frontend image built successfully${NC}"

echo -e "${BLUE}🚀 Deploying Backend to Cloud Run...${NC}"
gcloud run deploy ${BACKEND_SERVICE} \
  --image gcr.io/${PROJECT_ID}/${BACKEND_SERVICE} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 100 \
  --max-instances 10 \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID}"

# Get backend URL
BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo -e "${GREEN}✅ Backend deployed at: ${BACKEND_URL}${NC}"

echo -e "${BLUE}🚀 Deploying Frontend to Cloud Run...${NC}"
gcloud run deploy ${FRONTEND_SERVICE} \
  --image gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --concurrency 100 \
  --max-instances 10 \
  --set-env-vars="API_HOST=${BACKEND_URL#https://}"

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo -e "${GREEN}✅ Frontend deployed at: ${FRONTEND_URL}${NC}"

echo -e "${YELLOW}🎉 Deployment Complete!${NC}"
echo -e "${YELLOW}📱 Frontend URL: ${FRONTEND_URL}${NC}"
echo -e "${YELLOW}🔧 Backend API: ${BACKEND_URL}${NC}"
echo -e "${YELLOW}📊 API Docs: ${BACKEND_URL}/docs${NC}"
echo -e "${YELLOW}🔍 Health Check: ${BACKEND_URL}/health${NC}"

# Test the deployment
echo -e "${BLUE}🧪 Testing deployment...${NC}"
curl -s ${BACKEND_URL}/health | jq .

echo -e "${GREEN}✨ LeafLoaf is ready for production!${NC}"
echo -e "${GREEN}Share this URL with users: ${FRONTEND_URL}${NC}"