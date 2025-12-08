#!/bin/bash

# Upload script for AI News Tracker to VPS
# Run this from your local machine (WSL2/Ubuntu)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration - EDIT THESE
VPS_USER="${1:-root}"           # VPS username (default: root)
VPS_HOST="${2:-srv1186603.hstgr.cloud}"  # VPS hostname or IP
VPS_PATH="${3:-~/ai-news-tracker}"       # Destination path on VPS
LOCAL_PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}Upload AI News Tracker to VPS${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Configuration:"
echo "  VPS User: $VPS_USER"
echo "  VPS Host: $VPS_HOST"
echo "  VPS Path: $VPS_PATH"
echo "  Local Dir: $LOCAL_PROJECT_DIR"
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${YELLOW}No SSH key found. You may be prompted for a password.${NC}"
    echo -e "${YELLOW}Consider setting up SSH keys for passwordless access.${NC}"
    echo ""
fi

# Test SSH connection
echo -e "${GREEN}Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${VPS_USER}@${VPS_HOST}" exit 2>/dev/null; then
    echo -e "${YELLOW}SSH connection test failed. You may need to enter password.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create destination directory on VPS
echo -e "${GREEN}Creating destination directory on VPS...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${VPS_PATH}"

# Files and directories to upload (excluding unnecessary files)
echo -e "${GREEN}Uploading project files...${NC}"

# Upload using rsync (more efficient than scp)
if command -v rsync &> /dev/null; then
    echo "Using rsync (faster, supports resume)..."
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='app/models/*.gguf' \
        --exclude='app/models/models--*' \
        --exclude='app/data/*.json' \
        --exclude='app/logs/*.log' \
        --exclude='web/ssl/*.pem' \
        --exclude='web/ssl/*.key' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        "${LOCAL_PROJECT_DIR}/" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"
else
    echo "Using scp (rsync not available)..."
    # Create tar archive and upload
    echo "Creating archive..."
    cd "$LOCAL_PROJECT_DIR"
    tar --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='app/models/*.gguf' \
        --exclude='app/models/models--*' \
        --exclude='app/data/*.json' \
        --exclude='app/logs/*.log' \
        --exclude='web/ssl/*.pem' \
        --exclude='web/ssl/*.key' \
        -czf /tmp/ai-news-tracker.tar.gz .
    
    echo "Uploading archive..."
    scp /tmp/ai-news-tracker.tar.gz "${VPS_USER}@${VPS_HOST}:/tmp/"
    
    echo "Extracting on VPS..."
    ssh "${VPS_USER}@${VPS_HOST}" "cd ${VPS_PATH} && tar -xzf /tmp/ai-news-tracker.tar.gz && rm /tmp/ai-news-tracker.tar.gz"
    
    rm /tmp/ai-news-tracker.tar.gz
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}Upload Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps on VPS:${NC}"
echo "1. SSH into your VPS:"
echo "   ssh ${VPS_USER}@${VPS_HOST}"
echo ""
echo "2. Navigate to project directory:"
echo "   cd ${VPS_PATH}"
echo ""
echo "3. Create .env file (if not uploaded):"
echo "   cp .env.example .env  # if exists"
echo "   nano .env            # edit with your settings"
echo ""
echo "4. Run the installation script:"
echo "   bash deployment/vps-setup/vps-install.sh"
echo ""
echo "5. After installation, download model and start containers:"
echo "   bash app/scripts/download_model.sh"
echo "   docker compose build --no-cache"
echo "   docker compose up -d"
echo ""

