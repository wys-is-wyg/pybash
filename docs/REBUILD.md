# Rebuilding and Accessing the Web Server

## Quick Rebuild Commands

### Full Rebuild (when code changes)
```bash
docker-compose stop web-server
docker-compose build --no-cache web-server
docker-compose up -d web-server
```

### Quick Restart (when only config changes)
```bash
docker-compose restart web-server
```

### View Logs
```bash
docker logs -f ai-news-web
```

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

## Fixing Browser Cache Issues

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

## Fixing SSL Errors

### Error: "ERR_SSL_PROTOCOL_ERROR" or "Invalid Response"

**Solution**: Make sure you're using the correct port:
- ✅ **HTTPS**: `https://localhost:8443` (port 8443)
- ❌ **NOT**: `https://localhost:8080` (port 8080 is HTTP only)

### Error: "Your connection is not private" (Self-signed certificate)

This is **normal** for development. To proceed:

1. Click **"Advanced"** or **"Show Details"**
2. Click **"Proceed to localhost"** or **"Accept the Risk"**
3. The browser will remember this choice

### If HTTPS Still Doesn't Work

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

## Navigation Links

The navigation now uses proper routes (not hash-based):
- `/` - Feed (all news)
- `/video-ideas` - Video ideas only
- `/output` - Raw JSON feed
- `/dashboard` - n8n dashboard
- `/rationale` - Architecture docs

## Troubleshooting

### Old navigation still showing?
1. Hard refresh (Ctrl+Shift+R)
2. Clear browser cache
3. Try incognito mode
4. Check that container was rebuilt: `docker logs ai-news-web`

### SSL not working?
1. Use port **8443** for HTTPS (not 8080)
2. Accept the self-signed certificate warning
3. Check logs: `docker logs ai-news-web`

### Routes return 404?
1. Check server.js has the route defined
2. Restart container: `docker-compose restart web-server`
3. Check logs for errors: `docker logs ai-news-web`

