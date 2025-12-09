# Quick Upload Guide

## Current Situation

You're SSH'd into VPS but need to upload files FROM your local machine.

**Solution:** Open a **new terminal window** on your local machine (not SSH'd) and run upload commands from there.

---

## Method 1: Use Upload Script (Easiest)

### Step 1: Open New Terminal Locally

- **Windows:** Open a new Git Bash window (or PowerShell/WSL)
- **Don't SSH** - stay on your local machine

### Step 2: Navigate to Project and Run Script

```bash
# Navigate to project root
cd /c/path/to/pybash  # Adjust path for your Windows location
# Or if in WSL:
cd ~/projects/pybash

# Run upload script
cd deployment/vps-setup
chmod +x upload-to-vps.sh
./upload-to-vps.sh ubuntu srv1186603.hstgr.cloud ~/ai-news-tracker
```

---

## Method 2: Manual SCP (If Script Doesn't Work)

### Step 1: Open New Terminal Locally

Open a new Git Bash window (stay local, don't SSH).

### Step 2: Create Archive Locally

```bash
# Navigate to project root
cd /c/path/to/pybash  # Your actual project path

# Create tar archive (excludes unnecessary files)
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
```

**Note:** In Git Bash, `/tmp` might not exist. Use a Windows temp location:

```bash
# For Git Bash on Windows, use:
tar ... -czf /c/temp/ai-news-tracker.tar.gz .
# Or:
tar ... -czf ~/ai-news-tracker.tar.gz .
```

### Step 3: Upload Archive

```bash
# Upload to VPS
scp ~/ai-news-tracker.tar.gz ubuntu@srv1186603.hstgr.cloud:/tmp/

# Or if using root:
scp ~/ai-news-tracker.tar.gz root@srv1186603.hstgr.cloud:/tmp/
```

### Step 4: Extract on VPS

In your **SSH session** (the terminal where you're already connected):

```bash
# You should already be SSH'd in, so just run:
mkdir -p ~/ai-news-tracker
cd ~/ai-news-tracker
tar -xzf /tmp/ai-news-tracker.tar.gz
rm /tmp/ai-news-tracker.tar.gz

# Verify files
ls -la
```

---

## Method 3: Using rsync (If Available)

From **new local terminal** (not SSH'd):

```bash
cd /c/path/to/pybash

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
    ./ ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
```

---

## Method 4: Create Zip and Upload via File Manager

### Step 1: Create Zip Locally

In **new local terminal**:

```bash
cd /c/path/to/pybash

# Create zip (Git Bash has zip)
zip -r ai-news-tracker.zip . \
    -x "*.git/*" \
    -x "*node_modules/*" \
    -x "*__pycache__/*" \
    -x "*.pyc" \
    -x ".env" \
    -x "app/models/*.gguf" \
    -x "app/models/models--*" \
    -x "app/data/*.json" \
    -x "app/logs/*.log" \
    -x "web/ssl/*.pem" \
    -x "web/ssl/*.key"
```

### Step 2: Upload via Hostinger File Manager

1. Log into Hostinger control panel
2. Go to File Manager
3. Navigate to `/home/ubuntu/`
4. Upload `ai-news-tracker.zip`
5. Extract via file manager or SSH

### Step 3: Extract on VPS

In your **SSH session**:

```bash
cd ~/ai-news-tracker
unzip ai-news-tracker.zip
rm ai-news-tracker.zip
```

---

## Quick Reference: Two Terminal Setup

**Terminal 1 (SSH'd into VPS):**
- Use for: Running commands on VPS, checking files, installation

**Terminal 2 (Local, NOT SSH'd):**
- Use for: Uploading files, creating archives, running SCP/rsync

---

## After Upload

Once files are uploaded, in your **SSH session** (Terminal 1):

```bash
cd ~/ai-news-tracker
ls -la  # Verify files

# Make scripts executable
chmod +x deployment/vps-setup/vps-install.sh
chmod +x app/scripts/*.sh

# Create .env file
nano .env

# Run installation
bash deployment/vps-setup/vps-install.sh srv1186603.hstgr.cloud
```

---

## Troubleshooting

### "scp: command not found" in Git Bash

Git Bash should have scp. If not:
- Use WSL2 instead: `wsl` then run commands
- Or use PowerShell with OpenSSH: `scp` should work

### "Permission denied"

```bash
# Make sure you're using the right user
scp file ubuntu@srv1186603.hstgr.cloud:/tmp/
# Or:
scp file root@srv1186603.hstgr.cloud:/tmp/
```

### "Connection refused"

- Check you're running from local machine (not SSH'd)
- Test SSH first: `ssh ubuntu@srv1186603.hstgr.cloud`

