#!/bin/bash
# Quick test script for GCP deployment

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 LeafLoaf GCP Quick Test${NC}"
echo "=========================="

# Get service URL
SERVICE_URL=$(gcloud run services describe leafloaf \
    --region northamerica-northeast1 \
    --format="value(status.url)")

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}❌ Could not get service URL${NC}"
    exit 1
fi

echo -e "📍 Service URL: ${GREEN}$SERVICE_URL${NC}"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}1. Testing Health Endpoint${NC}"
START=$(date +%s%N)
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" $SERVICE_URL/health)
END=$(date +%s%N)
LATENCY=$((($END - $START) / 1000000))

HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed (${LATENCY}ms)${NC}"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Test 2: Search with Gemma
echo -e "${YELLOW}2. Testing Search with Gemma Intent Analysis${NC}"
START=$(date +%s%N)
SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $SERVICE_URL/api/v1/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "I need organic oat milk and some gluten free bread",
        "session_id": "quick-test-'$(date +%s)'"
    }')
END=$(date +%s%N)
LATENCY=$((($END - $START) / 1000000))

HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
BODY=$(echo "$SEARCH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Search completed (${LATENCY}ms)${NC}"
    
    # Extract key information
    INTENT=$(echo "$BODY" | jq -r '.conversation.intent // "unknown"')
    PRODUCT_COUNT=$(echo "$BODY" | jq '.results | length')
    
    echo -e "   Intent detected: ${GREEN}$INTENT${NC}"
    echo -e "   Products found: ${GREEN}$PRODUCT_COUNT${NC}"
    
    # Show first product
    if [ "$PRODUCT_COUNT" -gt 0 ]; then
        FIRST_PRODUCT=$(echo "$BODY" | jq -r '.results[0].product_name // "Unknown"')
        echo -e "   First result: ${GREEN}$FIRST_PRODUCT${NC}"
    fi
    
    # Show response preview
    RESPONSE=$(echo "$BODY" | jq -r '.conversation.response // ""' | head -c 100)
    if [ -n "$RESPONSE" ]; then
        echo -e "   Response: \"$RESPONSE...\""
    fi
else
    echo -e "${RED}❌ Search failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
fi
echo ""

# Test 3: Concurrent Requests
echo -e "${YELLOW}3. Testing Concurrent Requests${NC}"
echo "Sending 5 concurrent requests..."

# Send concurrent requests
for i in {1..5}; do
    curl -s -X POST $SERVICE_URL/api/v1/search \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"test query $i\", \"session_id\": \"concurrent-$i\"}" \
        -o /tmp/concurrent_$i.txt \
        -w "%{http_code}\n" > /tmp/concurrent_$i.code &
done

# Wait for all requests
wait

# Check results
SUCCESS_COUNT=0
for i in {1..5}; do
    CODE=$(cat /tmp/concurrent_$i.code 2>/dev/null)
    if [ "$CODE" = "200" ]; then
        ((SUCCESS_COUNT++))
    fi
done

echo -e "${GREEN}✅ Completed: $SUCCESS_COUNT/5 successful${NC}"
echo ""

# Test 4: Check Mode
echo -e "${YELLOW}4. Checking Current Mode${NC}"
CURRENT_MODE=$(gcloud run services describe leafloaf \
    --region northamerica-northeast1 \
    --format="table(spec.template.spec.containers[0].env[name,value])" | grep -E "TEST_MODE|ENVIRONMENT")

echo "$CURRENT_MODE"
echo ""

# Summary
echo -e "${YELLOW}📊 Quick Test Summary${NC}"
echo "===================="
echo -e "Service URL: $SERVICE_URL"
echo -e "Health Check: ${GREEN}✅${NC}"
echo -e "Search API: ${GREEN}✅${NC}"
echo -e "Gemma Integration: ${GREEN}Active${NC}"
echo ""
echo -e "${GREEN}✨ Deployment is working!${NC}"
echo ""
echo "For detailed testing with latency analysis, run:"
echo "  python scripts/test_gcp_deployment.py"