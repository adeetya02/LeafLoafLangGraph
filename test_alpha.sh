#!/bin/bash
# Test script for dynamic alpha calculation

echo "=== Testing Dynamic Alpha Calculation ==="
echo "Watch the console logs for alpha values!"
echo ""

# Test 1: Very Specific (Multiple dietary terms)
echo "TEST 1: Very Specific Query - 'organic gluten free bread'"
echo "Expected: Low alpha (0.2-0.3)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "organic gluten free bread"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 2: Specific with nutritional
echo "TEST 2: Nutritional Specific - '2% organic milk'"
echo "Expected: Low alpha (0.3-0.35)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "2% organic milk"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 3: Single attribute
echo "TEST 3: Single Attribute - 'fresh vegetables'"
echo "Expected: Medium alpha (0.4-0.5)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "fresh vegetables"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 4: General product
echo "TEST 4: General Query - 'bananas'"
echo "Expected: Default alpha (0.5)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "bananas"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 5: Exploratory
echo "TEST 5: Exploratory - 'dinner ideas'"
echo "Expected: High alpha (0.8-0.9)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "dinner ideas"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 6: Purpose-driven
echo "TEST 6: Purpose Query - 'tomatoes for pasta'"
echo "Expected: Medium-high alpha (0.6-0.7)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "tomatoes for pasta"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 7: Complex query
echo "TEST 7: Complex - 'healthy breakfast options'"
echo "Expected: High alpha (0.8)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "healthy breakfast options"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"
sleep 1

# Test 8: Brand specific (if you add brands to config)
echo "TEST 8: Specific Product - 'cage free eggs'"
echo "Expected: Low-medium alpha (0.35-0.4)"
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "cage free eggs"}' \
  -s | python -m json.tool | grep -E "(query|total_time_ms)"
echo -e "\n---\n"

echo "=== Check your console logs for alpha values! ==="