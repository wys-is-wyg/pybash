# SSL/HTTPS Setup Guide

This guide explains how to set up HTTPS for the AI News Tracker web server.

## Development (Self-Signed Certificates)

For local development, use self-signed certificates:

### 1. Generate SSL Certificates

```bash
cd web
bash generate-ssl.sh
```

This creates:
- `web/ssl/cert.pem` - SSL certificate
- `web/ssl/key.pem` - Private key

### 2. Restart Docker Container

```bash
docker-compose restart web-server
```

### 3. Access HTTPS

- **HTTP**: http://localhost:8080
- **HTTPS**: https://localhost:8443

**Note**: Browsers will show a security warning for self-signed certificates. Click "Advanced" → "Proceed to localhost" to continue.

## Production (Let's Encrypt)

For production, use Let's Encrypt certificates:

### 1. Install Certbot

```bash
sudo apt-get update
sudo apt-get install certbot
```

### 2. Generate Certificates

```bash
sudo certbot certonly --standalone -d yourdomain.com
```

Certificates will be saved to:
- `/etc/letsencrypt/live/yourdomain.com/fullchain.pem`
- `/etc/letsencrypt/live/yourdomain.com/privkey.pem`

### 3. Update docker-compose.yml

```yaml
web-server:
  volumes:
    - /etc/letsencrypt/live/yourdomain.com:/app/ssl:ro
  environment:
    - SSL_CERT_PATH=/app/ssl/fullchain.pem
    - SSL_KEY_PATH=/app/ssl/privkey.pem
```

### 4. Auto-Renewal

Set up a cron job to renew certificates:

```bash
sudo crontab -e
```

Add:
```
0 0 * * * certbot renew --quiet && docker-compose restart web-server
```

## Environment Variables

- `HTTPS_PORT` - HTTPS port (default: 8443)
- `SSL_CERT_PATH` - Path to SSL certificate file
- `SSL_KEY_PATH` - Path to SSL private key file

## Troubleshooting

### Certificates Not Found

If you see "HTTPS not enabled" in logs:
1. Check that certificate files exist at the specified paths
2. Verify file permissions (should be readable)
3. Check volume mounts in docker-compose.yml

### Certificate Errors

- **Self-signed**: Expected in development, click through browser warning
- **Expired**: Renew certificates (Let's Encrypt certificates expire every 90 days)
- **Wrong domain**: Ensure certificate matches your domain name

## Security Notes

- **Never commit** private keys to git
- Add `web/ssl/` to `.gitignore`
- Use Let's Encrypt for production
- Self-signed certificates are for development only

