#!/bin/bash

##############################################################################
# Test Summarizer - Quick Test Script
#
# Tests the summarizer with just the first article from raw_news.json
# Skips the rest of the pipeline for quick testing.
#
# Usage:
#   bash test_summarizer.sh [article_number]
#
# Examples:
#   bash test_summarizer.sh        # Test first article
#   bash test_summarizer.sh 5      # Test 5th article
#   bash test_summarizer.sh 1 3    # Test articles 1-3
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/app"
DATA_DIR="$APP_DIR/data"

# Parse arguments
ARTICLE_NUM="${1:-1}"  # Default to first article
NUM_ARTICLES="${2:-1}"  # Default to 1 article

# Python executable - use Docker container if available
if docker ps --format '{{.Names}}' | grep -q "^ai-news-python$" 2>/dev/null; then
    PYTHON="python3"
    DOCKER_EXEC="docker exec ai-news-python"
    echo "[INFO] Using Docker container: ai-news-python"
else
    PYTHON="python3"
    DOCKER_EXEC=""
    echo "[WARN] Running locally - ensure Python dependencies are installed"
fi

# Check if raw_news.json exists
INPUT_FILE="$DATA_DIR/raw_news.json"
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: $INPUT_FILE not found"
    echo "Please run RSS scraper first: docker exec ai-news-python python3 /app/app/scripts/rss_scraper.py"
    exit 1
fi

echo "=========================================="
echo "Testing Summarizer"
echo "=========================================="
echo "Input file: $INPUT_FILE"
echo "Testing article(s): $ARTICLE_NUM to $((ARTICLE_NUM + NUM_ARTICLES - 1))"
echo ""

# Extract specific articles using Python
if [ -n "$DOCKER_EXEC" ]; then
    TEST_DATA=$($DOCKER_EXEC $PYTHON -c "
import json
import sys

try:
    with open('$INPUT_FILE', 'r') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    if not items:
        print('Error: No items found in raw_news.json', file=sys.stderr)
        sys.exit(1)
    
    # Extract articles (0-indexed, so subtract 1)
    start_idx = $ARTICLE_NUM - 1
    end_idx = start_idx + $NUM_ARTICLES
    
    if start_idx >= len(items):
        print(f'Error: Article $ARTICLE_NUM not found (only {len(items)} articles available)', file=sys.stderr)
        sys.exit(1)
    
    test_items = items[start_idx:end_idx]
    
    # Create test data structure
    test_data = {
        'items': test_items,
        'total_items': len(test_items),
        'test_mode': True
    }
    
    print(json.dumps(test_data))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
")
else
    TEST_DATA=$(python3 -c "
import json
import sys

try:
    with open('$INPUT_FILE', 'r') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    if not items:
        print('Error: No items found in raw_news.json', file=sys.stderr)
        sys.exit(1)
    
    start_idx = $ARTICLE_NUM - 1
    end_idx = start_idx + $NUM_ARTICLES
    
    if start_idx >= len(items):
        print(f'Error: Article $ARTICLE_NUM not found (only {len(items)} articles available)', file=sys.stderr)
        sys.exit(1)
    
    test_items = items[start_idx:end_idx]
    
    test_data = {
        'items': test_items,
        'total_items': len(test_items),
        'test_mode': True
    }
    
    print(json.dumps(test_data))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
")
fi

if [ $? -ne 0 ]; then
    echo "$TEST_DATA"
    exit 1
fi

# Show article title(s) being tested
echo "Article(s) to test:"
echo "$TEST_DATA" | $DOCKER_EXEC $PYTHON -c "
import json
import sys

data = json.load(sys.stdin)
for i, item in enumerate(data.get('items', []), 1):
    title = item.get('title', 'No title')[:80]
    print(f'  {i}. {title}...')
"

echo ""
echo "Running summarizer..."
echo ""

# Run summarizer with test data
if [ -n "$DOCKER_EXEC" ]; then
    echo "$TEST_DATA" | $DOCKER_EXEC $PYTHON "/app/app/scripts/summarizer.py" 2>&1
else
    echo "$TEST_DATA" | $PYTHON "$APP_DIR/scripts/summarizer.py" 2>&1
fi

SUMMARIZER_EXIT=$?

if [ $SUMMARIZER_EXIT -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Summarizer test completed successfully!"
    echo "=========================================="
    echo ""
    echo "Check output: $DATA_DIR/summaries.json"
    echo ""
    
    # Show summary preview
    if [ -f "$DATA_DIR/summaries.json" ]; then
        echo "Summary preview:"
        if [ -n "$DOCKER_EXEC" ]; then
            $DOCKER_EXEC $PYTHON -c "
import json
with open('$DATA_DIR/summaries.json', 'r') as f:
    data = json.load(f)
    items = data.get('items', [])
    if items:
        item = items[0]
        print(f\"Title: {item.get('title', '')[:60]}...\")
        print(f\"Summary: {item.get('summary', '')[:200]}...\")
        print(f\"Generated: {item.get('summary_generated', False)}\")
" 2>/dev/null || echo "Could not read summaries.json"
        else
            python3 -c "
import json
with open('$DATA_DIR/summaries.json', 'r') as f:
    data = json.load(f)
    items = data.get('items', [])
    if items:
        item = items[0]
        print(f\"Title: {item.get('title', '')[:60]}...\")
        print(f\"Summary: {item.get('summary', '')[:200]}...\")
        print(f\"Generated: {item.get('summary_generated', False)}\")
" 2>/dev/null || echo "Could not read summaries.json"
        fi
    fi
else
    echo ""
    echo "=========================================="
    echo "Summarizer test failed (exit code: $SUMMARIZER_EXIT)"
    echo "=========================================="
    exit $SUMMARIZER_EXIT
fi

