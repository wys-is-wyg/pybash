# Phase 10: Local Development Testing Guide

This document provides step-by-step instructions for testing the AI News Tracker application locally.

## Prerequisites

- Docker and Docker Compose installed and running
- Node.js and npm installed (for local web dependencies)
- Python 3.11+ and pytest installed (for running tests)
- WSL2 Ubuntu terminal (for Windows users)

## Quick Start

Run the automated test script:

```bash
./test-local.sh
```

This script automates steps 37-43 and provides a testing summary.

## Manual Testing Steps

### Step 37: Install Dependencies and Build Images

```bash
# Build Docker images
docker-compose build

# Install Node.js dependencies (for local development)
npm install --prefix web/
```

### Step 38: Start Containers

```bash
docker-compose up -d
```

Verify containers are running:

```bash
docker-compose ps
```

Expected output should show three services: `ai-news-python`, `ai-news-web`, and `ai-news-n8n` all with status "Up".

### Step 39: Verify All Services

Test each service endpoint:

```bash
# Python health check
curl http://localhost:5001/health

# Web server
curl http://localhost:8080

# n8n dashboard
curl http://localhost:5678
```

**Expected Results:**
- Python health: Returns JSON with `{"status": "healthy"}` or similar
- Web server: Returns HTML content (the main page)
- n8n: Returns HTML content (the n8n dashboard login page)

### Step 40: View Logs

Monitor container logs in real-time:

```bash
# Python app logs
docker-compose logs -f python-app

# Web server logs
docker-compose logs -f web-server

# n8n logs
docker-compose logs -f n8n
```

Press `Ctrl+C` to stop following logs.

### Step 41: Test API Endpoints

Test the Flask API endpoints:

```bash
# Get news feed
curl http://localhost:5001/api/news

# Refresh feed (POST request)
curl -X POST http://localhost:5001/api/refresh \
  -H "Content-Type: application/json" \
  -d '{"status":"test"}'
```

**Expected Results:**
- `/api/news`: Returns JSON array (may be empty `[]` if no data yet)
- `/api/refresh`: Returns success status (200 or 201)

### Step 42: Open Web UI

Open your browser and navigate to:

```
http://localhost:8080
```

You should see:
- The AI News Tracker homepage
- Navigation menu with sections: Feed, Dashboard, Rationale, Video Ideas, Output Feed
- Feed container (may show "No items available" if pipeline hasn't run yet)

### Step 43: Run API Tests

Run the pytest test suite:

```bash
cd ~/projects/pybash
pytest app/tests/test_api.py -v
```

**Expected Results:**
- All tests should pass
- Test output shows test names and status (PASSED/FAILED)

## Troubleshooting

### Containers Not Starting

If containers fail to start:

1. Check Docker is running: `docker ps`
2. Check for port conflicts: `netstat -tuln | grep -E '5001|8080|5678'`
3. View error logs: `docker-compose logs`
4. Rebuild images: `docker-compose build --no-cache`

### Services Not Responding

If services don't respond:

1. Check container status: `docker-compose ps`
2. Check container logs: `docker-compose logs <service-name>`
3. Verify environment variables: Check `.env` file exists and has required values
4. Restart containers: `docker-compose restart`

### API Tests Failing

If pytest tests fail:

1. Ensure you're in the project root directory
2. Install test dependencies: `pip install pytest pytest-cov requests-mock`
3. Check Python path: `python --version` (should be 3.11+)
4. Run with verbose output: `pytest app/tests/test_api.py -v -s`

### Web UI Not Loading

If the web UI doesn't load:

1. Check web-server container: `docker-compose logs web-server`
2. Verify port 8080 is accessible: `curl http://localhost:8080`
3. Check browser console for JavaScript errors
4. Verify static files are being served correctly

## Next Steps

After successful local testing:

1. **Phase 11**: Configure n8n workflows
2. **Phase 12**: Set up cron automation
3. **Phase 13-14**: Prepare for VPS deployment

## Additional Resources

- Docker Compose documentation: https://docs.docker.com/compose/
- Flask API documentation: See `app/main.py`
- n8n documentation: https://docs.n8n.io/

