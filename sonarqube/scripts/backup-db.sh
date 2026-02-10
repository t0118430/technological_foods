#!/bin/bash
# SonarQube PostgreSQL Database Backup Script
# Runs daily to backup SonarQube database

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_PATH:-/backups}"
COLD_STORAGE_DIR="${COLD_STORAGE_PATH:-/mnt/usb-backup/sonarqube-cold-storage}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Create backup directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$COLD_STORAGE_DIR"

# Database credentials (from environment)
DB_HOST="${PGHOST:-sonarqube-db}"
DB_USER="${PGUSER:-sonar}"
DB_NAME="${PGDATABASE:-sonarqube}"

BACKUP_FILE="$BACKUP_DIR/sonarqube_backup_$TIMESTAMP.sql.gz"

echo "========================================"
echo "SonarQube Database Backup"
echo "========================================"
echo "Timestamp: $TIMESTAMP"
echo "Database: $DB_NAME@$DB_HOST"
echo "Backup file: $BACKUP_FILE"
echo ""

# Perform backup
echo "Starting database dump..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --verbose | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo "   Size: $SIZE"
    echo "   Location: $BACKUP_FILE"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Cleanup old backups (keep last 30 days)
echo ""
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "sonarqube_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
echo "✅ Cleanup completed"

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/sonarqube_backup_*.sql.gz 2>/dev/null | tail -5 || echo "No backups found"

echo ""
echo "========================================"
echo "Backup completed at $(date)"
echo "========================================"
