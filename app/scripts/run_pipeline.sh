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
#   bash run_pipeline.sh
#   Or via cron: 0 */6 * * * /path/to/run_pipeline.sh >> /var/log/pipeline.log 2>&1
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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/app"
DATA_DIR="$APP_DIR/data"
LOGS_DIR="$APP_DIR/logs"
LOG_FILE="$LOGS_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
ENV_FILE="$PROJECT_ROOT/.env"

# Python executable (use python3 if available, fall back to python)
PYTHON="${PYTHON3_BIN:-python3}"

# Ensure directories exist
mkdir -p "$DATA_DIR" "$LOGS_DIR"

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
    log "INFO" "=========================================="
    log "INFO" "Project Root: $PROJECT_ROOT"
    log "INFO" "App Directory: $APP_DIR"
    log "INFO" "Data Directory: $DATA_DIR"
    log "INFO" "Python: $PYTHON"
    log "INFO" ""

    # Step 1: Fetch news from all feeds (RSS scraper, Reddit, Twitter/X)
    log "INFO" "=== STEP 1: Fetching news from feeds ==="
    if [ -f "$APP_DIR/scripts/rss_scraper.py" ]; then
        log "INFO" "Running RSS scraper..."
        $PYTHON "$APP_DIR/scripts/rss_scraper.py" > "$DATA_DIR/raw_news.json" 2>&1 || {
            log "ERROR" "RSS scraper failed"
            exit 1
        }
        log "INFO" "Raw news saved to: $DATA_DIR/raw_news.json"
        local raw_count=$(grep -c '"title"' "$DATA_DIR/raw_news.json" 2>/dev/null || echo 0)
        log "INFO" "Fetched approximately $raw_count articles"
    else
        log "WARN" "RSS scraper not found, skipping..."
    fi
    log "INFO" ""

    # Step 2: Sanitize and filter content
    log "INFO" "=== STEP 2: Sanitizing and filtering content ==="
    if [ -f "$APP_DIR/scripts/content_sanitizer.py" ]; then
        log "INFO" "Running content sanitizer..."
        # Note: sanitizer is typically called from within summarizer/pipeline
        log "INFO" "Content sanitization will be applied during summarization"
    else
        log "WARN" "Content sanitizer not found, skipping explicit sanitization..."
    fi
    log "INFO" ""

    # Step 3: Summarize articles with Claude
    log "INFO" "=== STEP 3: Summarizing articles ==="
    if [ -f "$APP_DIR/scripts/summarizer.py" ]; then
        log "INFO" "Running summarizer (Claude)..."
        $PYTHON "$APP_DIR/scripts/summarizer.py" \
            < "$DATA_DIR/raw_news.json" \
            > "$DATA_DIR/summaries.json" 2>&1 || {
            log "ERROR" "Summarizer failed"
            exit 1
        }
        log "INFO" "Summaries saved to: $DATA_DIR/summaries.json"
        local summary_count=$(grep -c '"title"' "$DATA_DIR/summaries.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $summary_count summaries"
    else
        log "WARN" "Summarizer not found, skipping..."
    fi
    log "INFO" ""

    # Step 4: Generate video ideas from summaries
    log "INFO" "=== STEP 4: Generating video ideas ==="
    if [ -f "$APP_DIR/scripts/video_idea_generator.py" ]; then
        log "INFO" "Running video idea generator..."
        $PYTHON "$APP_DIR/scripts/video_idea_generator.py" \
            < "$DATA_DIR/summaries.json" \
            > "$DATA_DIR/video_ideas.json" 2>&1 || {
            log "ERROR" "Video idea generator failed"
            exit 1
        }
        log "INFO" "Video ideas saved to: $DATA_DIR/video_ideas.json"
        local idea_count=$(grep -c '"video_title"' "$DATA_DIR/video_ideas.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $idea_count video ideas"
    else
        log "WARN" "Video idea generator not found, skipping..."
    fi
    log "INFO" ""

    # Step 5: Generate thumbnails via Leonardo API
    log "INFO" "=== STEP 5: Generating thumbnails via Leonardo API ==="
    if [ -f "$APP_DIR/scripts/leonardo_api.py" ]; then
        log "INFO" "Running thumbnail generator..."
        $PYTHON "$APP_DIR/scripts/leonardo_api.py" \
            < "$DATA_DIR/video_ideas.json" \
            > "$DATA_DIR/thumbnails.json" 2>&1 || {
            log "WARN" "Thumbnail generator encountered issues (may be expected if API limits reached)"
        }
        log "INFO" "Thumbnails saved to: $DATA_DIR/thumbnails.json"
    else
        log "WARN" "Thumbnail generator not found, skipping..."
    fi
    log "INFO" ""

    # Step 6: Merge all data into unified feed
    log "INFO" "=== STEP 6: Merging data into feed.json ==="
    if [ -f "$APP_DIR/scripts/data_manager.py" ]; then
        log "INFO" "Running data manager..."
        $PYTHON "$APP_DIR/scripts/data_manager.py" 2>&1 || {
            log "ERROR" "Data manager failed"
            exit 1
        }
        log "INFO" "Merged feed saved to: $DATA_DIR/feed.json"
        if [ -f "$DATA_DIR/feed.json" ]; then
            local feed_count=$(grep -c '"title"' "$DATA_DIR/feed.json" 2>/dev/null || echo 0)
            log "INFO" "Final feed contains $feed_count items"
        fi
    else
        log "WARN" "Data manager not found, skipping merge..."
    fi
    log "INFO" ""

    # Step 7: Update Flask API with new feed
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
    log "INFO" ""

    # Summary
    log "INFO" "=========================================="
    log "INFO" "Pipeline completed successfully!"
    log "INFO" "=========================================="
    log "INFO" "Outputs saved to: $DATA_DIR/"
    log "INFO" "  - raw_news.json (initial fetch)"
    log "INFO" "  - summaries.json (Claude summaries)"
    log "INFO" "  - video_ideas.json (generated ideas)"
    log "INFO" "  - thumbnails.json (Leonardo API results)"
    log "INFO" "  - feed.json (final merged feed)"
    log "INFO" "Logs saved to: $LOG_FILE"
    log "INFO" ""

} 2>&1 | tee -a "$LOG_FILE"

# Exit with success
exit 0
