#!/bin/bash
# =============================================================================
# SSL Certificate Initialization Script
# Obtains Let's Encrypt SSL certificate for qortfolio.com
# Usage: sudo ./scripts/init-ssl.sh
# =============================================================================

set -e

# Configuration - MODIFY THESE
DOMAIN="qortfolio.com"
EMAIL="your-email@example.com"
DEPLOY_DIR="/opt/qortfolio"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

cd $DEPLOY_DIR

# Create required directories
mkdir -p certbot/conf certbot/www

log_info "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Create temporary nginx config for ACME challenge
log_info "Creating temporary nginx config..."
cat > nginx/conf.d/certbot-temp.conf << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Qortfolio - SSL Setup';
        add_header Content-Type text/plain;
    }
}
EOF

# Temporarily modify docker-compose to not require SSL
log_info "Starting nginx for ACME challenge..."

# Start only nginx with a minimal config
docker run -d --name nginx-certbot \
    -p 80:80 \
    -v $DEPLOY_DIR/nginx/conf.d/certbot-temp.conf:/etc/nginx/conf.d/default.conf:ro \
    -v $DEPLOY_DIR/certbot/www:/var/www/certbot:ro \
    nginx:alpine

sleep 5

# Verify nginx is running
if ! docker ps | grep -q nginx-certbot; then
    log_error "Nginx container failed to start"
    exit 1
fi

log_info "Obtaining SSL certificate..."

# Run certbot
docker run --rm \
    -v $DEPLOY_DIR/certbot/conf:/etc/letsencrypt \
    -v $DEPLOY_DIR/certbot/www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    -w /var/www/certbot \
    --email $EMAIL \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --agree-tos \
    --no-eff-email

# Stop temporary nginx
log_info "Stopping temporary nginx..."
docker stop nginx-certbot
docker rm nginx-certbot

# Remove temporary config
rm -f nginx/conf.d/certbot-temp.conf

# Check if certificate was obtained
if [ -d "certbot/conf/live/$DOMAIN" ]; then
    log_info "SSL certificate obtained successfully!"

    # Start full application stack
    log_info "Starting application with SSL..."
    docker-compose up -d

    echo ""
    echo "=============================================="
    log_info "SSL setup complete!"
    log_info "Your site is now available at: https://$DOMAIN"
    echo "=============================================="
else
    log_error "Failed to obtain SSL certificate"
    log_warn "Make sure your domain DNS is pointing to this server"
    log_warn "You can check DNS with: dig $DOMAIN"
    exit 1
fi
