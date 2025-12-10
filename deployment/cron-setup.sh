#!/bin/bash
# Phase 12: Cron Job Setup Script
# This script helps set up cron jobs for automated pipeline execution

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBHOOK_SCRIPT="$PROJECT_ROOT/app/scripts/webhook_trigger.sh"
PIPELINE_SCRIPT="$PROJECT_ROOT/app/scripts/run_pipeline.sh"

echo "═══════════════════════════════════════════"
echo "Phase 12: Cron Job Setup"
echo "═══════════════════════════════════════════"
echo ""

# Check if scripts exist
if [ ! -f "$WEBHOOK_SCRIPT" ]; then
    echo -e "${RED}✗ Webhook trigger script not found: $WEBHOOK_SCRIPT${NC}"
    exit 1
fi

if [ ! -f "$PIPELINE_SCRIPT" ]; then
    echo -e "${RED}✗ Pipeline script not found: $PIPELINE_SCRIPT${NC}"
    exit 1
fi

# Make scripts executable
chmod +x "$WEBHOOK_SCRIPT" "$PIPELINE_SCRIPT"
echo -e "${GREEN}✓ Scripts are executable${NC}"
echo ""

# Determine which script to use
echo "Choose automation method:"
echo "1) n8n Webhook Trigger (recommended) - Triggers n8n workflow"
echo "2) Direct Pipeline Execution - Runs scripts directly"
echo ""
read -p "Enter choice [1 or 2]: " choice

case $choice in
    1)
        SCRIPT_TO_USE="$WEBHOOK_SCRIPT"
        SCRIPT_NAME="webhook_trigger.sh"
        METHOD="n8n webhook"
        ;;
    2)
        SCRIPT_TO_USE="$PIPELINE_SCRIPT"
        SCRIPT_NAME="run_pipeline.sh"
        METHOD="direct pipeline"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}Selected: $METHOD${NC}"
echo ""

# Get schedule preference
echo "Choose schedule:"
echo "1) Every 6 hours (0 */6 * * *)"
echo "2) Every 12 hours (0 */12 * * *)"
echo "3) Daily at midnight (0 0 * * *)"
echo "4) Custom (you'll enter manually)"
echo ""
read -p "Enter choice [1-4]: " schedule_choice

case $schedule_choice in
    1)
        CRON_SCHEDULE="0 */6 * * *"
        ;;
    2)
        CRON_SCHEDULE="0 */12 * * *"
        ;;
    3)
        CRON_SCHEDULE="0 0 * * *"
        ;;
    4)
        read -p "Enter cron schedule (e.g., '0 */6 * * *'): " CRON_SCHEDULE
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Build cron line
CRON_LINE="$CRON_SCHEDULE $SCRIPT_TO_USE >> $PROJECT_ROOT/app/logs/cron.log 2>&1"

echo ""
echo -e "${YELLOW}The following cron job will be added:${NC}"
echo -e "${BLUE}$CRON_LINE${NC}"
echo ""

read -p "Add this cron job? (y/n): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_TO_USE"; then
    echo -e "${YELLOW}⚠ Cron job for this script already exists${NC}"
    echo "Current crontab entries:"
    crontab -l | grep "$SCRIPT_TO_USE" || true
    echo ""
    read -p "Remove existing entry and add new one? (y/n): " replace
    if [[ $replace =~ ^[Yy]$ ]]; then
        # Remove existing entry
        crontab -l 2>/dev/null | grep -v "$SCRIPT_TO_USE" | crontab -
        echo -e "${GREEN}✓ Removed existing cron job${NC}"
    else
        echo "Keeping existing entry. Exiting."
        exit 0
    fi
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo ""
echo -e "${GREEN}✓ Cron job added successfully!${NC}"
echo ""
echo "Current crontab:"
crontab -l
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To manually edit crontab: crontab -e"
echo "To view crontab: crontab -l"
echo "To remove all cron jobs: crontab -r"

