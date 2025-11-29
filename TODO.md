# AI News Tracker and Video Idea Generator - TODO.md

## Prerequisites: WSL2 Setup (Windows Development)

**For Windows developers using WSL2:**

0. Ensure WSL2 is configured:
   - Verify in PowerShell: `wsl --list --verbose` (should show Ubuntu with VERSION 2)
   - Enable Docker Desktop WSL2 integration: Docker Desktop Settings → Resources → WSL Integration → toggle ON for Ubuntu
   - Test in WSL2 bash: `docker --version` and `docker-compose --version`
   - All subsequent commands run in WSL2 bash terminal (accessible via `wsl` from PowerShell or Windows Terminal → Ubuntu)
   - Create project in WSL2 native filesystem (`~/projects/`) for best Docker performance

**For Linux VPS deployment:**
- All commands below work identically in bash on the Linux host

---

## Phase 1: Project Structure and Initial Setup

1. Create project structure:
   ```bash
   mkdir -p ~/projects/ai-news-tracker/{app/{scripts,config,data,logs},web/{public/{css,js},src},n8n/{workflows,data},deployment/vps-setup}
   cd ~/projects/ai-news-tracker
   git init
   ```

2. Create `.gitignore` with entries: `*.pyc`, `__pycache__/`, `.env`, `node_modules/`, `data/*.json`, `logs/*.log`, `.DS_Store`, `venv/`

3. Create `.env.example` template with placeholders:
   ```
   LEONARDO_API_KEY=your_key_here
   N8N_API_KEY=your_key_here
   N8N_AUTH_PASSWORD=your_password_here
   PYTHON_APP_PORT=5001
   WEB_PORT=8080
   N8N_PORT=5678
   ```

4. Copy to `.env` and fill in actual values: `cp .env.example .env`

## Phase 2: Python App - Core Configuration and Scripts

5. Create `app/config/settings.py` with configuration class containing:
   - Leonardo API endpoint and model defaults
   - List of RSS feed URLs to scrape
   - File paths for data directories
   - Logging configuration
   - Batch processing parameters

6. Create `app/config/__init__.py` (empty file for package initialization)

7. Create `app/scripts/__init__.py` (empty file for package initialization)

8. Create `app/scripts/rss_scraper.py` with function skeletons:
   - `fetch_rss_feeds(feed_urls: list) -> list`
   - `parse_feed_entries(entries: list) -> list`
   - `save_raw_news(news_items: list, output_file: str) -> None`
   - Command-line execution for direct invocation

9. Create `app/scripts/social_media_scraper.py` with function skeleton:
   - `fetch_twitter_ai_news(hashtags: list) -> list` (placeholder for future implementation)

10. Create `app/scripts/summarizer.py` with function skeletons:
    - `summarize_article(text: str, max_words: int = 150) -> str`
    - `batch_summarize_news(news_items: list) -> list`
    - Integration with chosen summarization library (transformers, etc.)

11. Create `app/scripts/video_idea_generator.py` with function skeletons:
    - `generate_video_ideas(summaries: list) -> list`
    - `format_video_idea(title: str, description: str, source: str) -> dict`

12. Create `app/scripts/leonardo_api.py` with function skeletons:
    - `initialize_leonardo_client(api_key: str)` – sets up client with API key
    - `generate_thumbnail(prompt: str, model_id: str = "default") -> dict` – POST request to Leonardo API with prompt, returns generation_id
    - `get_generation_status(generation_id: str) -> dict` – polls generation status until complete
    - `download_generated_image(image_url: str, save_path: str) -> bool` – downloads finished image to local file
    - `batch_generate_thumbnails(video_ideas: list, output_dir: str) -> list` – orchestrates batch thumbnail generation with retry/rate-limit handling

13. Create `app/scripts/data_manager.py` with function skeletons:
    - `load_json(file_path: str) -> dict`
    - `save_json(data: dict, file_path: str) -> None`
    - `merge_feeds(news_items: list, video_ideas: list, thumbnails: list) -> list` – combines all data into unified structure
    - `generate_feed_json(merged_data: list, output_file: str) -> None` – outputs final feed.json

14. Create `app/scripts/logger.py` with logging setup:
    - Console and file handlers
    - Log level configuration via environment variable
    - Logs directory: `app/logs/`

15. Create `app/requirements.txt` with dependencies:
    ```
    flask
    requests
    feedparser
    transformers
    python-dotenv
    gunicorn
    aiohttp
    ```

## Phase 3: Python App - Main Application

16. Create `app/main.py` with Flask initialization and endpoints:
    - Health check endpoint: `@app.route('/health', methods=['GET'])`
    - News feed endpoint: `@app.route('/api/news', methods=['GET'])` – returns current feed.json
    - Refresh trigger: `@app.route('/api/refresh', methods=['POST'])` – accepts merged feed data and updates feed.json
    - Individual pipeline endpoints: `/api/scrape`, `/api/summarize`, `/api/generate-ideas`, `/api/generate-thumbnails` for n8n calls
    - n8n webhook receiver: `@app.route('/webhook/n8n', methods=['POST'])` – captures workflow completion callbacks
    - CORS setup for web frontend
    - Error handling and JSON responses

## Phase 4: Bash Orchestration and Cron

17. Create `app/scripts/run_pipeline.sh` (executable):
    ```bash
    #!/bin/bash
    set -euo pipefail
    source /app/.env
    LOG_FILE="/app/logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
    
    {
      echo "Starting pipeline..."
      python /app/scripts/rss_scraper.py > /app/data/raw_news.json
      python /app/scripts/summarizer.py < /app/data/raw_news.json > /app/data/summaries.json
      python /app/scripts/video_idea_generator.py < /app/data/summaries.json > /app/data/video_ideas.json
      python /app/scripts/leonardo_api.py < /app/data/video_ideas.json > /app/data/thumbnails.json
      python /app/scripts/data_manager.py
      curl -X POST http://python-app:5001/api/refresh \
        -H "Content-Type: application/json" \
        -d @/app/data/feed.json
      echo "Pipeline completed successfully"
    } 2>&1 | tee -a "$LOG_FILE"
    ```

18. Create `app/scripts/webhook_trigger.sh` (executable):
    ```bash
    #!/bin/bash
    PAYLOAD='{"trigger":"scheduled","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
    curl -X POST "http://n8n:5678/webhook/run-pipeline" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD"
    ```

## Phase 5: Web Frontend - HTML and Assets

19. Create `web/public/index.html` with:
    - HTML5 boilerplate, charset UTF-8, viewport meta tag
    - Title: "AI News Tracker & Video Ideas"
    - Navigation menu with links to: `N8N Dashboard`, `Rationale / Workflow`, `Video Ideas`, `Output Feed`
    - Main feed container: `<div id="feed-container"></div>`
    - Script tag: `<script src="js/app.js"></script>`
    - Link to stylesheet: `<link rel="stylesheet" href="css/style.css">`

20. Create `web/public/css/style.css` with:
    - CSS reset: `*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }`
    - CSS variables for dark theme: `--primary: #0a0e27`, `--accent: #00d9ff`, `--text: #e0e0e0`, `--card-bg: #1a1f3a`
    - Body styles: dark background, sans-serif, smooth transitions
    - Navigation styles: horizontal menu bar, hover effects with accent color
    - Feed container: CSS Grid with responsive columns
    - News card styles: border, padding, shadow, hover scale/lift effect
    - Thumbnail styles: responsive `max-width: 100%`, lazy loading
    - Media query for mobile: `@media (max-width: 768px)` – single column grid

21. Create `web/public/js/app.js` with:
    - `async fetchFeed()` – GET request to `/api/news`, returns feed data
    - `renderFeed(feedData)` – populates feed container with card elements (title, summary, thumbnail, source link)
    - `setupNavigation()` – click handlers for menu items to show/hide corresponding sections
    - Auto-refresh timer: `setInterval(fetchFeed, 300000)` (5 minutes)
    - Error handling: displays user-friendly messages in feed container
    - Initialize on document ready

22. Create `web/public/dashboard.html` with:
    - n8n dashboard iframe: `<iframe src="http://localhost:5678" style="width:100%; height:100vh;"></iframe>`

23. Create `web/public/rationale.html` with:
    - Architecture overview describing scraper → summarizer → video idea generator → thumbnail generation pipeline
    - Automation description: n8n webhook triggers cron/bash scripts
    - Data flow diagram (ASCII or image)

24. Create `web/public/video-ideas.html` with:
    - Section to display video ideas in detail (title, description, suggested thumbnail)
    - Filtering/sorting controls (by date, source, category)
    - Fetch from `/api/news` and filter for video_ideas entries

25. Create `web/public/feed-output.html` with:
    - Raw JSON feed viewer in `<pre>` tag
    - Download button for feed.json
    - Fetch endpoint `/api/news` and display as formatted JSON

## Phase 6: Web Server

26. Create `web/server.js` with:
    - Express app initialization: `const express = require('express'); const app = express();`
    - Static middleware: `app.use(express.static('public'))`
    - CORS middleware: `app.use(cors())`
    - Proxy route for API calls: `app.use('/api', createProxyMiddleware({ target: 'http://python-app:5001', changeOrigin: true }))`
    - Root route: `app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')))`
    - Listen on port from `process.env.WEB_PORT || 8080`

27. Create `web/package.json` with:
    - Dependencies: `express`, `cors`, `express-http-proxy`, `path`
    - Start script: `"start": "node server.js"`
    - Dev script: `"dev": "nodemon server.js"` (optional)

28. Create `web/public/config.js` with API base URL configuration:
    ```javascript
    const API_BASE_URL = process.env.NODE_ENV === 'production' 
      ? 'http://python-app:5001' 
      : 'http://localhost:5001';
    ```

## Phase 7: Dockerfiles

29. Create `Dockerfile.python`:
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    ENV PYTHONUNBUFFERED=1
    COPY app/requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY app/ .
    COPY .env .
    EXPOSE 5001
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:5001/health || exit 1
    CMD ["gunicorn", "--bind", "0.0.0.0:5001", "main:app"]
    ```

30. Create `Dockerfile.web`:
    ```dockerfile
    FROM node:18-alpine
    WORKDIR /app
    COPY web/package*.json ./
    RUN npm ci --only=production
    COPY web/ .
    EXPOSE 8080
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
      CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1
    CMD ["npm", "start"]
    ```

## Phase 8: Docker Compose

31. Create `docker-compose.yml` with services:
    - **python-app**: build `Dockerfile.python`, container name `ai-news-python`, port `5001:5001`, env from `.env`, volumes `./app:/app` and `./data:/app/data`, network `ai-network`, restart `always`
    - **web-server**: build `Dockerfile.web`, container name `ai-news-web`, port `8080:8080`, depends_on `python-app`, network `ai-network`, restart `always`
    - **n8n**: image `n8nio/n8n:latest`, container name `ai-news-n8n`, port `5678:5678`, env vars `N8N_BASIC_AUTH_ACTIVE=true`, `N8N_BASIC_AUTH_USER=admin`, `N8N_BASIC_AUTH_PASSWORD` from `.env`, volume `n8n_data:/home/node/.n8n`, network `ai-network`, restart `always`
    - Named volume: `n8n_data:`
    - Network: `ai-network` (bridge driver)

## Phase 9: Local Development Testing

32. Install dependencies and build images:
    ```bash
    docker-compose build
    npm install --prefix web/
    ```

33. Start containers:
    ```bash
    docker-compose up -d
    ```

34. Verify all services:
    - Python health: `curl http://localhost:5001/health`
    - Web server: `curl http://localhost:8080`
    - n8n: `curl http://localhost:5678` (should return HTML)

35. View logs:
    ```bash
    docker-compose logs -f python-app
    docker-compose logs -f web-server
    docker-compose logs -f n8n
    ```

36. Test API endpoints:
    - News feed: `curl http://localhost:5001/api/news`
    - Refresh trigger: `curl -X POST http://localhost:5001/api/refresh -H "Content-Type: application/json" -d '{"status":"test"}'`

37. Open web UI: navigate to `http://localhost:8080` in browser

## Phase 10: n8n Workflow Configuration

38. Access n8n UI at `http://localhost:5678` (credentials: admin / password from `.env`)

39. Create new workflow named `AI News Pipeline` with nodes:
    - **Webhook trigger**: POST `/webhook/run-pipeline` – entry point
    - **HTTP Request**: GET `http://python-app:5001/api/scrape` – fetch and parse RSS feeds
    - **HTTP Request**: POST `http://python-app:5001/api/summarize` – summarize articles
    - **HTTP Request**: POST `http://python-app:5001/api/generate-ideas` – generate video ideas
    - **HTTP Request**: POST `http://python-app:5001/api/generate-thumbnails` – generate thumbnails via Leonardo API
    - **HTTP Request**: POST `http://python-app:5001/api/refresh` – merge data and update feed.json
    - **Webhook response**: return success status

40. Configure webhook node with `PUT /webhook/run-pipeline` for manual triggering from UI

41. Save and activate workflow

42. Test workflow manually from n8n UI

## Phase 11: Cron and Automation Setup (Local Docker)

43. Create cron job script in host machine crontab (outside container):
    ```bash
    crontab -e
    # Add line: 0 */6 * * * /path/to/projects/ai-news-tracker/app/scripts/run_pipeline.sh
    # Runs every 6 hours
    ```

44. Alternatively, create systemd timer unit (optional, for host scheduling):
    - Unit file: `/etc/systemd/system/ai-news-tracker.service`
    - Timer file: `/etc/systemd/system/ai-news-tracker.timer` with `OnCalendar=*-*-* 00/6:00:00`

## Phase 12: VPS Deployment Preparation

45. Create `deployment/vps-setup/setup.sh` (executable) with steps:
    ```bash
    #!/bin/bash
    set -euo pipefail
    
    # System updates
    sudo apt update && sudo apt upgrade -y
    
    # Install Docker and Docker Compose
    sudo apt install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    newgrp docker
    
    # Create deployment directory
    mkdir -p ~/ai-news-tracker
    
    # Generate SSH keys for VPS CI/CD (if needed)
    ssh-keygen -t ed25519 -f ~/.ssh/vps_deploy -N ""
    ```

46. Create `deployment/vps-setup/README.md` documenting:
    - VPS system requirements: Ubuntu 20.04+, 2GB RAM min, 20GB storage
    - Network ports required: 80 (HTTP), 443 (HTTPS), 5678 (n8n)
    - Recommended: Nginx reverse proxy for HTTPS and load balancing
    - DNS setup instructions
    - Firewall rules (ufw)

## Phase 13: VPS Deployment Script

47. Create `deployment/deploy.sh` (executable):
    ```bash
    #!/bin/bash
    set -euo pipefail
    
    VPS_USER="ubuntu"
    VPS_HOST="your.vps.ip.address"
    DEPLOY_DIR="/home/$VPS_USER/ai-news-tracker"
    
    echo "Deploying to VPS..."
    
    # Copy project files via SCP
    ssh -i ~/.ssh/vps_key $VPS_USER@$VPS_HOST "mkdir -p $DEPLOY_DIR"
    scp -r -i ~/.ssh/vps_key .env $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    scp -r -i ~/.ssh/vps_key app/ $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    scp -r -i ~/.ssh/vps_key web/ $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    scp -r -i ~/.ssh/vps_key n8n/ $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    scp -i ~/.ssh/vps_key docker-compose.yml $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    scp -i ~/.ssh/vps_key Dockerfile.python Dockerfile.web $VPS_USER@$VPS_HOST:$DEPLOY_DIR/
    
    # Execute remote deployment
    ssh -i ~/.ssh/vps_key $VPS_USER@$VPS_HOST << 'EOF'
    cd $DEPLOY_DIR
    docker-compose down --remove-orphans || true
    docker-compose build --no-cache
    docker-compose up -d
    docker-compose ps
    EOF
    
    echo "Deployment complete!"
    ```

48. Create `deployment/vps-commands.md` documenting essential VPS sysadmin commands:
    ```markdown
    # VPS Administration Commands
    
    ## Connect to VPS
    ssh -i ~/.ssh/vps_key ubuntu@your.vps.ip
    
    ## Docker Management
    docker ps                          # List running containers
    docker logs -f container_name      # View live logs
    docker-compose down                # Stop all services
    docker-compose up -d               # Start all services
    docker-compose restart python-app  # Restart specific service
    docker system prune -a             # Clean up unused images
    
    ## File/Data Management
    scp -i key file ubuntu@vps:/path   # Copy file to VPS
    scp -i key ubuntu@vps:/path ./     # Copy file from VPS
    
    ## Monitoring
    df -h                              # Disk usage
    free -h                            # Memory usage
    docker stats                       # Container resource usage
    
    ## Reverse Proxy (Nginx)
    sudo systemctl status nginx        # Check Nginx status
    sudo nginx -t                      # Test Nginx config
    sudo systemctl reload nginx        # Reload config
    
    ## Firewall (ufw)
    sudo ufw status                    # Show firewall rules
    sudo ufw allow 80/tcp              # Allow HTTP
    sudo ufw allow 443/tcp             # Allow HTTPS
    sudo ufw allow 5678/tcp            # Allow n8n
    
    ## Logs
    tail -f /var/log/syslog           # System logs
    docker-compose logs -f --tail=100  # App logs (last 100 lines)
    ```

## Phase 14: Production Nginx Reverse Proxy (VPS)

49. Create `deployment/nginx.conf` with:
    - Upstream blocks for python-app (5001), web-server (8080), n8n (5678)
    - Server block for HTTP → HTTPS redirect
    - Server block for HTTPS with SSL certificates
    - Proxy passes for `/`, `/api/*`, `/webhook/*`, `/dashboard` routes
    - Gzip compression enabled

50. Create `deployment/certbot-setup.sh` for SSL certificate generation via Let's Encrypt:
    ```bash
    sudo certbot certonly --standalone -d your.domain.com
    sudo systemctl start nginx
    ```

## Phase 15: Final Checklist and Documentation

51. Create `README.md` in project root with:
    - Project overview and architecture diagram
    - Local setup instructions: clone, `.env` setup, `docker-compose up`
    - VPS deployment instructions: run `deployment/deploy.sh`
    - API endpoint documentation: `/api/news`, `/api/refresh`, `/webhook/n8n`
    - n8n workflow export (manual: export JSON from UI)
    - Troubleshooting common issues

52. Create `ARCHITECTURE.md` documenting:
    - Data flow: Scraper → Summarizer → Video Idea Gen → Leonardo API → Feed Merge → Web Display
    - Container network: all services on `ai-network` bridge
    - Volume mounts: persistent `n8n_data`, shared `./app/data`
    - Webhook flow: n8n → Python Flask endpoints

53. Test full pipeline end-to-end locally, then on VPS:
    - Trigger manual pipeline run: `bash app/scripts/run_pipeline.sh`
    - Verify feed.json generated: `cat app/data/feed.json`
    - Check web UI displays feed: `curl http://localhost:8080/api/news`
    - Trigger n8n workflow and observe logs

54. Document VPS credentials securely (password manager):
    - VPS SSH key location and passphrase
    - n8n admin username and password
    - Leonardo API key (in `.env`)
    - Any third-party API credentials

55. Set up automated backups for n8n data and feed history:
    - Cron job on VPS: `0 2 * * * docker exec ai-news-n8n tar -czf /home/ubuntu/backups/n8n-$(date +%Y%m%d).tar.gz /home/node/.n8n`
    - Store backups remotely (S3, rsync to secondary storage)

56. Monitor and log production health:
    - Check container health: `docker-compose ps` (shows health status)
    - Monitor disk space: `df -h` on VPS
    - Track API response times and error rates
    - Set up log aggregation (optional: ELK stack, Datadog, etc.)