#!/bin/bash

# VPS Installation Script for AI News Tracker
# Run this script on your Ubuntu 24.04 VPS after uploading project files

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-srv1186603.hstgr.cloud}"  # Default domain, can override with argument
PROJECT_DIR="${HOME}/ai-news-tracker"

echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}AI News Tracker - VPS Installation${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root. Run as a regular user with sudo privileges.${NC}"
    exit 1
fi

# Check sudo access
if ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}This script requires sudo privileges. You may be prompted for your password.${NC}"
fi

echo -e "${GREEN}[1/8] Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${GREEN}[2/8] Installing prerequisites...${NC}"
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    nginx \
    certbot \
    python3-certbot-nginx

echo -e "${GREEN}[3/8] Installing Docker...${NC}"
# Remove old versions if any
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
fi

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
if ! groups | grep -q docker; then
    echo -e "${GREEN}Adding user to docker group...${NC}"
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Note: You may need to log out and back in for docker group changes to take effect.${NC}"
    echo -e "${YELLOW}Or run: newgrp docker${NC}"
fi

# Verify Docker installation
if sudo docker run --rm hello-world > /dev/null 2>&1; then
    echo -e "${GREEN}Docker installed successfully!${NC}"
else
    echo -e "${RED}Docker installation verification failed.${NC}"
    exit 1
fi

echo -e "${GREEN}[4/8] Configuring firewall (UFW)...${NC}"
# Allow SSH first (critical!)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Enable firewall (non-interactive)
echo "y" | sudo ufw enable

# Show status
sudo ufw status verbose

echo -e "${GREEN}[5/8] Checking project directory...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    echo -e "${YELLOW}Please upload your project files first using SCP or the upload script.${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Check for required files
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found in $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}[6/8] Securing Docker ports (binding to localhost only)...${NC}"
# Backup original docker-compose.yml
if [ ! -f "docker-compose.yml.backup" ]; then
    cp docker-compose.yml docker-compose.yml.backup
fi

# Update ports to bind to localhost only (security)
sed -i.bak 's/- "5001:5001"/- "127.0.0.1:5001:5001"/' docker-compose.yml
sed -i.bak 's/- "8080:8080"/- "127.0.0.1:8080:8080"/' docker-compose.yml
sed -i.bak 's/- "8443:8443"/- "127.0.0.1:8443:8443"/' docker-compose.yml
sed -i.bak 's/- "5678:5678"/- "127.0.0.1:5678:5678"/' docker-compose.yml
rm -f docker-compose.yml.bak

echo -e "${GREEN}[7/8] Configuring Nginx reverse proxy...${NC}"

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/ai-news-tracker > /dev/null <<EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    # SSL certificates (will be added by Certbot)
    # ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;

    # Increase timeouts for long-running requests
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Main web application (port 8080)
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Python API (port 5001)
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # n8n dashboard (port 5678)
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }

    # n8n static assets
    location /static/ {
        proxy_pass http://localhost:5678/static/;
        proxy_http_version 1.1;
    }

    location /assets/ {
        proxy_pass http://localhost:5678/assets/;
        proxy_http_version 1.1;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/ai-news-tracker /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo -e "${GREEN}Nginx configured successfully!${NC}"
else
    echo -e "${RED}Nginx configuration test failed!${NC}"
    exit 1
fi

echo -e "${GREEN}[8/8] Setting up SSL certificate (Let's Encrypt)...${NC}"
echo -e "${YELLOW}This will temporarily stop Nginx to obtain the certificate.${NC}"
read -p "Do you want to set up SSL now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Stop Nginx temporarily
    sudo systemctl stop nginx
    
    # Generate certificate
    if sudo certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}" 2>/dev/null || \
       sudo certbot certonly --standalone -d "$DOMAIN"; then
        echo -e "${GREEN}SSL certificate obtained!${NC}"
        
        # Update Nginx config with certificate paths
        sudo sed -i "s|# ssl_certificate|ssl_certificate|g" /etc/nginx/sites-available/ai-news-tracker
        sudo sed -i "s|# ssl_certificate_key|ssl_certificate_key|g" /etc/nginx/sites-available/ai-news-tracker
        
        # Test and reload
        if sudo nginx -t; then
            sudo systemctl start nginx
            sudo systemctl reload nginx
            echo -e "${GREEN}SSL configured in Nginx!${NC}"
        else
            echo -e "${RED}Nginx configuration error after SSL setup!${NC}"
            sudo systemctl start nginx
        fi
        
        # Set up auto-renewal
        (crontab -l 2>/dev/null; echo "0 0 * * * certbot renew --quiet && systemctl reload nginx") | crontab -
        echo -e "${GREEN}SSL auto-renewal configured!${NC}"
    else
        echo -e "${YELLOW}SSL certificate generation failed or skipped. You can set it up later.${NC}"
        sudo systemctl start nginx
    fi
else
    echo -e "${YELLOW}Skipping SSL setup. You can set it up later with:${NC}"
    echo -e "${YELLOW}  sudo certbot certonly --standalone -d ${DOMAIN}${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Ensure your .env file is configured in $PROJECT_DIR"
echo "2. Download the LLM model:"
echo "   cd $PROJECT_DIR && bash app/scripts/download_model.sh"
echo "3. Build and start Docker containers:"
echo "   cd $PROJECT_DIR"
echo "   docker compose build --no-cache"
echo "   docker compose up -d"
echo "4. Verify services:"
echo "   docker compose ps"
echo "   docker compose logs -f"
echo ""
echo -e "${YELLOW}If you added yourself to the docker group, you may need to:${NC}"
echo "   newgrp docker"
echo "   # or log out and back in"
echo ""
echo -e "${GREEN}Your site should be accessible at:${NC}"
echo "   http://${DOMAIN} (will redirect to HTTPS if SSL is configured)"
echo "   https://${DOMAIN} (if SSL is configured)"
echo ""

