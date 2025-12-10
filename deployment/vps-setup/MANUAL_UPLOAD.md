# Manual Upload Methods

## Method 1: Manual SCP (Command Line)

### Step 1: Create Archive Locally

From your **local terminal** (not SSH'd):

```bash
cd ~/projects/pybash

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
    -czf ~/project.tar.gz .
```

### Step 2: Upload Archive

```bash
# Upload to VPS (will prompt for password)
scp ~/project.tar.gz ubuntu@srv1186603.hstgr.cloud:/tmp/

# Or if using root:
scp ~/project.tar.gz root@srv1186603.hstgr.cloud:/tmp/
```

### Step 3: Extract on VPS

In your **SSH session**:

```bash
mkdir -p ~/ai-news-tracker
cd ~/ai-news-tracker
tar -xzf /tmp/project.tar.gz
rm /tmp/project.tar.gz
ls -la  # Verify files
```

---

## Method 2: Direct SCP (No Archive)

From **local terminal**:

```bash
cd ~/projects/pybash

# Upload directories one by one
scp -r app ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp -r web ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp -r n8n ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp -r deployment ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp docker-compose.yml ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp Dockerfile.python ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
scp Dockerfile.web ubuntu@srv1186603.hstgr.cloud:~/ai-news-tracker/
```

---

## Method 3: Create Zip and Upload via File Manager

### Step 1: Create Zip Locally

```bash
cd ~/projects/pybash

zip -r project.zip . \
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
4. Upload `project.zip`
5. Extract via file manager or SSH

### Step 3: Extract on VPS (if via SSH)

```bash
cd ~/ai-news-tracker
unzip project.zip
rm project.zip
```

---

## After Upload

Once files are on VPS, in your **SSH session**:

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
