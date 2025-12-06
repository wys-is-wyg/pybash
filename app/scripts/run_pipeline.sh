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
#   bash run_pipeline.sh [--test] [--limit N]
#   --test: Run in test mode (limits to 6 articles, generates thumbnails for those 6)
#   --limit N: Limit feed to N articles (default: 30, test mode: 6)
#   Or via cron: 0 */6 * * * /path/to/run_pipeline.sh >> /var/log/pipeline.log 2>&1
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
FEED_LIMIT=30
SKIP_THUMBNAILS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_MODE=true
            FEED_LIMIT=6
            # Test mode still generates thumbnails, just for fewer articles
            SKIP_THUMBNAILS=false
            shift
            ;;
        --limit)
            FEED_LIMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--test] [--limit N]"
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
LOG_FILE="$LOGS_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
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
    
    # Remove JSON data files
    local data_files=(
        "$DATA_DIR/raw_news.json"
        "$DATA_DIR/summaries.json"
        "$DATA_DIR/video_ideas.json"
        "$DATA_DIR/thumbnails.json"
        "$DATA_DIR/feed.json"
    )
    
    local removed_count=0
    for file in "${data_files[@]}"; do
        if [ -f "$file" ]; then
            rm -f "$file"
            removed_count=$((removed_count + 1))
            log "INFO" "Removed: $(basename "$file")"
        fi
    done
    
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

    # Step 0: Cleanup old data and images
    cleanup_old_data

    # Step 1: Fetch news from all feeds (RSS scraper, Reddit, Twitter/X)
    log "INFO" "=== STEP 1: Fetching news from feeds ==="
    if [ -f "$APP_DIR/scripts/rss_scraper.py" ]; then
        log "INFO" "Running RSS scraper..."
        if [ -n "$DOCKER_EXEC" ]; then
            # Script writes to file directly, just capture stderr for errors
            $DOCKER_EXEC $PYTHON "/app/app/scripts/rss_scraper.py" 2>"$DATA_DIR/rss_scraper_stderr.log" || {
                log "ERROR" "RSS scraper failed"
                if [ -f "$DATA_DIR/rss_scraper_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/rss_scraper_stderr.log" | tail -10)"
                fi
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/rss_scraper.py" 2>"$DATA_DIR/rss_scraper_stderr.log" || {
                log "ERROR" "RSS scraper failed"
                if [ -f "$DATA_DIR/rss_scraper_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/rss_scraper_stderr.log" | tail -10)"
                fi
                exit 1
            }
        fi
        log "INFO" "Raw news saved to: $DATA_DIR/raw_news.json"
        raw_count=$(grep -c '"title"' "$DATA_DIR/raw_news.json" 2>/dev/null || echo 0)
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
        if [ -n "$DOCKER_EXEC" ]; then
            # Script writes to file directly, just capture stderr for errors
            $DOCKER_EXEC $PYTHON "/app/app/scripts/summarizer.py" < "$DATA_DIR/raw_news.json" 2>"$DATA_DIR/summarizer_stderr.log" || {
                log "ERROR" "Summarizer failed"
                if [ -f "$DATA_DIR/summarizer_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/summarizer_stderr.log" | tail -10)"
                fi
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/summarizer.py" < "$DATA_DIR/raw_news.json" 2>"$DATA_DIR/summarizer_stderr.log" || {
                log "ERROR" "Summarizer failed"
                if [ -f "$DATA_DIR/summarizer_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/summarizer_stderr.log" | tail -10)"
                fi
                exit 1
            }
        fi
        log "INFO" "Summaries saved to: $DATA_DIR/summaries.json"
        summary_count=$(grep -c '"title"' "$DATA_DIR/summaries.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $summary_count summaries"
    else
        log "WARN" "Summarizer not found, skipping..."
    fi
    log "INFO" ""

    # Step 4: Generate video ideas from summaries
    log "INFO" "=== STEP 4: Generating video ideas ==="
    if [ -f "$APP_DIR/scripts/video_idea_generator.py" ]; then
        log "INFO" "Running video idea generator..."
        if [ -n "$DOCKER_EXEC" ]; then
            # Script writes to file directly, just capture stderr for errors
            $DOCKER_EXEC $PYTHON "/app/app/scripts/video_idea_generator.py" < "$DATA_DIR/summaries.json" 2>"$DATA_DIR/video_ideas_stderr.log" || {
                log "ERROR" "Video idea generator failed"
                if [ -f "$DATA_DIR/video_ideas_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/video_ideas_stderr.log" | tail -10)"
                fi
                exit 1
            }
        else
            $PYTHON "$APP_DIR/scripts/video_idea_generator.py" < "$DATA_DIR/summaries.json" 2>"$DATA_DIR/video_ideas_stderr.log" || {
                log "ERROR" "Video idea generator failed"
                if [ -f "$DATA_DIR/video_ideas_stderr.log" ]; then
                    log "ERROR" "Error output: $(cat "$DATA_DIR/video_ideas_stderr.log" | tail -10)"
                fi
                exit 1
            }
        fi
        log "INFO" "Video ideas saved to: $DATA_DIR/video_ideas.json"
        idea_count=$(grep -c '"video_title"' "$DATA_DIR/video_ideas.json" 2>/dev/null || echo 0)
        log "INFO" "Generated $idea_count video ideas"
    else
        log "WARN" "Video idea generator not found, skipping..."
    fi
    log "INFO" ""

    # Step 5: Generate thumbnails via Leonardo API (limited to top N video ideas)
    if [ "$SKIP_THUMBNAILS" = false ]; then
        # In test mode, check credits and prompt for confirmation
        if [ "$TEST_MODE" = true ]; then
            log "INFO" "=== Checking Leonardo API Credits (Test Mode) ==="
            
            # Function to check Leonardo credits
            check_leonardo_credits() {
                local api_key
                if [ -f "$PROJECT_ROOT/.env" ]; then
                    api_key=$(grep '^LEONARDO_API_KEY=' "$PROJECT_ROOT/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
                fi
                
                if [ -z "$api_key" ]; then
                    log "WARN" "LEONARDO_API_KEY not found in .env"
                    return 1
                fi
                
                local response
                response=$(curl -s -w "\n%{http_code}" \
                    -X GET 'https://cloud.leonardo.ai/api/rest/v1/me' \
                    -H "Authorization: Bearer $api_key" \
                    -H 'Content-Type: application/json' 2>/dev/null)
                
                local http_code
                http_code=$(echo "$response" | tail -n1)
                local response_body
                response_body=$(echo "$response" | sed '$d')
                
                if [ "$http_code" = "200" ]; then
                    # Extract token information (API tokens are separate from subscription tokens)
                    local token_info
                    token_info=$(echo "$response_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'user_details' in data and len(data['user_details']) > 0:
        user = data['user_details'][0]
        sub_tokens = user.get('subscriptionTokens', 0)
        api_tokens = user.get('apiSubscriptionTokens', 0)
        api_paid_tokens = user.get('apiPaidTokens', 0) or 0
        paid_tokens = user.get('paidTokens', 0)
        # API uses apiSubscriptionTokens + apiPaidTokens, NOT regular subscriptionTokens
        api_total = api_tokens + (api_paid_tokens if api_paid_tokens else 0)
        print(f'{api_total}|{sub_tokens}|{api_tokens}|{api_paid_tokens}')
    else:
        print('0|0|0|0')
except Exception as e:
    print(f'0|0|0|0')
" 2>/dev/null)
                    
                    if [ -n "$token_info" ]; then
                        api_total=$(echo "$token_info" | cut -d'|' -f1)
                        sub_tokens=$(echo "$token_info" | cut -d'|' -f2)
                        api_sub_tokens=$(echo "$token_info" | cut -d'|' -f3)
                        api_paid=$(echo "$token_info" | cut -d'|' -f4)
                        
                        # Store all token info for display
                        echo "${api_total}|${sub_tokens}|${api_sub_tokens}|${api_paid}"
                        return 0
                    else
                        log "WARN" "Could not parse token information"
                        return 1
                    fi
                else
                    log "WARN" "Failed to check credits (HTTP $http_code)"
                    return 1
                fi
            }
            
            # Check credits
            token_info=$(check_leonardo_credits)
            if [ $? -eq 0 ] && [ -n "$token_info" ]; then
                api_total=$(echo "$token_info" | cut -d'|' -f1)
                sub_tokens=$(echo "$token_info" | cut -d'|' -f2)
                api_sub_tokens=$(echo "$token_info" | cut -d'|' -f3)
                api_paid=$(echo "$token_info" | cut -d'|' -f4)
                
                log "INFO" ""
                log "INFO" "═══════════════════════════════════════════"
                log "INFO" "Leonardo API Credits Check"
                log "INFO" "═══════════════════════════════════════════"
                log "INFO" "API Subscription Tokens: $api_sub_tokens"
                if [ -n "$api_paid" ] && [ "$api_paid" != "0" ] && [ "$api_paid" != "null" ]; then
                    log "INFO" "API Paid Tokens: $api_paid"
                fi
                log "INFO" "Total API Tokens Available: $api_total"
                log "INFO" "Regular Subscription Tokens: $sub_tokens (not used by API)"
                log "INFO" ""
                log "INFO" "Estimated tokens needed: ~$FEED_LIMIT (1 per thumbnail)"
                log "INFO" ""
                
                # Warn if API tokens are low or zero
                if [ "$api_total" = "0" ] || [ -z "$api_total" ] || [ "$api_total" = "null" ]; then
                    log "WARN" "⚠️  WARNING: You have 0 API tokens available!"
                    log "WARN" "The API requires 'apiSubscriptionTokens' or 'apiPaidTokens', not regular subscription tokens."
                    log "WARN" "Please check your Leonardo API plan or purchase API tokens."
                    log "WARN" ""
                elif [ "$api_total" -lt "$FEED_LIMIT" ]; then
                    log "WARN" "⚠️  WARNING: You may not have enough API tokens ($api_total available, ~$FEED_LIMIT needed)"
                    log "WARN" ""
                fi
                
                # Prompt for confirmation (read from /dev/tty to avoid pipe issues)
                while true; do
                    read -p "Proceed with thumbnail generation? (y/n): " -n 1 -r < /dev/tty
                    echo
                    case $REPLY in
                        [Yy]* )
                            log "INFO" "Proceeding with thumbnail generation..."
                            break
                            ;;
                        [Nn]* )
                            log "INFO" "Thumbnail generation cancelled by user"
                            SKIP_THUMBNAILS=true
                            break
                            ;;
                        * )
                            echo "Please answer yes (y) or no (n)." > /dev/tty
                            ;;
                    esac
                done
                log "INFO" ""
            else
                log "WARN" "Could not check credits, proceeding anyway..."
            fi
        fi
        
        log "INFO" "=== STEP 5: Generating thumbnails via Leonardo API (limit: $FEED_LIMIT) ==="
        if [ -f "$APP_DIR/scripts/leonardo_api.py" ]; then
            # Limit video ideas to match feed limit (only generate thumbnails for top N)
            VIDEO_IDEAS_INPUT="$DATA_DIR/video_ideas.json"
            if [ -f "$DATA_DIR/video_ideas.json" ] && [ "$FEED_LIMIT" -lt 100 ]; then
                log "INFO" "Limiting video ideas to $FEED_LIMIT for thumbnail generation"
                LIMITED_FILE="$DATA_DIR/video_ideas_limited.json"
                
                if [ -n "$DOCKER_EXEC" ]; then
                    $DOCKER_EXEC $PYTHON -c "
import json
from pathlib import Path

data_file = Path('/app/app/data/video_ideas.json')
limit_file = Path('/app/app/data/video_ideas_limited.json')

with open(data_file, 'r') as f:
    data = json.load(f)

items = data.get('items', [])[:$FEED_LIMIT]
limited_data = {
    'items': items,
    'total_items': len(items),
    'limited_to': $FEED_LIMIT
}

with open(limit_file, 'w') as f:
    json.dump(limited_data, f, indent=2)

print(f'Limited video ideas to {len(items)} items')
" 2>"$DATA_DIR/limit_ideas_stderr.log" && {
                        if [ -f "$LIMITED_FILE" ]; then
                            VIDEO_IDEAS_INPUT="$LIMITED_FILE"
                            log "INFO" "Using limited video ideas file with $FEED_LIMIT items"
                        else
                            log "WARN" "Limited file not created, using all video ideas"
                        fi
                    } || {
                        log "WARN" "Failed to limit video ideas, using all ideas"
                    }
                else
                    $PYTHON -c "
import json
from pathlib import Path

data_file = Path('$DATA_DIR/video_ideas.json')
limit_file = Path('$DATA_DIR/video_ideas_limited.json')

with open(data_file, 'r') as f:
    data = json.load(f)

items = data.get('items', [])[:$FEED_LIMIT]
limited_data = {
    'items': items,
    'total_items': len(items),
    'limited_to': $FEED_LIMIT
}

with open(limit_file, 'w') as f:
    json.dump(limited_data, f, indent=2)

print(f'Limited video ideas to {len(items)} items')
" 2>"$DATA_DIR/limit_ideas_stderr.log" && {
                        if [ -f "$LIMITED_FILE" ]; then
                            VIDEO_IDEAS_INPUT="$LIMITED_FILE"
                            log "INFO" "Using limited video ideas file with $FEED_LIMIT items"
                        else
                            log "WARN" "Limited file not created, using all video ideas"
                        fi
                    } || {
                        log "WARN" "Failed to limit video ideas, using all ideas"
                    }
                fi
            fi
            
            log "INFO" "Running thumbnail generator (limit: $FEED_LIMIT)..."
            if [ -n "$DOCKER_EXEC" ]; then
                # Convert local path to container path
                if [ "$VIDEO_IDEAS_INPUT" = "$DATA_DIR/video_ideas_limited.json" ]; then
                    CONTAINER_INPUT="/app/app/data/video_ideas_limited.json"
                else
                    CONTAINER_INPUT="/app/app/data/video_ideas.json"
                fi
                # Script writes to file directly, pass input file and limit as arguments
                $DOCKER_EXEC $PYTHON "/app/app/scripts/leonardo_api.py" --input "$CONTAINER_INPUT" --limit "$FEED_LIMIT" 2>"$DATA_DIR/thumbnails_stderr.log" || {
                    log "WARN" "Thumbnail generator encountered issues (may be expected if API limits reached)"
                    if [ -f "$DATA_DIR/thumbnails_stderr.log" ]; then
                        log "WARN" "Error output: $(cat "$DATA_DIR/thumbnails_stderr.log" | tail -5)"
                    fi
                }
            else
                $PYTHON "$APP_DIR/scripts/leonardo_api.py" --input "$VIDEO_IDEAS_INPUT" --limit "$FEED_LIMIT" 2>"$DATA_DIR/thumbnails_stderr.log" || {
                    log "WARN" "Thumbnail generator encountered issues (may be expected if API limits reached)"
                    if [ -f "$DATA_DIR/thumbnails_stderr.log" ]; then
                        log "WARN" "Error output: $(cat "$DATA_DIR/thumbnails_stderr.log" | tail -5)"
                    fi
                }
            fi
            log "INFO" "Thumbnails saved to: $DATA_DIR/thumbnails.json"
        else
            log "WARN" "Thumbnail generator not found, skipping..."
        fi
    fi
    log "INFO" ""

    # Step 6: Merge all data into unified feed
    log "INFO" "=== STEP 6: Merging data into feed.json (limit: $FEED_LIMIT) ==="
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
        log "INFO" "Merged feed saved to: $DATA_DIR/feed.json"
        if [ -f "$DATA_DIR/feed.json" ]; then
            feed_count=$(grep -c '"title"' "$DATA_DIR/feed.json" 2>/dev/null || echo 0)
            log "INFO" "Final feed contains $feed_count items (limit: $FEED_LIMIT)"
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
