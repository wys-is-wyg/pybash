# VPS Setup Scripts

Scripts to automate VPS deployment of AI News Tracker.

## Quick Start

### Prerequisites

**The upload script requires SSH access to your VPS.** If you don't have SSH set up:

1. **Test SSH connection first:**
   ```bash
   ssh ubuntu@srv1186603.hstgr.cloud
   # Or: ssh root@srv1186603.hstgr.cloud
   ```

2. **If SSH doesn't work**, see `MANUAL_UPLOAD.md` for alternative methods (file manager, SFTP client, etc.)

3. **If SSH works**, proceed with the upload script below.

### 1. Upload Project to VPS

From your **local machine** (WSL2/Ubuntu):

```bash
cd deployment/vps-setup
chmod +x upload-to-vps.sh
./upload-to-vps.sh [username] [hostname] [destination-path]
```

**Note:** The script uses SSH/SCP/rsync, so SSH must be working. If you get connection errors, see `MANUAL_UPLOAD.md`.

**Examples:**
```bash
# Default (root@srv1186603.hstgr.cloud:~/ai-news-tracker)
./upload-to-vps.sh

# Custom user and host
./upload-to-vps.sh deploy srv1186603.hstgr.cloud ~/ai-news-tracker

# With IP address
./upload-to-vps.sh root 192.168.1.100 ~/ai-news-tracker
```

**What gets uploaded:**
- All project files
- Excludes: `.git`, `node_modules`, `__pycache__`, `.env`, model files, logs

**What you need to do manually:**
- Create `.env` file on VPS with your configuration
- Download LLM model (after installation)

### 2. Run Installation Script on VPS

SSH into your VPS:

```bash
ssh user@your-vps-host
cd ~/ai-news-tracker
chmod +x deployment/vps-setup/vps-install.sh
bash deployment/vps-setup/vps-install.sh [domain]
```

**Examples:**
```bash
# Default domain (srv1186603.hstgr.cloud)
bash deployment/vps-setup/vps-install.sh

# Custom domain
bash deployment/vps-setup/vps-install.sh yourdomain.com
```

**What the script does:**
1. Updates system packages
2. Installs Docker, Docker Compose, Nginx, Certbot
3. Configures UFW firewall (ports 22, 80, 443)
4. Secures Docker ports (binds to localhost only)
5. Sets up Nginx reverse proxy
6. Optionally sets up SSL/HTTPS with Let's Encrypt

### 3. Complete Setup

After installation script completes:

```bash
# Navigate to project
cd ~/ai-news-tracker

# Create .env file (if not uploaded)
nano .env
# Add your configuration (see .env.example or docs)

# Download LLM model (~2.3GB, takes time)
bash app/scripts/download_model.sh

# Build and start containers
docker compose build --no-cache
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

## Manual Upload (Alternative)

If you prefer to upload manually or the script doesn't work:

### Using SCP

```bash
# From local machine
scp -r \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='app/models/*.gguf' \
  . user@vps-host:~/ai-news-tracker/
```

### Using SFTP

```bash
sftp user@vps-host
cd ~/ai-news-tracker
put -r local-project-directory/*
```

## Troubleshooting

### Upload Script Issues

**"Permission denied"**
- Check SSH key is set up: `ssh-keygen -t ed25519`
- Copy key to VPS: `ssh-copy-id user@vps-host`
- Or use password authentication

**"rsync: command not found"**
- Script will fall back to scp/tar method
- Or install rsync: `sudo apt install rsync`

**"Connection timeout"**
- Check VPS is running and accessible
- Verify firewall allows SSH (port 22)
- Check VPS IP/hostname is correct

### Installation Script Issues

**"Docker permission denied"**
- Script adds user to docker group
- Run: `newgrp docker` or log out/in
- Or use: `sudo docker compose ...`

**"Nginx configuration error"**
- Check domain name is correct
- Verify DNS points to VPS IP
- For Let's Encrypt, domain must resolve

**"Port already in use"**
- Check what's using the port: `sudo lsof -i :80`
- Stop conflicting service or change ports

**"SSL certificate failed"**
- Ensure domain DNS points to VPS
- Port 80 must be accessible for verification
- Can skip SSL and set up later

## Files

- `vps-install.sh` - Main installation script (run on VPS)
- `upload-to-vps.sh` - Upload script (run on local machine)
- `README.md` - This file

## Security Notes

- Script binds Docker containers to localhost only (127.0.0.1)
- UFW firewall configured with minimal ports (22, 80, 443)
- Nginx acts as reverse proxy (no direct container access)
- SSL/HTTPS recommended for production
- `.env` file not uploaded (create manually on VPS)

## Next Steps After Installation

1. **Verify services:**
   ```bash
   curl http://localhost:8080
   curl http://localhost:5001/health
   ```

2. **Check Nginx:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

3. **View logs:**
   ```bash
   docker compose logs -f
   sudo tail -f /var/log/nginx/error.log
   ```

4. **Set up automation:**
   - Systemd timers (see `deployment/systemd/`)
   - Cron jobs (see `deployment/cron-setup.sh`)

5. **Monitor:**
   - Set up log rotation
   - Configure monitoring/alerting
   - Set up backups

## Support

See `docs/VPS_DEPLOYMENT.md` for detailed manual instructions and troubleshooting.

