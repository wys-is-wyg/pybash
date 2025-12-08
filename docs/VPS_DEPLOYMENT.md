# VPS Deployment Guide

Complete guide for deploying AI News Tracker to a bare Ubuntu 24.04 VPS.

## Table of Contents

1. [Quick Start (Automated)](#quick-start-automated)
2. [Initial VPS Setup](#initial-vps-setup)
3. [Install Dependencies](#install-dependencies)
4. [Firewall Configuration](#firewall-configuration)
5. [Deploy Application](#deploy-application)
6. [Nginx Reverse Proxy Setup](#nginx-reverse-proxy-setup)
7. [SSL/HTTPS Setup](#sslhttps-setup)
8. [Post-Deployment Steps](#post-deployment-steps)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start (Automated)

**For automated setup, use the provided scripts:**

### Step 1: Upload Project to VPS

From your **local machine** (WSL2/Ubuntu bash):

```bash
cd deployment/vps-setup
chmod +x upload-to-vps.sh
./upload-to-vps.sh [username] [hostname] [destination-path]
```

**Example:**
```bash
./upload-to-vps.sh root srv1186603.hstgr.cloud ~/ai-news-tracker
```

### Step 2: Run Installation Script on VPS

SSH into your VPS and run:

```bash
ssh root@srv1186603.hstgr.cloud
cd ~/ai-news-tracker
chmod +x deployment/vps-setup/vps-install.sh
bash deployment/vps-setup/vps-install.sh srv1186603.hstgr.cloud
```

The script will:
- Install Docker, Nginx, Certbot, and all dependencies
- Configure firewall (UFW)
- Set up Nginx reverse proxy
- Optionally configure SSL/HTTPS

### Step 3: Complete Setup

After installation:

```bash
# Create .env file
nano .env  # Add your configuration

# Download LLM model
bash app/scripts/download_model.sh

# Build and start containers
docker compose build --no-cache
docker compose up -d
```

**See `deployment/vps-setup/README.md` for detailed script documentation.**

**For manual step-by-step instructions, continue reading below.**

---

## Initial VPS Setup

### 1. Connect to VPS

```bash
ssh root@your-vps-ip
# Or if using a non-root user:
ssh username@your-vps-ip
```

### 2. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Create Non-Root User (if needed)

```bash
# Create user
adduser deploy
usermod -aG sudo deploy

# Switch to new user
su - deploy
```

---

## Install Dependencies

### 1. Install Docker

```bash
# Remove old versions if any
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
sudo docker run hello-world
```

### 2. Install Docker Compose (if not using plugin)

```bash
# Docker Compose is included in docker-compose-plugin, but if you need standalone:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 3. Add User to Docker Group

```bash
# Add current user to docker group (avoid needing sudo for docker commands)
sudo usermod -aG docker $USER

# Apply group changes (or log out and back in)
newgrp docker

# Verify
docker ps
```

### 4. Install Nginx

```bash
sudo apt-get install -y nginx

# Check status
sudo systemctl status nginx
```

### 5. Install Certbot (for SSL certificates)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
```

### 6. Install Git (if not already installed)

```bash
sudo apt-get install -y git
```

---

## Firewall Configuration

### 1. Configure UFW (Uncomplicated Firewall)

```bash
# Check UFW status
sudo ufw status

# Allow SSH (IMPORTANT: do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow custom SSH port if you changed it (e.g., 65002)
# sudo ufw allow 65002/tcp

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### 2. Verify Firewall Rules

```bash
# List all rules
sudo ufw status numbered

# Test that SSH is still accessible before closing session
# If locked out, you may need to access VPS console from hosting provider
```

**Important Notes:**
- Always allow SSH (port 22) before enabling UFW
- Docker containers can bypass UFW rules - we'll configure Nginx to handle external traffic
- Internal Docker ports (8080, 8443, 5001, 5678) should NOT be exposed to the internet

---

## Deploy Application

### 1. Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone <your-repo-url> ai-news-tracker
cd ai-news-tracker

# Or if deploying via SCP, create directory and upload files
mkdir -p ~/ai-news-tracker
# Then use SCP from local machine:
# scp -r . user@vps-ip:~/ai-news-tracker/
```

### 2. Create Environment File

```bash
# Copy example .env if exists, or create new one
cp .env.example .env  # if exists
# Or create manually:
nano .env
```

Add required environment variables:

```bash
# Python App
FLASK_ENV=production
FLASK_DEBUG=False

# LLM Configuration
LLM_MODEL_PATH=/app/app/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
LLM_N_CTX=2048
LLM_N_THREADS=2
LLM_N_GPU_LAYERS=0

# n8n Authentication
N8N_AUTH_PASSWORD=your-secure-password-here

# Leonardo AI API (if using)
LEONARDO_API_KEY=your-api-key-here

# Add any other required variables
```

### 3. Download LLM Model

```bash
cd ~/ai-news-tracker
bash app/scripts/download_model.sh
```

This downloads ~2.3GB model file. Wait for completion.

### 4. Build and Start Containers

```bash
cd ~/ai-news-tracker

# Build containers
docker compose build --no-cache

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Verify Services

```bash
# Check Python app
curl http://localhost:5001/health

# Check web server
curl http://localhost:8080

# Check n8n (should require auth)
curl http://localhost:5678
```

---

## Nginx Reverse Proxy Setup

Nginx will route external traffic (ports 80/443) to your Docker containers.

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/ai-news-tracker
```

Add the following configuration:

```nginx
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name srv1186603.hstgr.cloud;  # Replace with your domain

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name srv1186603.hstgr.cloud;  # Replace with your domain

    # SSL certificates (will be added by Certbot)
    # ssl_certificate /etc/letsencrypt/live/srv1186603.hstgr.cloud/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/srv1186603.hstgr.cloud/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;

    # Increase timeouts for long-running requests
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Main web application (port 8080)
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Python API (port 5001)
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # n8n dashboard (port 5678)
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
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
```

### 2. Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/ai-news-tracker /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

### 3. Update Docker Compose Ports (Security)

Edit `docker-compose.yml` to bind containers only to localhost (not 0.0.0.0):

```yaml
services:
  python-app:
    ports:
      - "127.0.0.1:5001:5001"  # Only accessible from localhost

  web-server:
    ports:
      - "127.0.0.1:8080:8080"   # Only accessible from localhost
      - "127.0.0.1:8443:8443"   # Only accessible from localhost

  n8n:
    ports:
      - "127.0.0.1:5678:5678"   # Only accessible from localhost
```

Then restart:

```bash
docker compose down
docker compose up -d
```

---

## SSL/HTTPS Setup

### Option 1: Let's Encrypt (Recommended for Production)

```bash
# Stop Nginx temporarily (Certbot needs port 80)
sudo systemctl stop nginx

# Generate certificate
sudo certbot certonly --standalone -d srv1186603.hstgr.cloud

# Start Nginx
sudo systemctl start nginx

# Update Nginx config to use certificates
sudo nano /etc/nginx/sites-available/ai-news-tracker
```

Uncomment and update SSL certificate paths:

```nginx
ssl_certificate /etc/letsencrypt/live/srv1186603.hstgr.cloud/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/srv1186603.hstgr.cloud/privkey.pem;
```

Add SSL configuration:

```nginx
# SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

Reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Self-Signed Certificate (Development Only)

```bash
cd ~/ai-news-tracker/web
bash generate-ssl.sh
```

Then update `docker-compose.yml` to mount certificates (if not already done).

### Auto-Renewal for Let's Encrypt

```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for auto-renewal
sudo crontab -e
```

Add:

```
0 0 * * * certbot renew --quiet && systemctl reload nginx
```

---

## Post-Deployment Steps

### 1. Verify Model Loading

```bash
cd ~/ai-news-tracker
docker compose logs python-app | grep -i "model\|llm"
```

Should see: `"LLM model loaded successfully"`

### 2. Test All Endpoints

```bash
# Main site (via Nginx)
curl http://srv1186603.hstgr.cloud
curl https://srv1186603.hstgr.cloud

# API endpoint
curl https://srv1186603.hstgr.cloud/api/health

# n8n dashboard
curl https://srv1186603.hstgr.cloud/n8n
```

### 3. Set Up Automation

If using systemd timers or cron jobs:

```bash
# Copy systemd files
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable ai-news-tracker.timer
sudo systemctl start ai-news-tracker.timer
```

Or set up cron jobs:

```bash
crontab -e
```

Add your scheduled tasks.

### 4. Monitor Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f python-app
docker compose logs -f web-server
docker compose logs -f n8n

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Troubleshooting

### Connection Refused Errors

**Problem**: `srv1186603.hstgr.cloud refused to connect`

**Solutions**:

1. **Check Docker containers are running**:
   ```bash
   docker compose ps
   docker compose logs
   ```

2. **Check Nginx is running**:
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```

3. **Check firewall**:
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

4. **Check ports are listening**:
   ```bash
   sudo netstat -tlnp | grep -E '80|443|8080|5001|5678'
   # Or using ss:
   sudo ss -tlnp | grep -E '80|443|8080|5001|5678'
   ```

5. **Check Nginx can reach Docker containers**:
   ```bash
   curl http://localhost:8080
   curl http://localhost:5001/health
   ```

6. **Check hosting provider firewall**:
   - Some VPS providers have additional firewalls in their control panel
   - Check Hostinger control panel for firewall rules

### Docker Containers Not Starting

```bash
# Check logs
docker compose logs

# Check disk space
df -h

# Check Docker daemon
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker
```

### Nginx 502 Bad Gateway

```bash
# Check if containers are running
docker compose ps

# Check if containers are accessible from host
curl http://localhost:8080
curl http://localhost:5001/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### SSL Certificate Issues

```bash
# Check certificate exists
sudo ls -la /etc/letsencrypt/live/srv1186603.hstgr.cloud/

# Test certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew
```

### Model Not Loading

```bash
# Check model file exists
ls -lh ~/ai-news-tracker/app/models/

# Check .env file
cat .env | grep LLM

# Check container logs
docker compose logs python-app | grep -i model
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :80
sudo lsof -i :443
sudo lsof -i :8080

# Kill process if needed
sudo kill -9 <PID>
```

### Permission Issues

```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER ~/ai-news-tracker
```

---

## Useful Commands Reference

### Docker Compose

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart specific service
docker compose restart python-app

# View logs
docker compose logs -f

# Rebuild after changes
docker compose build --no-cache
docker compose up -d
```

### Nginx

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

### Firewall

```bash
# Check status
sudo ufw status verbose

# Allow port
sudo ufw allow 80/tcp

# Delete rule
sudo ufw delete allow 80/tcp

# Disable firewall (not recommended)
sudo ufw disable
```

### System

```bash
# Check disk space
df -h

# Check memory
free -h

# Check running processes
ps aux | grep docker
ps aux | grep nginx

# Check system logs
sudo journalctl -xe
```

---

## Security Checklist

- [ ] UFW firewall enabled with only necessary ports open
- [ ] Docker containers bound to localhost only (127.0.0.1)
- [ ] Nginx reverse proxy handling external traffic
- [ ] SSL/HTTPS enabled with valid certificates
- [ ] Strong passwords for n8n and any other services
- [ ] SSH key authentication enabled (disable password auth)
- [ ] Regular system updates scheduled
- [ ] SSL certificate auto-renewal configured
- [ ] Logs monitored regularly
- [ ] Backups configured (if needed)

---

## Next Steps

1. Configure domain DNS (if using custom domain)
2. Set up monitoring/alerting
3. Configure automated backups
4. Set up log rotation
5. Review and harden security settings
6. Test all functionality end-to-end

---

## Support

For issues specific to:
- **Docker**: Check `docker compose logs`
- **Nginx**: Check `/var/log/nginx/error.log`
- **Application**: Check application logs in `app/logs/`
- **System**: Check `sudo journalctl -xe`
