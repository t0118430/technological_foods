#!/bin/bash
# SonarQube Database Restore Script
# Restores from a full database backup

set -e

BACKUP_DIR="${BACKUP_PATH:-/backups}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lht "$BACKUP_DIR"/sonarqube_backup_*.sql.gz | head -10
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${PGHOST:-sonarqube-db}"
DB_USER="${PGUSER:-sonar}"
DB_NAME="${PGDATABASE:-sonarqube}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "========================================"
echo "SonarQube Database Restore"
echo "========================================"
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME@$DB_HOST"
echo ""

read -p "⚠️  WARNING: This will REPLACE all current data. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Step 1: Terminating active connections..."
psql -h "$DB_HOST" -U "$DB_USER" -d postgres <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
EOF

echo "Step 2: Dropping existing database..."
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "Step 3: Creating fresh database..."
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "Step 4: Restoring from backup..."
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored successfully!"
    echo ""
    echo "Please restart SonarQube:"
    echo "  docker-compose restart sonarqube"
else
    echo "❌ Restore failed!"
    exit 1
fi

echo ""
echo "========================================"
echo "Restore completed at $(date)"
echo "========================================"
