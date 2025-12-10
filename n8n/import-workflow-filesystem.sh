#!/bin/bash
# Import n8n workflow via file system (works when UI/API doesn't)
# This copies the workflow file into n8n's data directory

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
WORKFLOW_FILE="${1:-n8n/workflows/ai-news-pipeline.json}"
CONTAINER_NAME="${N8N_CONTAINER_NAME:-ai-news-n8n}"

echo "═══════════════════════════════════════════"
echo "n8n Workflow Import (File System Method)"
echo "═══════════════════════════════════════════"
echo ""

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}✗ Workflow file not found: $WORKFLOW_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Workflow file found: $WORKFLOW_FILE${NC}"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}✗ n8n container '$CONTAINER_NAME' is not running${NC}"
    echo "Start it with: docker-compose up -d n8n"
    exit 1
fi

echo -e "${GREEN}✓ n8n container is running${NC}"

# Copy workflow file to n8n container's import directory
echo ""
echo "Copying workflow file to n8n container..."
docker cp "$WORKFLOW_FILE" "${CONTAINER_NAME}:/tmp/ai-news-pipeline.json"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Workflow file copied to container${NC}"
else
    echo -e "${RED}✗ Failed to copy workflow file${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠ Manual import required${NC}"
echo ""
echo "The workflow file has been copied to the n8n container."
echo "To import it:"
echo ""
echo "1. Access n8n UI (http://localhost:5678 or your VPS URL)"
echo "2. Login with your credentials"
echo "3. Click 'Workflows' → 'Import from File'"
echo "4. The file is available in the container at: /tmp/ai-news-pipeline.json"
echo ""
echo "OR use the n8n CLI inside the container:"
echo ""
echo "  docker exec -it ${CONTAINER_NAME} n8n import:workflow --input=/tmp/ai-news-pipeline.json"
echo ""
echo -e "${GREEN}Workflow file ready for import!${NC}"

