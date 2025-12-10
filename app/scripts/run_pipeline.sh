#!/bin/bash

##############################################################################
# AI News Tracker - Master Pipeline Orchestrator
#
# Purpose:
#   Orchestrates the complete data processing pipeline:
#   1. Fetch news from feeds (Google News, Reddit, Twitter/X)
#   2. Sanitize and filter content
#   3. Summarize articles with Claude
#   4. Generate video ideas
#   5. Generate thumbnails via Leonardo API
#   6. Merge all data into feed.json
#   7. Update Flask API with new feed
#
# Usage:
#   bash run_pipeline.sh [--test] [--limit N] [--image-limit N]
#   --test: Run in test mode (limits to 12 articles, image-limit defaults to 0)
#   --limit N: Limit feed to N articles (default: 12)
#   --image-limit N: Limit thumbnail generation to N images (default: 0 in test mode, unlimited in production)
#   Or via cron: 0 0 * * * /path/to/run_pipeline.sh >> /var/log/pipeline.log 2>&1  (runs daily at midnight)
#
# Note: This script runs the pipeline directly. To trigger via n8n workflow, use:
#   curl -X POST http://localhost:5678/webhook/run-pipeline
#   Or use the webhook_trigger.sh script
#
# Requirements:
#   - .env file with API keys (ANTHROPIC_API_KEY, LEONARDO_API_KEY, etc.)
#   - Python 3.11+ with dependencies installed
#   - Flask app running at http://python-app:5001 (or http://localhost:5001)
#
# Error Handling:
#   - set -euo pipefail: Exit on error, undefined vars, pipe failures
#   - Logs all output to timestamped log file
#   - Returns non-zero exit code on failure
#
##############################################################################

set -euo pipefail

# Parse command-line arguments
TEST_MODE=false
FEED_LIMIT=30  # Default: 30 articles
IMAGE_LIMIT=0  # Default: no images in test mode, unlimited in production

while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_MODE=true
            FEED_LIMIT=5  # Test mode: limit to 5 articles
            # Test mode defaults to 0 images (can be overridden with --image-limit)
            IMAGE_LIMIT=0
            shift
            ;;
        --limit)
            FEED_LIMIT="$2"
            shift 2
            ;;
        --image-limit)
            IMAGE_LIMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--test] [--limit N] [--image-limit N]"
            echo "  --test: Run in test mode (limits to 12 articles, image-limit defaults to 0)"
            echo "  --limit N: Limit feed to N articles (default: 12)"
            echo "  --image-limit N: Limit thumbnail generation to N images (default: 0 in test mode, unlimited in production)"
            exit 1
            ;;
    esac
done

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/app"
DATA_DIR="$APP_DIR/data"
LOGS_DIR="$APP_DIR/logs"
ENV_FILE="$PROJECT_ROOT/.env"

# Python executable - use Docker container if available, otherwise local python3
# Check if we're running inside Docker or if container exists
if [ -f /.dockerenv ] || [ -n "${DOCKER_CONTAINER:-}" ]; then
    # Running inside Docker container
    PYTHON="${PYTHON3_BIN:-python3}"
    DOCKER_EXEC=""
elif docker ps --format '{{.Names}}' | grep -q "^ai-news-python$" 2>/dev/null; then
    # Container exists, use docker exec
    PYTHON="python3"
    DOCKER_EXEC="docker exec ai-news-python"
    DOCKER_EXEC_I="docker exec -i ai-news-python"  # For stdin forwarding
    echo "[INFO] Using Docker container: ai-news-python"
else
    # Running locally, use local python3
    PYTHON="${PYTHON3_BIN:-python3}"
    DOCKER_EXEC=""
    echo "[WARN] Running locally - ensure Python dependencies are installed"
fi

# Ensure directories exist
mkdir -p "$DATA_DIR" "$LOGS_DIR"

# Cleanup function to remove old data and images
cleanup_old_data() {
    log "INFO" "=== CLEANUP: Removing old feed data and images ==="
    
    # Remove ALL JSON files EXCEPT display.json
    # display.json is kept until a new one is successfully created
    local removed_count=0
    if [ -d "$DATA_DIR" ]; then
        while IFS= read -r -d '' json_file; do
            local filename=$(basename "$json_file")
            if [ "$filename" != "display.json" ]; then
                rm -f "$json_file"
                removed_count=$((removed_count + 1))
                log "INFO" "Removed: $filename"
            fi
        done < <(find "$DATA_DIR" -maxdepth 1 -name "*.json" -type f -print0 2>/dev/null)
    fi
    
    # Remove thumbnail image files (thumbnail_*.png)
    if [ -d "$DATA_DIR" ]; then
        local image_count=0
        while IFS= read -r -d '' image_file; do
            rm -f "$image_file"
            image_count=$((image_count + 1))
            log "INFO" "Removed image: $(basename "$image_file")"
        done < <(find "$DATA_DIR" -maxdepth 1 -name "thumbnail_*.png" -type f -print0 2>/dev/null)
        
        if [ $image_count -gt 0 ]; then
            log "INFO" "Removed $image_count thumbnail image(s)"
        fi
    fi
    
    if [ $removed_count -gt 0 ] || [ ${image_count:-0} -gt 0 ]; then
        log "INFO" "Cleanup complete: removed $removed_count data file(s) and ${image_count:-0} image(s)"
    else
        log "INFO" "No old data to clean up"
    fi
    log "INFO" ""
}

# Create or touch .env if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env file not found at $ENV_FILE"
    echo "Some steps may fail without API keys."
fi

# Source .env to load API keys and config
if [ -f "$ENV_FILE" ]; then
    set +a  # Disable automatic export
    source "$ENV_FILE"
    set -a  # Re-enable automatic export
fi

# Log function with timestamp
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message"
}

# Error handler
error_exit() {
    local line_num="$1"
    local exit_code="$2"
    log "ERROR" "Pipeline failed at line $line_num with exit code $exit_code"
    log "ERROR" "Full pipeline did not complete successfully"
    exit "$exit_code"
}

# Trap errors and call error handler
trap 'error_exit ${LINENO} $?' ERR

# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

{
    log "INFO" "=========================================="
    log "INFO" "Starting AI News Tracker Pipeline"
    if [ "$TEST_MODE" = true ]; then
        log "INFO" "TEST MODE: Limited to $FEED_LIMIT articles"
    else
        log "INFO" "Feed limit: $FEED_LIMIT articles"
    fi
    log "INFO" "=========================================="
    log "INFO" "Project Root: $PROJECT_ROOT"
    log "INFO" "App Directory: $APP_DIR"
    log "INFO" "Data Directory: $DATA_DIR"
    log "INFO" "Python: $PYTHON"
    log "INFO" ""

    
    PIPELINE_START=$(date +%s)

    # Step 0: Cleanup old data and images
    STEP_START=$(date +%s)
    cleanup_old_data
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))

    # Step 1: Fetch news from all feeds (RSS scraper, Reddit, Twitter/X)
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 1: Fetching news from feeds ==="
    if [ -f "$APP_DIR/scripts/rss_scraper.py" ]; then
        log "INFO" "Running RSS scraper..."
        if [ -n "$DOCKER_EXEC" ]; then
            # Script writes to file directly, just capture stderr for errors
            $DOCKER_EXEC $PYTHON "/app/app/scripts/rss_scraper.py" || {
                log "ERROR" "RSS scraper failed"
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/rss_scraper.py" || {
                log "ERROR" "RSS scraper failed"
                exit 1
            }
        fi
        log "INFO" "Raw news saved to: $DATA_DIR/raw_news.json"
        raw_count=$(grep -c '"title"' "$DATA_DIR/raw_news.json" 2>/dev/null || echo 0)
        log "INFO" "Fetched approximately $raw_count articles"
    else
        log "WARN" "RSS scraper not found, skipping..."
    fi
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Step 2: Pre-filter articles for AI relevance (before summarization)
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 2: Pre-filtering articles for AI relevance (limit: $FEED_LIMIT) ==="
    if [ -f "$APP_DIR/scripts/pre_filter.py" ]; then
        log "INFO" "Running pre-filter with limit: $FEED_LIMIT..."
        if [ -n "$DOCKER_EXEC" ]; then
            $DOCKER_EXEC $PYTHON "/app/app/scripts/pre_filter.py" --limit "$FEED_LIMIT" || {
                log "ERROR" "Pre-filter failed"
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/pre_filter.py" --limit "$FEED_LIMIT" || {
                log "ERROR" "Pre-filter failed"
                exit 1
            }
        fi
        filtered_count=$(grep -c '"article_id"' "$DATA_DIR/filtered_news.json" 2>/dev/null || echo 0)
        log "INFO" "Pre-filtered to $filtered_count AI-relevant articles (saved to filtered_news.json)"
    else
        log "WARN" "Pre-filter not found, skipping... (all articles will be processed)"
    fi
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Step 3: Summarize filtered articles
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 3: Summarizing filtered articles ==="
    if [ -f "$APP_DIR/scripts/summarizer.py" ]; then
        log "INFO" "Running summarizer (reading from filtered_news.json)..."
        if [ -n "$DOCKER_EXEC" ]; then
            # Script reads from filtered_news.json via stdin or file fallback
            if [ -f "$DATA_DIR/filtered_news.json" ]; then
                cat "$DATA_DIR/filtered_news.json" | $DOCKER_EXEC_I $PYTHON "/app/app/scripts/summarizer.py" || {
                    log "ERROR" "Summarizer failed"
                    exit 1
                }
            else
                log "ERROR" "filtered_news.json not found"
                exit 1
            fi
        else
            # Local execution
            if [ -f "$DATA_DIR/filtered_news.json" ]; then
                cat "$DATA_DIR/filtered_news.json" | $PYTHON "$APP_DIR/scripts/summarizer.py" || {
                    log "ERROR" "Summarizer failed"
                    exit 1
            }
            else
                log "ERROR" "filtered_news.json not found"
                exit 1
            fi
        fi
        log "INFO" "Summaries saved to: $DATA_DIR/summaries.json"
        summary_count=$(grep -c '"article_id"' "$DATA_DIR/summaries.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $summary_count summaries"
    else
        log "WARN" "Summarizer not found, skipping..."
    fi
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Step 4: Generate video ideas from summaries
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 4: Generating video ideas ==="
    if [ -f "$APP_DIR/scripts/video_idea_generator.py" ]; then
        log "INFO" "Running video idea generator..."
        if [ -n "$DOCKER_EXEC" ]; then
            # Use docker exec -i to enable stdin forwarding
            if [ -f "$DATA_DIR/summaries.json" ]; then
                cat "$DATA_DIR/summaries.json" | $DOCKER_EXEC_I $PYTHON "/app/app/scripts/video_idea_generator.py" || {
                    log "ERROR" "Video idea generator failed"
                    exit 1
                }
            else
                log "ERROR" "summaries.json not found"
                exit 1
            fi
        else
            # Local execution - pipe works fine
            cat "$DATA_DIR/summaries.json" | $PYTHON "$APP_DIR/scripts/video_idea_generator.py" || {
                log "ERROR" "Video idea generator failed"
                exit 1
            }
        fi
        log "INFO" "Video ideas saved to: $DATA_DIR/video_ideas.json"
        idea_count=$(grep -c '"article_id"' "$DATA_DIR/video_ideas.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $idea_count video ideas"
    else
        log "WARN" "Video idea generator not found, skipping..."
    fi
    log "INFO" ""

    # Step 5: Tag images are pre-generated separately (see generate_tag_images.sh)
    # Skip thumbnail generation in pipeline - images are assigned from tag_images based on visual_tags
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 5: Skipping thumbnail generation (using pre-generated tag images) ==="
    log "INFO" "Tag images should be generated separately using: bash app/scripts/generate_tag_images.sh"
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Step 6: Merge all data into unified feed (tag images assigned based on visual_tags)
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 6: Merging data into feed.json and display.json (limit: $FEED_LIMIT) ==="
    
    # Use data_manager.py directly (simpler, no API dependency)
    if [ -f "$APP_DIR/scripts/data_manager.py" ]; then
        log "INFO" "Running data manager with feed limit: $FEED_LIMIT..."
        if [ -n "$DOCKER_EXEC" ]; then
            $DOCKER_EXEC $PYTHON "/app/app/scripts/data_manager.py" --limit "$FEED_LIMIT" 2>&1 || {
                log "ERROR" "Data manager failed"
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/data_manager.py" --limit "$FEED_LIMIT" 2>&1 || {
                log "ERROR" "Data manager failed"
                exit 1
            }
        fi
    else
        log "ERROR" "Data manager not found at $APP_DIR/scripts/data_manager.py"
        exit 1
    fi
    
    log "INFO" "Merged feed saved to: $DATA_DIR/feed.json"
    if [ -f "$DATA_DIR/feed.json" ]; then
        feed_count=$(grep -c '"title"' "$DATA_DIR/feed.json" 2>/dev/null || echo 0)
        log "INFO" "Final feed contains $feed_count items (limit: $FEED_LIMIT)"
    fi
    
    # Verify display.json was successfully created and is valid
    # (We don't delete display.json in cleanup - only overwrite it when new one is ready)
    if [ -f "$DATA_DIR/display.json" ]; then
        # Verify new display.json is valid (has items array and version)
        if grep -q '"items"' "$DATA_DIR/display.json" 2>/dev/null && grep -q '"version"' "$DATA_DIR/display.json" 2>/dev/null; then
            display_count=$(grep -c '"article_id"' "$DATA_DIR/display.json" 2>/dev/null || echo 0)
            log "INFO" "display.json created successfully with $display_count items"
        else
            log "WARN" "display.json exists but appears invalid - old version may still be in use"
        fi
    else
        log "WARN" "display.json was not created - old version will remain if it exists"
    fi
    
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Step 7: Update Flask API with new feed
    STEP_START=$(date +%s)
    log "INFO" "=== STEP 7: Updating Flask API ==="
    
    # Determine Flask URL (from .env or default)
    FLASK_HOST="${FLASK_HOST:-localhost}"
    FLASK_PORT="${PYTHON_APP_PORT:-5001}"
    FLASK_URL="http://$FLASK_HOST:$FLASK_PORT"
    
    log "INFO" "Sending feed update to Flask API at $FLASK_URL/api/refresh"
    
    if [ -f "$DATA_DIR/feed.json" ]; then
        # Check if Flask is reachable
        if curl -sf "$FLASK_URL/health" > /dev/null 2>&1; then
            log "INFO" "Flask API is reachable"
            
            # Send POST request with feed.json
            response=$(curl -s -X POST "$FLASK_URL/api/refresh" \
                -H "Content-Type: application/json" \
                -d @"$DATA_DIR/feed.json" \
                -w "\n%{http_code}") || {
                log "ERROR" "Failed to send feed to Flask API"
                exit 1
            }
            
            http_code=$(echo "$response" | tail -n1)
            if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
                log "INFO" "Feed successfully updated (HTTP $http_code)"
            else
                log "WARN" "Flask API returned HTTP $http_code (may still be ok)"
            fi
        else
            log "WARN" "Flask API not reachable at $FLASK_URL (app may not be running)"
            log "INFO" "Feed prepared at $DATA_DIR/feed.json but not sent to API"
        fi
    else
        log "WARN" "feed.json not found, skipping API update"
    fi
    STEP_END=$(date +%s)
    STEP_DURATION=$((STEP_END - STEP_START))
    log "INFO" ""

    # Calculate total pipeline duration
    PIPELINE_END=$(date +%s)
    PIPELINE_DURATION=$((PIPELINE_END - PIPELINE_START))
    
    # Write final summary to execution log

    # Summary
    log "INFO" "=========================================="
    log "INFO" "Pipeline completed successfully!"
    log "INFO" "Total execution time: ${PIPELINE_DURATION}s ($(awk "BEGIN {printf \"%.1f\", ${PIPELINE_DURATION}/60}") minutes)"
    log "INFO" "=========================================="
    log "INFO" "Outputs saved to: $DATA_DIR/"
    log "INFO" "  - raw_news.json (initial fetch, preserved)"
    log "INFO" "  - filtered_news.json (filtered articles with article_id)"
    log "INFO" "  - summaries.json (summaries with article_id)"
    log "INFO" "  - video_ideas.json (video ideas with article_id)"
    log "INFO" "  - tag_images/ (pre-generated tag images, see generate_tag_images.sh)"
    log "INFO" "  - feed.json (final merged feed, version 2.0)"
    log "INFO" ""

}

# Exit with success
exit 0
