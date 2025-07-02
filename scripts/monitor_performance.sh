#!/bin/bash
# Simple performance monitoring for LeafLoaf GCP deployment

SERVICE_URL="https://leafloaf-v2srnrkkhq-nn.a.run.app"
LOG_FILE="performance_log_$(date +%Y%m%d).csv"

# Initialize CSV if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
    echo "timestamp,endpoint,latency_ms,status_code,success" > "$LOG_FILE"
fi

# Function to test endpoint and log results
test_endpoint() {
    local endpoint=$1
    local method=$2
    local data=$3
    
    START=$(date +%s%3N)
    
    if [ "$method" = "POST" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVICE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVICE_URL$endpoint" 2>/dev/null)
    fi
    
    END=$(date +%s%3N)
    LATENCY=$((END - START))
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    SUCCESS="false"
    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS="true"
    fi
    
    # Log to CSV
    echo "$(date -Iseconds),$endpoint,$LATENCY,$HTTP_CODE,$SUCCESS" >> "$LOG_FILE"
    
    # Print to console
    if [ "$SUCCESS" = "true" ]; then
        echo "✅ $endpoint: ${LATENCY}ms"
    else
        echo "❌ $endpoint: ${LATENCY}ms (HTTP $HTTP_CODE)"
    fi
}

echo "🔍 Monitoring LeafLoaf Performance"
echo "📊 Logging to: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    echo "$(date '+%H:%M:%S') - Running tests..."
    
    # Test health endpoint
    test_endpoint "/health" "GET" ""
    
    # Test search endpoint
    test_endpoint "/api/v1/search" "POST" '{"query":"organic milk","session_id":"monitor"}'
    
    echo ""
    
    # Wait before next test (adjust interval as needed)
    sleep 60
done