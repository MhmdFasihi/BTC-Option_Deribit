#!/bin/bash
# =============================================================================
# Qortfolio Deployment Script
# Full automated deployment for Ubuntu 22.04/24.04 VPS
# Usage: sudo ./scripts/deploy.sh
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# Configuration - MODIFY THESE VALUES
# -----------------------------------------------------------------------------
DOMAIN="qortfolio.com"
EMAIL="your-email@example.com"  # For Let's Encrypt notifications
DEPLOY_DIR="/opt/qortfolio"
BACKUP_DIR="/opt/backups/qortfolio"

# -----------------------------------------------------------------------------
# Colors for output
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# -----------------------------------------------------------------------------
# Check if running as root
# -----------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

echo ""
echo "=============================================="
echo "  Qortfolio VPS Deployment Script"
echo "=============================================="
echo ""
log_info "Domain: $DOMAIN"
log_info "Deploy directory: $DEPLOY_DIR"
echo ""

# -----------------------------------------------------------------------------
# Step 1: System Preparation
# -----------------------------------------------------------------------------
log_step "Step 1/10: Updating system packages..."
apt update && apt upgrade -y

log_step "Step 2/10: Installing required packages..."
apt install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx

# Enable and start Docker
systemctl enable docker
systemctl start docker

# -----------------------------------------------------------------------------
# Step 3: Create directories
# -----------------------------------------------------------------------------
log_step "Step 3/10: Creating directories..."
mkdir -p $DEPLOY_DIR
mkdir -p $BACKUP_DIR
mkdir -p $DEPLOY_DIR/{data,logs,certbot/conf,certbot/www}
mkdir -p $DEPLOY_DIR/data/{raw,processed,cache}

# -----------------------------------------------------------------------------
# Step 4: Copy application files
# -----------------------------------------------------------------------------
log_step "Step 4/10: Setting up application..."
cd $DEPLOY_DIR

# If running from git repo, files are already here
# Otherwise, clone from GitHub
if [ ! -f "docker-compose.yml" ]; then
    log_info "Cloning repository..."
    git clone https://github.com/mhmdfasihi/qortfolio.git .
fi

# -----------------------------------------------------------------------------
# Step 5: Create dedicated user
# -----------------------------------------------------------------------------
log_step "Step 5/10: Creating application user..."
if ! id "qortfolio" &>/dev/null; then
    useradd -r -s /bin/false -d $DEPLOY_DIR qortfolio
fi
usermod -aG docker qortfolio

# -----------------------------------------------------------------------------
# Step 6: Environment file setup
# -----------------------------------------------------------------------------
log_step "Step 6/10: Setting up environment..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    if [ -f "$DEPLOY_DIR/.env.production" ]; then
        cp $DEPLOY_DIR/.env.production $DEPLOY_DIR/.env
        log_warn "Created .env from .env.production template"
        log_warn "Please edit $DEPLOY_DIR/.env with your API credentials!"
    elif [ -f "$DEPLOY_DIR/.env.example" ]; then
        cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env
        log_warn "Created .env from .env.example template"
        log_warn "Please edit $DEPLOY_DIR/.env with your API credentials!"
    else
        log_error "No .env template found!"
    fi
fi

# -----------------------------------------------------------------------------
# Step 7: Configure firewall
# -----------------------------------------------------------------------------
log_step "Step 7/10: Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
log_info "Firewall configured: SSH, HTTP, HTTPS allowed"

# -----------------------------------------------------------------------------
# Step 8: Obtain SSL certificate
# -----------------------------------------------------------------------------
log_step "Step 8/10: Setting up SSL certificate..."

# Create temporary nginx config for initial certificate
mkdir -p $DEPLOY_DIR/nginx/conf.d
cat > $DEPLOY_DIR/nginx/conf.d/certbot-init.conf << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Qortfolio - SSL Setup in Progress';
        add_header Content-Type text/plain;
    }
}
EOF

# Start nginx for ACME challenge
docker-compose up -d nginx 2>/dev/null || true
sleep 5

# Check if certificate already exists
if [ ! -d "$DEPLOY_DIR/certbot/conf/live/$DOMAIN" ]; then
    log_info "Obtaining SSL certificate from Let's Encrypt..."

    docker-compose run --rm certbot certonly \
        --webroot \
        -w /var/www/certbot \
        --email $EMAIL \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --agree-tos \
        --no-eff-email \
        --force-renewal || {
            log_warn "Certbot failed. You may need to run it manually later."
            log_warn "Make sure your domain DNS is pointing to this server."
        }
else
    log_info "SSL certificate already exists"
fi

# Remove temporary config
rm -f $DEPLOY_DIR/nginx/conf.d/certbot-init.conf

# Stop nginx before full deployment
docker-compose down 2>/dev/null || true

# -----------------------------------------------------------------------------
# Step 9: Build and start containers
# -----------------------------------------------------------------------------
log_step "Step 9/10: Building and starting containers..."
cd $DEPLOY_DIR

# Set permissions
chown -R qortfolio:docker $DEPLOY_DIR
chmod 750 $DEPLOY_DIR
chmod 640 $DEPLOY_DIR/.env 2>/dev/null || true

# Build and start
docker-compose build --no-cache
docker-compose up -d

# Wait for containers to start
log_info "Waiting for containers to start..."
sleep 20

# -----------------------------------------------------------------------------
# Step 10: Setup systemd service
# -----------------------------------------------------------------------------
log_step "Step 10/10: Setting up systemd service..."
cat > /etc/systemd/system/qortfolio.service << EOF
[Unit]
Description=Qortfolio Bitcoin Options Analytics Platform
Documentation=https://github.com/mhmdfasihi/qortfolio
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR
Environment="COMPOSE_PROJECT_NAME=qortfolio"
ExecStartPre=/usr/bin/docker-compose pull
ExecStart=/usr/bin/docker-compose up --remove-orphans
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart
Restart=always
RestartSec=10
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable qortfolio.service

# -----------------------------------------------------------------------------
# Setup cron jobs
# -----------------------------------------------------------------------------
log_info "Setting up cron jobs..."

# SSL renewal cron job
cat > /etc/cron.d/qortfolio-ssl << EOF
# Renew SSL certificates twice daily
0 0,12 * * * root cd $DEPLOY_DIR && docker-compose run --rm certbot renew --quiet && docker-compose exec -T nginx nginx -s reload
EOF

# Backup cron job
cat > /etc/cron.d/qortfolio-backup << EOF
# Daily backup at 2 AM
0 2 * * * root $DEPLOY_DIR/scripts/backup.sh >> /var/log/qortfolio-backup.log 2>&1
EOF

# -----------------------------------------------------------------------------
# Verify deployment
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
log_info "Verifying deployment..."
echo "=============================================="

# Check container status
docker-compose ps

# Health check
sleep 5
if curl -sf "http://localhost:8501/_stcore/health" > /dev/null 2>&1; then
    log_info "Health check PASSED"
else
    log_warn "Health check failed - containers may still be starting"
fi

echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
log_info "Application URL: https://$DOMAIN"
log_info "Deploy directory: $DEPLOY_DIR"
echo ""
log_info "Useful commands:"
echo "  - View logs:     docker-compose logs -f"
echo "  - Restart:       docker-compose restart"
echo "  - Stop:          docker-compose down"
echo "  - Update:        ./scripts/update.sh"
echo ""

if [ ! -d "$DEPLOY_DIR/certbot/conf/live/$DOMAIN" ]; then
    log_warn "SSL certificate not yet configured!"
    log_warn "Run: docker-compose run --rm certbot certonly --webroot -w /var/www/certbot -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos"
fi

log_warn "Don't forget to edit $DEPLOY_DIR/.env with your API credentials!"
