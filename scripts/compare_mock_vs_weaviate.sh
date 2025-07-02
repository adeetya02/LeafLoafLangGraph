#!/bin/bash
# Compare performance between mock data and real Weaviate

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 LeafLoaf Mock vs Weaviate Performance Comparison${NC}"
echo "===================================================="

SERVICE_URL=$(gcloud run services describe leafloaf \
    --region northamerica-northeast1 \
    --format="value(status.url)")

# Test queries for comparison
declare -a queries=(
    "Oatly Barista Edition"
    "organic milk"
    "breakfast cereals"
    "vegan cheese"
    "gluten free bread"
)

# Function to test a query and return latency
test_query() {
    local query=$1
    local start=$(date +%s%N)
    
    curl -s -X POST $SERVICE_URL/api/v1/search \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"session_id\": \"compare-test\"}" \
        -o /dev/null
    
    local end=$(date +%s%N)
    echo $(( ($end - $start) / 1000000 ))
}

# Test in current mode
echo -e "\n${YELLOW}📊 Testing in current mode...${NC}"
CURRENT_MODE=$(gcloud run services describe leafloaf \
    --region northamerica-northeast1 \
    --format="value(spec.template.spec.containers[0].env[?(@.name=='TEST_MODE')].value)")

echo "Current TEST_MODE: $CURRENT_MODE"
echo ""

# Collect mock results
declare -A mock_results
for query in "${queries[@]}"; do
    latency=$(test_query "$query")
    mock_results["$query"]=$latency
    echo -e "Mock: \"$query\" - ${GREEN}${latency}ms${NC}"
done

# Ask to switch to production
echo -e "\n${YELLOW}Ready to test with real Weaviate?${NC}"
echo "This will switch to production mode (TEST_MODE=false)"
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Comparison cancelled"
    exit 0
fi

# Switch to production
echo -e "\n${YELLOW}Switching to production mode...${NC}"
gcloud run services update leafloaf \
    --region northamerica-northeast1 \
    --update-env-vars "TEST_MODE=false" \
    --quiet

echo "Waiting for service to update..."
sleep 30

# Test with Weaviate
echo -e "\n${YELLOW}📊 Testing with real Weaviate...${NC}"
declare -A weaviate_results
for query in "${queries[@]}"; do
    latency=$(test_query "$query")
    weaviate_results["$query"]=$latency
    echo -e "Weaviate: \"$query\" - ${GREEN}${latency}ms${NC}"
done

# Generate comparison report
echo -e "\n${BLUE}📈 COMPARISON REPORT${NC}"
echo "===================="
printf "%-30s %10s %10s %10s\n" "Query" "Mock" "Weaviate" "Difference"
echo "------------------------------------------------------------"

total_mock=0
total_weaviate=0
count=0

for query in "${queries[@]}"; do
    mock_lat=${mock_results["$query"]}
    weaviate_lat=${weaviate_results["$query"]}
    diff=$((weaviate_lat - mock_lat))
    
    if [ $diff -gt 0 ]; then
        diff_str="+${diff}ms"
    else
        diff_str="${diff}ms"
    fi
    
    printf "%-30s %10sms %10sms %10s\n" "$query" "$mock_lat" "$weaviate_lat" "$diff_str"
    
    total_mock=$((total_mock + mock_lat))
    total_weaviate=$((total_weaviate + weaviate_lat))
    count=$((count + 1))
done

echo "------------------------------------------------------------"
avg_mock=$((total_mock / count))
avg_weaviate=$((total_weaviate / count))
avg_diff=$((avg_weaviate - avg_mock))

printf "%-30s %10sms %10sms %10sms\n" "AVERAGE" "$avg_mock" "$avg_weaviate" "+$avg_diff"

# Calculate percentage increase
percent_increase=$((avg_diff * 100 / avg_mock))
echo -e "\n${YELLOW}Performance Impact: ${percent_increase}% increase in latency${NC}"

# Switch back to test mode
echo -e "\n${YELLOW}Switching back to test mode...${NC}"
gcloud run services update leafloaf \
    --region northamerica-northeast1 \
    --update-env-vars "TEST_MODE=true" \
    --quiet

echo -e "\n${GREEN}✅ Comparison complete!${NC}"
echo ""
echo "Key Findings:"
echo "- Mock data average: ${avg_mock}ms"
echo "- Weaviate average: ${avg_weaviate}ms"
echo "- Average increase: ${avg_diff}ms (${percent_increase}%)"
echo ""
echo "Note: Weaviate provides real product data and better search relevance"
echo "The latency increase is expected and acceptable for production use"