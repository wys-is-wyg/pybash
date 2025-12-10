#!/bin/bash

##############################################################################
# AI News Tracker - n8n Webhook Trigger
#
# Purpose:
#   Triggers the n8n pipeline via webhook to initiate news processing workflow
#   Can be called manually or via cron for scheduled execution
#
# Usage:
#   bash webhook_trigger.sh [trigger_source] [optional_metadata]
#   Examples:
#     webhook_trigger.sh                    # Manual trigger (default)
#     webhook_trigger.sh "cron"             # Triggered by cron job
#     webhook_trigger.sh "manual" "user:admin"  # Manual with metadata
#
# Requirements:
#   - .env file with N8N_WEBHOOK_URL
#   - curl command available
#   - curl must support -w flag for HTTP status codes
#
# Environment Variables (from .env):
#   N8N_WEBHOOK_URL: Full URL to n8n webhook endpoint
#                    Example: https://n8n.example.com/webhook/news-pipeline
#
# Output:
#   - Logs to /app/logs/webhook_trigger_YYYYMMDD_HHMMSS.log
#   - Stdout: Summary of trigger result
#   - Exit code: 0 on success, 1 on failure
#
##############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$PROJECT_ROOT/app"
ENV_FILE="$PROJECT_ROOT/.env"

# Parameters
TRIGGER_SOURCE="${1:-manual}"
METADATA="${2:-}"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

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
    log "ERROR" "Webhook trigger failed at line $line_num with exit code $exit_code"
    exit "$exit_code"
}

# Trap errors and call error handler
trap 'error_exit ${LINENO} $?' ERR

{
    log "INFO" "=========================================="
    log "INFO" "Triggering n8n Pipeline Webhook"
    log "INFO" "=========================================="
    log "INFO" "Trigger Source: $TRIGGER_SOURCE"
    log "INFO" "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        log "INFO" "Loading environment from .env"
        set +a
        source "$ENV_FILE"
        set -a
    else
        log "WARN" ".env file not found at $ENV_FILE"
        log "WARN" "Will attempt to use N8N_WEBHOOK_URL from environment"
    fi

    # Check if webhook URL is set
    if [ -z "${N8N_WEBHOOK_URL:-}" ]; then
        log "ERROR" "N8N_WEBHOOK_URL not set in environment or .env"
        log "ERROR" "Please set N8N_WEBHOOK_URL in .env or environment"
        exit 1
    fi

    log "INFO" "n8n Webhook URL configured (endpoint hidden for security)"

    # Construct JSON payload
    TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
    
    # Build payload JSON
    PAYLOAD=$(cat <<EOF
{
  "trigger_source": "$TRIGGER_SOURCE",
  "timestamp": "$TIMESTAMP",
  "hostname": "$HOSTNAME",
  "triggered_by": "pybash_webhook_trigger",
  "metadata": "$METADATA"
}
EOF
)

    log "INFO" "Constructed webhook payload:"
    log "INFO" "  Trigger Source: $TRIGGER_SOURCE"
    log "INFO" "  Timestamp: $TIMESTAMP"
    log "INFO" "  Hostname: $HOSTNAME"
    if [ -n "$METADATA" ]; then
        log "INFO" "  Metadata: $METADATA"
    fi

    # Send webhook request
    log "INFO" "Sending POST request to n8n webhook..."
    
    # Use curl with verbose output and HTTP status code capture
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$N8N_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" 2>&1) || {
        log "ERROR" "curl command failed"
        exit 1
    }

    # Parse response (last line is HTTP code, rest is response body)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

    log "INFO" "Webhook response received"
    log "INFO" "HTTP Status Code: $HTTP_CODE"
    
    if [ -n "$RESPONSE_BODY" ]; then
        log "INFO" "Response Body:"
        echo "$RESPONSE_BODY" | while IFS= read -r line; do
            log "INFO" "  $line"
        done
    fi

    # Evaluate response
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "202" ]; then
        log "INFO" "✓ Webhook trigger successful (HTTP $HTTP_CODE)"
        log "INFO" "n8n pipeline has been triggered"
        log "INFO" "Monitor n8n dashboard for execution status"
    elif [ "$HTTP_CODE" = "204" ]; then
        log "INFO" "✓ Webhook accepted (HTTP 204 - No Content)"
        log "INFO" "n8n pipeline has been triggered"
    else
        log "WARN" "Webhook returned unexpected status code: $HTTP_CODE"
        log "WARN" "Pipeline may not have been triggered"
        log "WARN" "Check n8n webhook configuration and accessibility"
        # Don't exit on unexpected codes - webhook may still have processed
    fi

    log "INFO" ""
    log "INFO" "=========================================="
    log "INFO" "Webhook trigger completed"
    log "INFO" "=========================================="

}

exit 0
