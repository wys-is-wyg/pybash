#!/bin/bash
# Helper script to import n8n workflow via API
# This is an alternative to manual import through the UI

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
N8N_URL="${N8N_URL:-http://localhost:5678}"
WORKFLOW_FILE="${1:-n8n/workflows/ai-news-pipeline.json}"
N8N_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_PASSWORD="${N8N_AUTH_PASSWORD:-}"

echo "═══════════════════════════════════════════"
echo "n8n Workflow Import Script"
echo "═══════════════════════════════════════════"
echo ""

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}✗ Workflow file not found: $WORKFLOW_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Workflow file found: $WORKFLOW_FILE${NC}"

# Check if n8n is accessible
echo -n "Checking n8n accessibility... "
if curl -s -f -o /dev/null "$N8N_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo "n8n is not accessible at $N8N_URL"
    echo "Make sure n8n container is running: docker-compose ps"
    exit 1
fi

# Check if password is set
if [ -z "$N8N_PASSWORD" ]; then
    echo -e "${YELLOW}⚠ N8N_AUTH_PASSWORD not set${NC}"
    echo "Please set N8N_AUTH_PASSWORD in .env or environment"
    echo ""
    echo "For manual import, use the n8n UI:"
    echo "1. Go to http://localhost:5678"
    echo "2. Login with admin / (your password)"
    echo "3. Click 'Workflows' → 'Import from File'"
    echo "4. Select: $WORKFLOW_FILE"
    exit 1
fi

echo "Attempting to import workflow via API..."
echo ""

# Note: n8n API import requires authentication
# This script provides instructions for manual import
# Full API import would require n8n API key setup

echo "For automated import, you need to:"
echo "1. Get your n8n API key from: $N8N_URL/api/v1/api-keys"
echo "2. Use the API to import the workflow"
echo ""
echo "Alternatively, import manually:"
echo "1. Open: $N8N_URL"
echo "2. Login with: $N8N_USER / (password from .env)"
echo "3. Go to Workflows → Import from File"
echo "4. Select: $WORKFLOW_FILE"
echo "5. Save and activate the workflow"
echo ""
echo -e "${GREEN}Workflow file ready: $WORKFLOW_FILE${NC}"

