#!/bin/bash
# =============================================================================
# Qortfolio Backup Script
# Creates compressed backups of data, configuration, and SSL certificates
# Usage: sudo ./scripts/backup.sh
# =============================================================================

set -e

DEPLOY_DIR="/opt/qortfolio"
BACKUP_DIR="/opt/backups/qortfolio"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1"; }
log_warn() { echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] $1"; }

# Create backup directory
mkdir -p $BACKUP_DIR

cd $DEPLOY_DIR

log_info "Starting backup..."

# -----------------------------------------------------------------------------
# Backup application data
# -----------------------------------------------------------------------------
log_info "Backing up application data..."
tar -czf "$BACKUP_DIR/data-$TIMESTAMP.tar.gz" \
    -C $DEPLOY_DIR \
    --exclude='data/cache/*' \
    data/ 2>/dev/null || log_warn "Data backup: some files may be missing"

# -----------------------------------------------------------------------------
# Backup configuration
# -----------------------------------------------------------------------------
log_info "Backing up configuration..."
tar -czf "$BACKUP_DIR/config-$TIMESTAMP.tar.gz" \
    -C $DEPLOY_DIR \
    .env \
    .streamlit/ \
    nginx/ \
    docker-compose.yml 2>/dev/null || log_warn "Config backup: some files may be missing"

# -----------------------------------------------------------------------------
# Backup SSL certificates
# -----------------------------------------------------------------------------
if [ -d "$DEPLOY_DIR/certbot/conf" ]; then
    log_info "Backing up SSL certificates..."
    tar -czf "$BACKUP_DIR/ssl-$TIMESTAMP.tar.gz" \
        -C $DEPLOY_DIR \
        certbot/conf/ 2>/dev/null || log_warn "SSL backup: some files may be missing"
fi

# -----------------------------------------------------------------------------
# Backup Redis data (if running)
# -----------------------------------------------------------------------------
if docker-compose ps redis 2>/dev/null | grep -q "Up"; then
    log_info "Backing up Redis data..."
    docker-compose exec -T redis redis-cli BGSAVE 2>/dev/null || true
    sleep 3
    docker cp qortfolio-redis:/data/dump.rdb "$BACKUP_DIR/redis-$TIMESTAMP.rdb" 2>/dev/null || log_warn "Redis backup failed"
fi

# -----------------------------------------------------------------------------
# Create combined backup archive
# -----------------------------------------------------------------------------
log_info "Creating combined backup archive..."
cd $BACKUP_DIR

# Combine all backups into one archive
tar -czf "full-backup-$TIMESTAMP.tar.gz" \
    data-$TIMESTAMP.tar.gz \
    config-$TIMESTAMP.tar.gz \
    ssl-$TIMESTAMP.tar.gz 2>/dev/null || \
tar -czf "full-backup-$TIMESTAMP.tar.gz" \
    data-$TIMESTAMP.tar.gz \
    config-$TIMESTAMP.tar.gz 2>/dev/null

# Add Redis backup if it exists
if [ -f "redis-$TIMESTAMP.rdb" ]; then
    tar -rf "full-backup-$TIMESTAMP.tar.gz" "redis-$TIMESTAMP.rdb" 2>/dev/null || true
fi

# Remove individual archives
rm -f "data-$TIMESTAMP.tar.gz" \
      "config-$TIMESTAMP.tar.gz" \
      "ssl-$TIMESTAMP.tar.gz" \
      "redis-$TIMESTAMP.rdb" 2>/dev/null

# -----------------------------------------------------------------------------
# Cleanup old backups
# -----------------------------------------------------------------------------
log_info "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "full-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "pre-update-*.tar.gz" -mtime +7 -delete

# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------
BACKUP_SIZE=$(du -h "$BACKUP_DIR/full-backup-$TIMESTAMP.tar.gz" | cut -f1)
log_info "Backup complete: full-backup-$TIMESTAMP.tar.gz ($BACKUP_SIZE)"

# List recent backups
echo ""
log_info "Recent backups:"
ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null | tail -5
