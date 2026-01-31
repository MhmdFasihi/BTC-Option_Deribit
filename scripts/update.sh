#!/bin/bash
# =============================================================================
# Qortfolio Update Script
# Pulls latest changes and performs rolling update
# Usage: sudo ./scripts/update.sh
# =============================================================================

set -e

DEPLOY_DIR="/opt/qortfolio"
BACKUP_DIR="/opt/backups/qortfolio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

echo ""
echo "=============================================="
echo "  Qortfolio Update Script"
echo "=============================================="
echo ""

cd $DEPLOY_DIR

# -----------------------------------------------------------------------------
# Step 1: Create pre-update backup
# -----------------------------------------------------------------------------
log_info "Creating pre-update backup..."
mkdir -p $BACKUP_DIR

tar -czf "$BACKUP_DIR/pre-update-$TIMESTAMP.tar.gz" \
    --exclude='data/cache' \
    --exclude='.git' \
    --exclude='certbot' \
    data/ logs/ .env 2>/dev/null || log_warn "Backup partially completed"

log_info "Backup saved: pre-update-$TIMESTAMP.tar.gz"

# -----------------------------------------------------------------------------
# Step 2: Pull latest changes
# -----------------------------------------------------------------------------
log_info "Pulling latest changes from Git..."
git fetch origin
git reset --hard origin/main

# Restore .env if it was overwritten
if [ -f "$BACKUP_DIR/pre-update-$TIMESTAMP.tar.gz" ]; then
    # Extract just the .env file
    tar -xzf "$BACKUP_DIR/pre-update-$TIMESTAMP.tar.gz" -C $DEPLOY_DIR .env 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# Step 3: Rebuild containers
# -----------------------------------------------------------------------------
log_info "Rebuilding Docker containers..."
docker-compose build --no-cache

# -----------------------------------------------------------------------------
# Step 4: Rolling update
# -----------------------------------------------------------------------------
log_info "Performing rolling update..."
docker-compose up -d --remove-orphans

# Wait for containers to be healthy
log_info "Waiting for containers to become healthy..."
sleep 20

# -----------------------------------------------------------------------------
# Step 5: Verify update
# -----------------------------------------------------------------------------
log_info "Verifying update..."

# Check container status
docker-compose ps

# Health check
if curl -sf "http://localhost:8501/_stcore/health" > /dev/null 2>&1; then
    log_info "Health check PASSED"

    # Clean up old Docker images
    log_info "Cleaning up old Docker images..."
    docker image prune -f

    echo ""
    echo "=============================================="
    log_info "Update completed successfully!"
    echo "=============================================="
else
    log_error "Health check FAILED"
    log_warn "Rolling back to previous version..."

    # Attempt rollback
    if [ -f "$BACKUP_DIR/pre-update-$TIMESTAMP.tar.gz" ]; then
        tar -xzf "$BACKUP_DIR/pre-update-$TIMESTAMP.tar.gz" -C $DEPLOY_DIR
        docker-compose up -d
        log_warn "Rollback attempted. Please check the logs."
    fi

    exit 1
fi

# -----------------------------------------------------------------------------
# Cleanup old backups (keep last 7 days)
# -----------------------------------------------------------------------------
log_info "Cleaning up old backups..."
find $BACKUP_DIR -name "pre-update-*.tar.gz" -mtime +7 -delete

echo ""
log_info "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart:   docker-compose restart"
echo ""
