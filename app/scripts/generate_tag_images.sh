#!/bin/bash

##############################################################################
# Generate Tag Images - Batch Image Generation for Visual Tags
#
# Purpose:
#   Generates one image per visual tag category in VISUAL_TAG_CATEGORIES.
#   Images are saved as numbered files (tag_001.png, tag_002.png, etc.)
#   These images are then reused for articles based on their visual tags.
#
# Usage:
#   bash generate_tag_images.sh [--limit N]
#   --limit N: Limit to N images (default: 30, one per tag category)
#
# Requirements:
#   - .env file with LEONARDO_API_KEY
#   - Python 3.11+ with dependencies installed
#   - Docker container ai-news-python running (or local Python)
#
##############################################################################

set -euo pipefail

# Parse command-line arguments
IMAGE_LIMIT=30

while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            IMAGE_LIMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--limit N]"
            echo "  --limit N: Limit to N images (default: 30)"
            exit 1
            ;;
    esac
done

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/app"
DATA_DIR="$APP_DIR/data"
TAG_IMAGES_DIR="$DATA_DIR/tag_images"
ENV_FILE="$PROJECT_ROOT/.env"

# Python executable - use Docker container if available, otherwise local python3
if [ -f /.dockerenv ] || [ -n "${DOCKER_CONTAINER:-}" ]; then
    PYTHON="${PYTHON3_BIN:-python3}"
    DOCKER_EXEC=""
elif docker ps --format '{{.Names}}' | grep -q "^ai-news-python$" 2>/dev/null; then
    PYTHON="python3"
    DOCKER_EXEC="docker exec ai-news-python"
    echo "[INFO] Using Docker container: ai-news-python"
else
    PYTHON="${PYTHON3_BIN:-python3}"
    DOCKER_EXEC=""
    echo "[WARN] Running locally - ensure Python dependencies are installed"
fi

# Ensure directories exist
mkdir -p "$TAG_IMAGES_DIR" "$LOGS_DIR"

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level]   $message" | tee -a "$LOG_FILE"
}

log "INFO" "=== Starting Tag Image Generation ==="
log "INFO" "Image limit: $IMAGE_LIMIT"
log "INFO" "Output directory: $TAG_IMAGES_DIR"
log "INFO" ""

# Check Leonardo API key
if [ -f "$ENV_FILE" ]; then
    api_key=$(grep '^LEONARDO_API_KEY=' "$ENV_FILE" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    if [ -z "$api_key" ]; then
        log "ERROR" "LEONARDO_API_KEY not found in .env"
        exit 1
    fi
else
    log "ERROR" ".env file not found: $ENV_FILE"
    exit 1
fi

# Create Python script to generate tag images
log "INFO" "Generating images for visual tag categories..."

if [ -n "$DOCKER_EXEC" ]; then
    $DOCKER_EXEC $PYTHON "/app/app/scripts/generate_tag_images.py" --limit "$IMAGE_LIMIT" --output-dir "/app/app/data/tag_images"
else
    $PYTHON "$APP_DIR/scripts/generate_tag_images.py" --limit "$IMAGE_LIMIT" --output-dir "$TAG_IMAGES_DIR"
fi

if [ $? -eq 0 ]; then
    log "INFO" ""
    log "INFO" "=== Tag Image Generation Complete ==="
    log "INFO" "Images saved to: $TAG_IMAGES_DIR"
    image_count=$(find "$TAG_IMAGES_DIR" -name "tag_*.png" 2>/dev/null | wc -l)
    log "INFO" "Total images generated: $image_count"
else
    log "ERROR" "Tag image generation failed"
    exit 1
fi

