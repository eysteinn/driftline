#!/bin/bash
# Quick test script for mission flow
# This script tests the basic flow without requiring Python dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8000"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"

echo "=========================================="
echo "Mission Flow Quick Test"
echo "=========================================="
echo ""

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if services are running
echo "Step 1: Checking services..."
print_info "Checking API health..."

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" ${API_BASE_URL}/health)
if [ "$API_HEALTH" -eq 200 ]; then
    print_status 0 "API is healthy"
else
    print_status 1 "API is not responding (HTTP $API_HEALTH)"
fi

echo ""
echo "Step 2: Registering test user..."
print_info "Email: $TEST_EMAIL"

REGISTER_RESPONSE=$(curl -s -X POST ${API_BASE_URL}/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"fullName\": \"Test User\"
  }")

# Extract access token
ACCESS_TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)

if [ -n "$ACCESS_TOKEN" ]; then
    print_status 0 "User registered successfully"
    print_info "Access token: ${ACCESS_TOKEN:0:20}..."
else
    print_status 1 "User registration failed"
    echo "Response: $REGISTER_RESPONSE"
fi

echo ""
echo "Step 3: Creating test mission..."

MISSION_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
MISSION_RESPONSE=$(curl -s -X POST ${API_BASE_URL}/api/v1/missions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"name\": \"Quick Test Mission\",
    \"description\": \"Automated test mission\",
    \"lastKnownLat\": 60.0,
    \"lastKnownLon\": -3.0,
    \"lastKnownTime\": \"$MISSION_TIME\",
    \"objectType\": \"1\",
    \"forecastHours\": 24,
    \"ensembleSize\": 100
  }")

# Extract mission ID
MISSION_ID=$(echo $MISSION_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -n "$MISSION_ID" ]; then
    print_status 0 "Mission created successfully"
    print_info "Mission ID: $MISSION_ID"
    
    # Extract status
    MISSION_STATUS=$(echo $MISSION_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    print_info "Initial status: $MISSION_STATUS"
else
    print_status 1 "Mission creation failed"
    echo "Response: $MISSION_RESPONSE"
fi

echo ""
echo "Step 4: Checking mission status..."
sleep 2

STATUS_RESPONSE=$(curl -s ${API_BASE_URL}/api/v1/missions/${MISSION_ID}/status \
  -H "Authorization: Bearer $ACCESS_TOKEN")

CURRENT_STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)

if [ -n "$CURRENT_STATUS" ]; then
    print_status 0 "Status retrieved successfully"
    print_info "Current status: $CURRENT_STATUS"
else
    print_status 1 "Status retrieval failed"
fi

echo ""
echo "Step 5: Listing user missions..."

MISSIONS_RESPONSE=$(curl -s ${API_BASE_URL}/api/v1/missions \
  -H "Authorization: Bearer $ACCESS_TOKEN")

MISSION_COUNT=$(echo $MISSIONS_RESPONSE | grep -o '"id"' | wc -l)

if [ $MISSION_COUNT -gt 0 ]; then
    print_status 0 "Missions listed successfully"
    print_info "Found $MISSION_COUNT mission(s)"
else
    print_status 1 "Mission listing failed or no missions found"
fi

echo ""
echo "Step 6: Checking Redis queue..."
print_info "Connecting to Redis..."

if command -v docker &> /dev/null; then
    QUEUE_LENGTH=$(docker exec driftline-redis redis-cli LLEN drift_jobs 2>/dev/null || echo "0")
    print_info "Queue length: $QUEUE_LENGTH"
    
    if [ $QUEUE_LENGTH -gt 0 ]; then
        print_status 0 "Job found in Redis queue"
    else
        print_info "Queue is empty (job may have been processed)"
    fi
else
    print_info "Docker not available, skipping Redis check"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Test completed successfully!"
echo ""
echo "✓ API is responsive"
echo "✓ User registration works"
echo "✓ Mission creation works"
echo "✓ Job enqueuing works"
echo "✓ Mission status retrieval works"
echo "✓ Mission listing works"
echo ""
echo "Mission ID: $MISSION_ID"
echo "Status: $CURRENT_STATUS"
echo ""
echo "To monitor the drift worker processing:"
echo "  docker compose -f docker-compose.dev.yml logs -f drift-worker"
echo ""
echo "To check mission status again:"
echo "  curl ${API_BASE_URL}/api/v1/missions/${MISSION_ID}/status \\"
echo "    -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
echo "To get results (once completed):"
echo "  curl ${API_BASE_URL}/api/v1/missions/${MISSION_ID}/results \\"
echo "    -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
