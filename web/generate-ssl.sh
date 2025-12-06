#!/bin/bash
# Generate self-signed SSL certificates for development

set -e

SSL_DIR="./ssl"
mkdir -p "$SSL_DIR"

echo "Generating self-signed SSL certificate for development..."
echo "⚠️  This is for development only. Use Let's Encrypt for production."

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout "$SSL_DIR/key.pem" \
  -out "$SSL_DIR/cert.pem" \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=AI News Tracker/CN=localhost" \
  2>/dev/null || {
  echo "Error: openssl not found. Install openssl to generate certificates."
  echo "On Ubuntu/Debian: sudo apt-get install openssl"
  exit 1
}

echo "✅ SSL certificates generated:"
echo "   Certificate: $SSL_DIR/cert.pem"
echo "   Private Key: $SSL_DIR/key.pem"
echo ""
echo "To use in Docker, set environment variables:"
echo "  SSL_CERT_PATH=/app/ssl/cert.pem"
echo "  SSL_KEY_PATH=/app/ssl/key.pem"
echo ""
echo "Or mount the ssl directory as a volume in docker-compose.yml"

