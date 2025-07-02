#\!/bin/bash

echo "=========================================================================="
echo "🔍 LEAFLOAF PERFORMANCE TEST - ALPHA VALUES AND COMPONENT BREAKDOWN"
echo "Timestamp: $(date)"
echo "=========================================================================="

BASE_URL="http://localhost:8080/api/v1/search"

# Function to test a query
test_query() {
    local query="$1"
    local description="$2"
    
    echo -e "\n📝 Testing: $query ($description)"
    
    # Make the request and capture response
    response=$(curl -s -X POST "$BASE_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"session_id\": \"test-$(date +%s)\"}" \
        -w "\n{\"network_time\": %{time_total}}")
    
    # Extract metrics using jq
    echo "$response" | jq -r '
        if .execution then
            "   Intent: \(.conversation.intent // "unknown")
   Alpha: \(.metadata.search_config.alpha // 0)
   Total server time: \(.execution.total_time_ms // 0)ms
   Network time: \((.network_time // 0) * 1000)ms
   
   Component breakdown:
     - Supervisor: \(.execution.agent_timings.supervisor // 0)ms
     - Product Search: \(.execution.agent_timings.product_search // 0)ms
     - Order Agent: \(.execution.agent_timings.order_agent // 0)ms
     - Response Compiler: \(.execution.agent_timings.response_compiler // 0)ms
   
   Cache info: \(.execution.reasoning_steps[0] // "No cache info")
   Products found: \(.products | length)"
        else
            "   Error: Failed to get response"
        end
    '
}

echo -e "\n🏷️  BRAND-SPECIFIC QUERIES (Expected Alpha: 0.1-0.3)"
echo "--------------------------------------------------------------------------"
test_query "oatly barista" "Brand + Product"
test_query "horizon organic" "Brand Name"

echo -e "\n📦 PRODUCT CATEGORY QUERIES (Expected Alpha: 0.4-0.6)"
echo "--------------------------------------------------------------------------"
test_query "organic milk" "Category + Attribute"
test_query "bell peppers" "Specific Product"
test_query "spinach" "Single Product"

echo -e "\n🔍 EXPLORATORY QUERIES (Expected Alpha: 0.7-0.9)"
echo "--------------------------------------------------------------------------"
test_query "breakfast ideas" "Meal Ideas"
test_query "healthy snacks" "Category Browse"

echo -e "\n🛒 CART OPERATIONS (No Search Required)"
echo "--------------------------------------------------------------------------"
test_query "add to cart" "Add Item"
test_query "show my cart" "List Cart"
test_query "remove that" "Remove Item"

echo -e "\n🧪 COMPLEX QUERIES"
echo "--------------------------------------------------------------------------"
test_query "organic oatly milk for coffee" "Brand + Attributes + Use"
test_query "what vegetables do you have" "Question Format"

echo -e "\n=========================================================================="
echo "✅ Test Complete"
echo "=========================================================================="
