#!/bin/bash
# Integration test script for data-service

set -e

echo "=== Data Service Integration Tests ==="
echo ""

# Base URL
BASE_URL="${BASE_URL:-http://localhost:8003}"

echo "Testing against: $BASE_URL"
echo ""

# Test 1: Health check
echo "Test 1: Health check"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo "✓ Health check passed (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Health check failed (HTTP $http_code)"
    exit 1
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root endpoint"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    echo "✓ Root endpoint passed (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Root endpoint failed (HTTP $http_code)"
    exit 1
fi
echo ""

# Test 3: Ocean currents endpoint (without credentials, expect 502)
echo "Test 3: Ocean currents endpoint"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/data/ocean-currents?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

# Without credentials, we expect 502 (Bad Gateway - external source error)
if [ "$http_code" -eq 502 ] || [ "$http_code" -eq 200 ]; then
    echo "✓ Ocean currents endpoint responding (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Ocean currents endpoint unexpected status (HTTP $http_code)"
    echo "  Response: $body"
    exit 1
fi
echo ""

# Test 4: Wind endpoint (without credentials, expect 502)
echo "Test 4: Wind endpoint"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/data/wind?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 502 ] || [ "$http_code" -eq 200 ]; then
    echo "✓ Wind endpoint responding (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Wind endpoint unexpected status (HTTP $http_code)"
    echo "  Response: $body"
    exit 1
fi
echo ""

# Test 5: Waves endpoint (without credentials, expect 502)
echo "Test 5: Waves endpoint"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/data/waves?min_lat=60&max_lat=70&min_lon=-20&max_lon=-10&start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 502 ] || [ "$http_code" -eq 200 ]; then
    echo "✓ Waves endpoint responding (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Waves endpoint unexpected status (HTTP $http_code)"
    echo "  Response: $body"
    exit 1
fi
echo ""

# Test 6: Invalid bounds (expect 400)
echo "Test 6: Invalid bounds"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/data/ocean-currents?min_lat=70&max_lat=60&min_lon=-20&max_lon=-10")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 400 ]; then
    echo "✓ Invalid bounds correctly rejected (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Invalid bounds should return 400, got $http_code"
    exit 1
fi
echo ""

# Test 7: Missing parameters (expect 400)
echo "Test 7: Missing parameters"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/data/ocean-currents")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 400 ]; then
    echo "✓ Missing parameters correctly rejected (HTTP $http_code)"
    echo "  Response: $body"
else
    echo "✗ Missing parameters should return 400, got $http_code"
    exit 1
fi
echo ""

echo "=== All tests passed! ==="
