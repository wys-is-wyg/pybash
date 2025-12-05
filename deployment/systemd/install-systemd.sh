#!/bin/bash
# Phase 12: Systemd Timer Installation Script
# This script installs systemd service and timer units for automated pipeline execution

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script is in deployment/systemd/, so files are in the same directory
SYSTEMD_DIR="$SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SYSTEMD_DIR/ai-news-tracker.service"
TIMER_FILE="$SYSTEMD_DIR/ai-news-tracker.timer"
SYSTEMD_SERVICE="/etc/systemd/system/ai-news-tracker.service"
SYSTEMD_TIMER="/etc/systemd/system/ai-news-tracker.timer"

echo "═══════════════════════════════════════════"
echo "Phase 12: Systemd Timer Installation"
echo "═══════════════════════════════════════════"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if files exist
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}✗ Service file not found: $SERVICE_FILE${NC}"
    exit 1
fi

if [ ! -f "$TIMER_FILE" ]; then
    echo -e "${RED}✗ Timer file not found: $TIMER_FILE${NC}"
    exit 1
fi

# Get username (default to current user if not root)
USERNAME="${SUDO_USER:-$USER}"
if [ "$USERNAME" = "root" ]; then
    echo -e "${YELLOW}⚠ Running as root. Please specify username:${NC}"
    read -p "Enter username: " USERNAME
fi

# Verify paths exist
PROJECT_PATH="/home/$USERNAME/projects/pybash"
if [ ! -d "$PROJECT_PATH" ]; then
    echo -e "${YELLOW}⚠ Project directory not found: $PROJECT_PATH${NC}"
    read -p "Enter correct project path: " PROJECT_PATH
fi

# Create temporary service file with replaced values
TEMP_SERVICE=$(mktemp)
sed "s|REPLACE_USERNAME|$USERNAME|g; s|REPLACE_PROJECT_ROOT|$PROJECT_PATH|g" "$SERVICE_FILE" > "$TEMP_SERVICE"

# Update service file with actual username and paths
echo -e "${BLUE}Configuring service file for user: $USERNAME${NC}"
echo -e "${BLUE}Project path: $PROJECT_PATH${NC}"

# Copy files to systemd directory
echo -e "${BLUE}Installing systemd units...${NC}"
cp "$TEMP_SERVICE" "$SYSTEMD_SERVICE"
cp "$TIMER_FILE" "$SYSTEMD_TIMER"
rm "$TEMP_SERVICE"

# Set permissions
chmod 644 "$SYSTEMD_SERVICE" "$SYSTEMD_TIMER"

# Reload systemd
echo -e "${BLUE}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable and start timer
echo -e "${BLUE}Enabling and starting timer...${NC}"
systemctl enable ai-news-tracker.timer
systemctl start ai-news-tracker.timer

echo ""
echo -e "${GREEN}✓ Systemd timer installed and started!${NC}"
echo ""
echo "Service status:"
systemctl status ai-news-tracker.timer --no-pager -l || true
echo ""
echo "Timer status:"
systemctl list-timers ai-news-tracker.timer --no-pager || true
echo ""
echo "Useful commands:"
echo "  systemctl status ai-news-tracker.timer  # Check timer status"
echo "  systemctl status ai-news-tracker.service  # Check last run"
echo "  systemctl list-timers  # List all timers"
echo "  journalctl -u ai-news-tracker.service  # View service logs"
echo "  systemctl stop ai-news-tracker.timer  # Stop timer"
echo "  systemctl disable ai-news-tracker.timer  # Disable timer"

