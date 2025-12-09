# VPS Setup Instructions

## Quick Setup Guide

### Step 1: Choose Project Location

**Recommended locations:**
- `/home/ubuntu/ai-news-tracker` - For ubuntu user (recommended)
- `/home/deploy/ai-news-tracker` - For dedicated deploy user
- `/opt/ai-news-tracker` - For system-wide installation (requires root)

**Best Practice:** Use a non-root user (like `ubuntu`) and place project in their home directory.

### Step 2: Upload Project Files

From your **local machine** (WSL2/Ubuntu):

```bash
cd deployment/vps-setup
chmod +x upload-to-vps.sh

# Upload to ubuntu user's home directory (recommended)
./upload-to-vps.sh ubuntu srv1186603.hstgr.cloud ~/ai-news-tracker

# Or upload to root (not recommended, but works)
./upload-to-vps.sh root srv1186603.hstgr.cloud ~/ai-news-tracker
```

### Step 3: SSH into VPS and Switch to Non-Root User

```bash
# SSH as root (or ubuntu if you have key access)
ssh root@srv1186603.hstgr.cloud

# If logged in as root, switch to ubuntu user
su - ubuntu

# Or if you have SSH key for ubuntu, connect directly:
# ssh ubuntu@srv1186603.hstgr.cloud
```

### Step 4: Run Installation Script

```bash
# Navigate to project directory
cd ~/ai-news-tracker

# Make script executable
chmod +x deployment/vps-setup/vps-install.sh

# Run installation (as non-root user with sudo)
bash deployment/vps-setup/vps-install.sh srv1186603.hstgr.cloud
```

### Step 5: Complete Setup

```bash
# Create .env file
nano .env
# Add your configuration

# Download LLM model
bash app/scripts/download_model.sh

# Build and start containers
docker compose build --no-cache
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

---

## If You're Currently Logged in as Root

If you're already logged in as root (like in your current session):

### Option 1: Switch to Ubuntu User (Recommended)

```bash
# Switch to ubuntu user
su - ubuntu

# Create project directory
mkdir -p ~/ai-news-tracker
cd ~/ai-news-tracker

# Then upload files from local machine to this location:
# ./upload-to-vps.sh ubuntu srv1186603.hstgr.cloud ~/ai-news-tracker
```

### Option 2: Upload to Root, Then Move

```bash
# As root, create directory
mkdir -p /root/ai-news-tracker

# Upload from local machine:
# ./upload-to-vps.sh root srv1186603.hstgr.cloud ~/ai-news-tracker

# Then move to ubuntu user (better security)
mv /root/ai-news-tracker /home/ubuntu/
chown -R ubuntu:ubuntu /home/ubuntu/ai-news-tracker

# Switch to ubuntu user
su - ubuntu
cd ~/ai-news-tracker
```

### Option 3: Use Root (Not Recommended, But Works)

If you must use root:

```bash
# Stay as root
cd /root/ai-news-tracker

# Upload from local:
# ./upload-to-vps.sh root srv1186603.hstgr.cloud ~/ai-news-tracker

# Run installation (script will warn but allow)
bash deployment/vps-setup/vps-install.sh srv1186603.hstgr.cloud
```

**Note:** The installation script will warn if run as root, but you can proceed if needed.

---

## Directory Structure

After setup, your project should be at:

```
/home/ubuntu/ai-news-tracker/     # Recommended
├── app/
├── web/
├── n8n/
├── deployment/
├── docker-compose.yml
├── .env
└── ...
```

---

## Permissions

Ensure proper permissions:

```bash
# If files are owned by root, fix ownership:
sudo chown -R ubuntu:ubuntu ~/ai-news-tracker

# Ensure scripts are executable:
chmod +x deployment/vps-setup/*.sh
chmod +x app/scripts/*.sh
```

---

## Troubleshooting

### "Permission denied" when running docker commands

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker  # or log out and back in
```

### "Cannot access /home/ubuntu/ai-news-tracker"

```bash
# Check if directory exists
ls -la /home/ubuntu/

# Create if needed
mkdir -p /home/ubuntu/ai-news-tracker
chown ubuntu:ubuntu /home/ubuntu/ai-news-tracker
```

### Files uploaded to wrong location

```bash
# Find where files were uploaded
find / -name "docker-compose.yml" 2>/dev/null

# Move to correct location
mv /path/to/project /home/ubuntu/ai-news-tracker
chown -R ubuntu:ubuntu /home/ubuntu/ai-news-tracker
```

