#!/bin/bash
# Phase 10: Local Development Testing Script
# This script automates verification steps for local development

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════"
echo "Phase 10: Local Development Testing"
echo "═══════════════════════════════════════════"
echo ""

# Function to check if a service is responding
check_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    if response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_status" ] || [ "$response" -eq "000" ]; then
            # 000 means connection failed, but we'll handle it
            if [ "$response" -eq "$expected_status" ]; then
                echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
                return 0
            else
                echo -e "${YELLOW}⚠ Connection issue${NC} (HTTP $response)"
                return 1
            fi
        else
            echo -e "${YELLOW}⚠ Unexpected status${NC} (HTTP $response)"
            return 1
        fi
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Step 37: Check if dependencies are installed
echo "Step 37: Checking dependencies..."
if [ ! -d "web/node_modules" ]; then
    echo -e "${YELLOW}⚠ web/node_modules not found. Run: npm install --prefix web/${NC}"
else
    echo -e "${GREEN}✓ Node modules installed${NC}"
fi

# Check if Docker images are built
echo -n "Checking Docker images... "
if docker images | grep -q "pybash-python-app\|ai-news-python" || docker images | grep -q "pybash-web-server\|ai-news-web"; then
    echo -e "${GREEN}✓ Docker images found${NC}"
else
    echo -e "${YELLOW}⚠ Docker images not found. Run: docker-compose build${NC}"
fi
echo ""

# Step 38: Check if containers are running
echo "Step 38: Checking container status..."
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Containers are running${NC}"
    docker-compose ps
else
    echo -e "${YELLOW}⚠ Containers not running. Start with: docker-compose up -d${NC}"
    echo ""
    read -p "Would you like to start containers now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose up -d
        echo "Waiting 10 seconds for services to start..."
        sleep 10
    else
        echo "Skipping container startup. Please start manually and rerun this script."
        exit 1
    fi
fi
echo ""

# Step 39: Verify all services
echo "Step 39: Verifying all services..."
echo ""

# Check Python health endpoint
if check_service "Python App (health)" "http://localhost:5001/health"; then
    echo "  Health check response:"
    curl -s http://localhost:5001/health | head -c 100
    echo "..."
else
    echo -e "  ${RED}Python app health check failed${NC}"
fi
echo ""

# Check Web server
if check_service "Web Server" "http://localhost:8080" 200; then
    echo "  Web server is responding"
else
    echo -e "  ${RED}Web server check failed${NC}"
fi
echo ""

# Check n8n
if check_service "n8n Dashboard" "http://localhost:5678" 200; then
    echo "  n8n dashboard is responding"
else
    echo -e "  ${YELLOW}n8n may not be ready yet${NC}"
fi
echo ""

# Step 41: Test API endpoints
echo "Step 41: Testing API endpoints..."
echo ""

# Test news feed endpoint
echo -n "Testing GET /api/news... "
if response=$(curl -s -w "\n%{http_code}" http://localhost:5001/api/news 2>/dev/null); then
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $http_code)"
        item_count=$(echo "$body" | grep -o '"title"' | wc -l || echo "0")
        echo "  Found $item_count items in feed"
    else
        echo -e "${YELLOW}⚠ Status: $http_code${NC}"
    fi
else
    echo -e "${RED}✗ Failed${NC}"
fi
echo ""

# Test refresh endpoint
echo -n "Testing POST /api/refresh... "
if response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:5001/api/refresh \
    -H "Content-Type: application/json" \
    -d '{"status":"test"}' 2>/dev/null); then
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $http_code)"
    else
        echo -e "${YELLOW}⚠ Status: $http_code${NC}"
    fi
else
    echo -e "${RED}✗ Failed${NC}"
fi
echo ""

# Step 43: Run API tests
echo "Step 43: Running API tests with pytest..."
echo ""

if command -v pytest &> /dev/null; then
    if [ -f "app/tests/test_api.py" ]; then
        echo "Running: pytest app/tests/test_api.py -v"
        if pytest app/tests/test_api.py -v; then
            echo -e "${GREEN}✓ All API tests passed${NC}"
        else
            echo -e "${RED}✗ Some tests failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ test_api.py not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ pytest not found. Install with: pip install pytest${NC}"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════"
echo "Testing Summary"
echo "═══════════════════════════════════════════"
echo ""
echo "Step 42: Open web UI manually at:"
echo "  ${GREEN}http://localhost:8080${NC}"
echo ""
echo "Step 40: View logs with:"
echo "  docker-compose logs -f python-app"
echo "  docker-compose logs -f web-server"
echo "  docker-compose logs -f n8n"
echo ""
echo "All automated checks complete!"
echo ""

