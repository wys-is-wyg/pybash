# Build and Development Guide

Complete guide for building, running, and developing the AI News Tracker application.

## Table of Contents

- [Initial Setup](#initial-setup)
- [Docker Build and Start](#docker-build-and-start)
- [Cache Clearing and Rebuilds](#cache-clearing-and-rebuilds)
- [Starting Services](#starting-services)
- [CSS Building](#css-building)
- [Accessing the Application](#accessing-the-application)
- [Troubleshooting](#troubleshooting)

## Initial Setup

### Prerequisites

- Docker and Docker Compose installed
- WSL2 Ubuntu (for Windows users)
- `.env` file configured with required environment variables

### First-Time Build

Build all Docker images:

```bash
docker-compose build
```

Start all services:

```bash
docker-compose up -d
```

Verify all containers are running:

```bash
docker-compose ps
```

Expected output should show three services:
- `ai-news-python` (Python Flask API)
- `ai-news-web` (Node.js web server)
- `ai-news-n8n` (n8n workflow automation)

## Docker Build and Start

### Full Stack Build and Start

Build and start all services:

```bash
docker-compose up -d --build
```

### Individual Service Build

Build a specific service:

```bash
docker-compose build python-app
docker-compose build web-server
docker-compose build n8n
```

### Start Services

Start all services (assumes images already built):

```bash
docker-compose up -d
```

Start a specific service:

```bash
docker-compose up -d python-app
docker-compose up -d web-server
docker-compose up -d n8n
```

## Cache Clearing and Rebuilds

### When to Clear Cache

**Always use `--no-cache` after:**
- Changes to Dockerfiles
- Changes to `requirements.txt` or `package.json`
- Changes to environment variables or configuration
- When changes aren't appearing despite volume mounts
- After any build-related changes

### Full Rebuild with Cache Clear

Rebuild all services from scratch:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Rebuild Specific Service with Cache Clear

Rebuild a single service:

```bash
# Stop the service
docker-compose stop python-app

# Rebuild without cache
docker-compose build --no-cache python-app

# Start the service
docker-compose up -d python-app
```

**Python App rebuild:**
```bash
docker-compose stop python-app
docker-compose build --no-cache python-app
docker-compose up -d python-app
```

**Web Server rebuild:**
```bash
docker-compose stop web-server
docker-compose build --no-cache web-server
docker-compose up -d web-server
```

### Quick Restart (No Rebuild)

When only configuration or volume-mounted files change:

```bash
docker-compose restart python-app
docker-compose restart web-server
docker-compose restart n8n
```

Or restart all:

```bash
docker-compose restart
```

## Starting Services

### Python Flask Application

The Python app runs automatically when the `python-app` container starts. It uses Gunicorn and listens on port 5001.

**Start Python app:**
```bash
docker-compose up -d python-app
```

**View Python app logs:**
```bash
docker logs -f ai-news-python
```

**Check Python app health:**
```bash
curl http://localhost:5001/health
```

**Restart Python app:**
```bash
docker-compose restart python-app
```

### Web Server

The Node.js web server runs automatically when the `web-server` container starts. It serves on ports 8080 (HTTP) and 8443 (HTTPS).

**Start web server:**
```bash
docker-compose up -d web-server
```

**View web server logs:**
```bash
docker logs -f ai-news-web
```

**Restart web server:**
```bash
docker-compose restart web-server
```

### n8n Workflow Automation

n8n runs automatically when the `n8n` container starts. It serves on port 5678.

**Start n8n:**
```bash
docker-compose up -d n8n
```

**View n8n logs:**
```bash
docker logs -f ai-news-n8n
```

## CSS Building

This project uses **Tailwind CSS v4** for styling. The CSS is built from a source file into the public directory.

### Source and Output Files

- **Source**: `web/src/input.css` (Tailwind imports + custom CSS)
- **Output**: `web/public/css/style.css` (compiled CSS)

### Build CSS in Docker Container (Recommended)

Since Tailwind is a dev dependency, install dev dependencies first:

```bash
# Install dev dependencies (includes Tailwind)
docker exec ai-news-web npm install --include=dev

# Build CSS
docker exec ai-news-web npm run build:css
```

Or as a one-liner:
```bash
docker exec ai-news-web sh -c "npm install --include=dev && npm run build:css"
```

### Build CSS Locally (WSL)

If you have Node.js installed in WSL:

```bash
# In WSL bash (not PowerShell)
cd ~/projects/pybash/web
npm install  # Only needed first time
npm run build:css
```

**Note**: Make sure you're in WSL bash, not Windows PowerShell, when running npm commands.

### Watch Mode (Development)

For automatic rebuilding when you edit CSS:

**Locally:**
```bash
cd web
npm run watch:css
```

**In Docker:**
```bash
docker exec -it ai-news-web npm run watch:css
```

This will watch `src/input.css` and automatically rebuild when you save changes.

### After Building CSS

1. **Hard refresh your browser** (Ctrl+Shift+R) to see changes
2. **No container restart needed** - CSS is served as static files

### CSS Troubleshooting

**"tailwindcss: command not found"**

Install dependencies first:
```bash
cd web
npm install
```

**Changes not showing?**

1. Hard refresh browser (Ctrl+Shift+R)
2. Clear browser cache
3. Check that `public/css/style.css` was updated (check file timestamp)

**Need to rebuild after editing `src/input.css`?**

Yes! Always run `npm run build:css` after editing the source file.

## Accessing the Application

### HTTP (Port 8080)

- **URL**: `http://localhost:8080`
- **Feed**: `http://localhost:8080/`
- **Video Ideas**: `http://localhost:8080/video-ideas`
- **Output**: `http://localhost:8080/output`
- **Dashboard**: `http://localhost:8080/dashboard`
- **Rationale**: `http://localhost:8080/rationale`

### HTTPS (Port 8443)

- **URL**: `https://localhost:8443`
- **Feed**: `https://localhost:8443/`
- **Video Ideas**: `https://localhost:8443/video-ideas`
- **Output**: `https://localhost:8443/output`
- **Dashboard**: `https://localhost:8443/dashboard`
- **Rationale**: `https://localhost:8443/rationale`

### n8n Dashboard

- **URL**: `http://localhost:5678`
- **Default Username**: `admin`
- **Default Password**: Set in `.env` as `N8N_AUTH_PASSWORD` (default: `changeme`)

### Python API

- **Health Check**: `http://localhost:5001/health`
- **News Feed**: `http://localhost:5001/api/news`
- **Refresh Feed**: `POST http://localhost:5001/api/refresh`

## Troubleshooting

### View Logs

Monitor container logs in real-time:

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f ai-news-python
docker logs -f ai-news-web
docker logs -f ai-news-n8n
```

Press `Ctrl+C` to stop following logs.

### Browser Cache Issues

If you see old navigation links or content:

1. **Hard Refresh**:
   - **Chrome/Edge**: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
   - **Firefox**: `Ctrl + F5` (Windows) or `Cmd + Shift + R` (Mac)

2. **Clear Cache**:
   - Open DevTools (F12)
   - Right-click the refresh button
   - Select "Empty Cache and Hard Reload"

3. **Incognito/Private Mode**:
   - Open a new incognito window
   - Access `http://localhost:8080` or `https://localhost:8443`

### SSL Errors

**Error: "ERR_SSL_PROTOCOL_ERROR" or "Invalid Response"**

**Solution**: Make sure you're using the correct port:
- ✅ **HTTPS**: `https://localhost:8443` (port 8443)
- ❌ **NOT**: `https://localhost:8080` (port 8080 is HTTP only)

**Error: "Your connection is not private" (Self-signed certificate)**

This is **normal** for development. To proceed:

1. Click **"Advanced"** or **"Show Details"**
2. Click **"Proceed to localhost"** or **"Accept the Risk"**
3. The browser will remember this choice

**If HTTPS Still Doesn't Work**

1. **Check if HTTPS server is running**:
   ```bash
   docker logs ai-news-web | grep HTTPS
   ```
   Should show: `HTTPS server running on port 8443`

2. **Verify SSL certificates exist**:
   ```bash
   docker exec ai-news-web ls -la /app/ssl/
   ```
   Should show `cert.pem` and `key.pem`

3. **Regenerate SSL certificates** (if needed):
   ```bash
   cd web
   bash generate-ssl.sh
   docker-compose restart web-server
   ```

### Container Issues

**Container won't start?**

1. Check logs: `docker logs <container-name>`
2. Verify environment variables in `.env`
3. Check port conflicts: `netstat -tulpn | grep <port>`
4. Rebuild with cache clear: `docker-compose build --no-cache <service>`

**Changes not appearing?**

1. For volume-mounted files (CSS, JS, HTML):
   - Hard refresh browser (Ctrl+Shift+R)
   - Restart container: `docker restart <container-name>`

2. For code changes in containers:
   - Rebuild with `--no-cache`: `docker-compose build --no-cache <service>`
   - Restart: `docker-compose up -d <service>`

**Python app not responding?**

1. Check health endpoint: `curl http://localhost:5001/health`
2. View logs: `docker logs ai-news-python`
3. Verify Python app is running: `docker ps | grep ai-news-python`
4. Restart: `docker-compose restart python-app`

**Routes return 404?**

1. Check server.js has the route defined
2. Restart container: `docker-compose restart web-server`
3. Check logs for errors: `docker logs ai-news-web`

### Quick Reference

```bash
# Full rebuild (cache clear)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Rebuild specific service
docker-compose build --no-cache <service>
docker-compose up -d <service>

# Restart service
docker-compose restart <service>

# View logs
docker logs -f <container-name>

# Build CSS
docker exec ai-news-web npm run build:css

# Check health
curl http://localhost:5001/health
curl http://localhost:8080
```
