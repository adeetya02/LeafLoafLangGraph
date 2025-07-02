#!/bin/bash
# LeafLoaf Mode Switcher - Easy environment variable updates for Cloud Run
# Usage: ./switch_modes.sh [mode]

set -e

# Configuration
SERVICE_NAME="leafloaf"
REGION="northamerica-northeast1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 LeafLoaf Mode Switcher${NC}"
echo "=========================="

# Function to update environment variables
update_env() {
    local env_vars=$1
    local description=$2
    
    echo -e "\n${YELLOW}Switching to: ${description}${NC}"
    echo "Updating environment variables: $env_vars"
    
    gcloud run services update $SERVICE_NAME \
        --region $REGION \
        --update-env-vars "$env_vars" \
        --quiet
    
    echo -e "${GREEN}✅ Update complete!${NC}"
}

# Function to show current configuration
show_current() {
    echo -e "\n${BLUE}📊 Current Configuration:${NC}"
    gcloud run services describe $SERVICE_NAME \
        --region $REGION \
        --format="table(spec.template.spec.containers[0].env[name,value])" 2>/dev/null | grep -E "TEST_MODE|FAST_MODE|ENVIRONMENT" || echo "No relevant env vars found"
}

# Main menu
case "$1" in
    "dev")
        update_env "TEST_MODE=true,FAST_MODE=false,ENVIRONMENT=development" "Development Mode (Mock Data + Zephyr LLM)"
        echo -e "${YELLOW}📝 Using mock data and HuggingFace Zephyr-7B${NC}"
        ;;
        
    "prod")
        update_env "TEST_MODE=false,FAST_MODE=false,ENVIRONMENT=production" "Production Mode (Weaviate + Gemma 2 9B)"
        echo -e "${YELLOW}📝 Using real Weaviate data and Vertex AI Gemma 2 9B${NC}"
        echo -e "${RED}⚠️  Make sure Weaviate credits are available!${NC}"
        ;;
        
    "fast")
        update_env "TEST_MODE=false,FAST_MODE=true,ENVIRONMENT=production" "Fast Production Mode (Weaviate + Pattern Matching)"
        echo -e "${YELLOW}📝 Using real Weaviate data with instant pattern matching (no LLM)${NC}"
        echo -e "${GREEN}⚡ Sub-50ms response times!${NC}"
        ;;
        
    "test-prod")
        update_env "TEST_MODE=true,FAST_MODE=false,ENVIRONMENT=production" "Test Production Mode (Mock Data + Gemma 2 9B)"
        echo -e "${YELLOW}📝 Using mock data with Vertex AI Gemma 2 9B${NC}"
        echo -e "${BLUE}🧪 Good for testing Gemma without Weaviate credits${NC}"
        ;;
        
    "current"|"status")
        show_current
        echo -e "\n${BLUE}🔗 Service URL:${NC}"
        gcloud run services describe $SERVICE_NAME \
            --region $REGION \
            --format="value(status.url)"
        ;;
        
    "logs")
        echo -e "${BLUE}📜 Viewing logs...${NC}"
        gcloud run logs tail $SERVICE_NAME --region $REGION
        ;;
        
    "test")
        echo -e "${BLUE}🧪 Testing deployment...${NC}"
        SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
            --region $REGION \
            --format="value(status.url)")
        
        echo -e "\n${YELLOW}Testing /health endpoint...${NC}"
        curl -s $SERVICE_URL/health | jq .
        
        echo -e "\n${YELLOW}Testing /api/v1/search endpoint...${NC}"
        curl -s -X POST $SERVICE_URL/api/v1/search \
            -H "Content-Type: application/json" \
            -d '{"query": "organic milk", "session_id": "mode-test"}' | jq .
        ;;
        
    *)
        echo "Usage: $0 [mode]"
        echo ""
        echo "Available modes:"
        echo "  dev        - Development Mode (Mock Data + Zephyr LLM)"
        echo "  prod       - Production Mode (Weaviate + Gemma 2 9B)"
        echo "  fast       - Fast Production Mode (Weaviate + Pattern Matching)"
        echo "  test-prod  - Test Production Mode (Mock Data + Gemma 2 9B)"
        echo ""
        echo "Other commands:"
        echo "  current    - Show current configuration"
        echo "  status     - Same as current"
        echo "  logs       - Tail service logs"
        echo "  test       - Test the deployment"
        echo ""
        echo "Examples:"
        echo "  $0 dev      # Switch to development mode"
        echo "  $0 prod     # Switch to full production mode"
        echo "  $0 fast     # Switch to fast mode (no LLM)"
        echo "  $0 current  # See current settings"
        
        show_current
        ;;
esac

echo -e "\n${GREEN}Done!${NC}"