# Build and Development Quick Reference

Quick reference guide for Docker, pipeline, testing, and development commands.

## Docker Commands

**Note:** Docker Compose v2 (plugin) uses `docker compose` (space), while v1 (standalone) uses `docker-compose` (hyphen). Both work identically. On VPS, you likely have v2 plugin installed.

### Full Rebuild (Cache Clear)

```bash
# Docker Compose v2 (plugin) - recommended
docker compose down
docker compose build --no-cache
docker compose up -d

# OR Docker Compose v1 (standalone)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Rebuild Specific Service

```bash
# Docker Compose v2
docker compose build --no-cache <service>
docker compose up -d <service>

# OR Docker Compose v1
docker-compose build --no-cache <service>
docker-compose up -d <service>
```

### Restart Service

```bash
# Docker Compose v2
docker compose restart <service>
# Or restart all:
docker compose restart

# OR Docker Compose v1
docker-compose restart <service>
docker-compose restart
```

### View Logs

```bash
# All services (v2)
docker compose logs -f

# All services (v1)
docker-compose logs -f

# Specific service (works with both)
docker logs -f ai-news-python
docker logs -f ai-news-web
docker logs -f ai-news-n8n
```

### Service Status

```bash
# Docker Compose v2
docker compose ps

# OR Docker Compose v1
docker-compose ps

# Direct Docker command (works with both)
docker ps | grep ai-news
```

## Pipeline Commands

### Run Full Pipeline

```bash
# Production mode (30 articles default)
bash app/scripts/run_pipeline.sh

# Test mode (5 articles, no images)
bash app/scripts/run_pipeline.sh --test

# Custom limit
bash app/scripts/run_pipeline.sh --limit 10

# With image limit
bash app/scripts/run_pipeline.sh --limit 10 --image-limit 5
```

### Trigger Pipeline via n8n Webhook

```bash
# Manual trigger
bash app/scripts/webhook_trigger.sh

# Cron trigger
bash app/scripts/webhook_trigger.sh "cron"

# With metadata
bash app/scripts/webhook_trigger.sh "manual" "user:admin"
```

### Individual Pipeline Steps

```bash
# RSS Scraper
docker exec ai-news-python python3 /app/app/scripts/rss_scraper.py

# Summarizer (reads from stdin or file)
docker exec -i ai-news-python python3 /app/app/scripts/summarizer.py < app/data/raw_news.json

# Video Idea Generator
docker exec -i ai-news-python python3 /app/app/scripts/video_idea_generator.py < app/data/summaries.json

# Data Manager (merge into feed.json)
docker exec ai-news-python python3 /app/app/scripts/data_manager.py --limit 30

# Generate Tag Images
bash app/scripts/generate_tag_images.sh
bash app/scripts/generate_tag_images.sh --limit 20
```

### Pipeline via API

```bash
# Refresh feed (merges data files)
curl -X POST http://localhost:5001/api/refresh

# Trigger pipeline via n8n webhook (if configured)
curl -X POST http://localhost:5678/webhook/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"trigger_source":"manual","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

## Test Commands

### Run API Tests

```bash
# All tests
pytest app/tests/test_api.py -v

# With coverage
pytest app/tests/test_api.py -v --cov=app

# Specific test
pytest app/tests/test_api.py::test_health_endpoint -v

# Verbose output
pytest app/tests/test_api.py -v -s
```

### Test Summarizer

```bash
# Test first article
bash app/scripts/test_summarizer.sh

# Test specific article
bash app/scripts/test_summarizer.sh 5

# Test multiple articles
bash app/scripts/test_summarizer.sh 1 3
```

### Health Checks

```bash
# Python API health
curl http://localhost:5001/health

# Web server
curl http://localhost:8080

# n8n dashboard
curl http://localhost:5678

# News feed endpoint
curl http://localhost:5001/api/news
```

## Development Commands

### Build CSS

```bash
# In Docker container
docker exec ai-news-web npm run build:css

# Install dev dependencies first (if needed)
docker exec ai-news-web npm install --include=dev

# Watch mode (auto-rebuild on changes)
docker exec -it ai-news-web npm run watch:css
```

### Access Application URLs

```bash
# HTTP
http://localhost:8080

# HTTPS
https://localhost:8443

# n8n Dashboard
http://localhost:5678

# Python API
http://localhost:5001/health
http://localhost:5001/api/news
```

### View Data Files

```bash
# List data files
ls -la app/data/

# View feed
cat app/data/feed.json | jq .

# View display data
cat app/data/display.json | jq .

# View pipeline logs
ls -la app/logs/
tail -f app/logs/pipeline_*.log
```

### Python Script Execution

```bash
# Run Python script in container
docker exec ai-news-python python3 /app/app/scripts/<script>.py

# Run with stdin input
docker exec -i ai-news-python python3 /app/app/scripts/<script>.py < input.json

# Interactive Python shell
docker exec -it ai-news-python python3
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs <container-name>

# Check port conflicts
netstat -tulpn | grep -E '5001|8080|5678'

# Rebuild with cache clear (v2)
docker compose build --no-cache <service>

# OR (v1)
docker-compose build --no-cache <service>
```

### Changes Not Appearing

```bash
# For volume-mounted files (CSS, JS, HTML)
# Hard refresh browser (Ctrl+Shift+R)
# Or restart container
docker restart <container-name>

# For code changes in containers (v2)
docker compose build --no-cache <service>
docker compose up -d <service>

# OR (v1)
docker-compose build --no-cache <service>
docker-compose up -d <service>
```

### Pipeline Errors

```bash
# Check pipeline logs
tail -f app/logs/pipeline_*.log

# Check execution log
cat app/data/pipeline_execution.log

# Verify data files exist
ls -la app/data/*.json

# Test individual steps
bash app/scripts/test_summarizer.sh
```
