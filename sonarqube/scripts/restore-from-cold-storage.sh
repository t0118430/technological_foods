#!/bin/bash
# SonarQube Cold Storage Restore Script
# Restores archived data from cold storage when needed

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <archive_file>"
    echo ""
    echo "Available archives:"
    ls -lh "${COLD_STORAGE_PATH:-/mnt/usb-backup/sonarqube-cold-storage}"/*.gz 2>/dev/null || echo "No archives found"
    exit 1
fi

ARCHIVE_FILE="$1"
DB_HOST="${PGHOST:-sonarqube-db}"
DB_USER="${PGUSER:-sonar}"
DB_NAME="${PGDATABASE:-sonarqube}"

if [ ! -f "$ARCHIVE_FILE" ]; then
    echo "❌ Error: Archive file not found: $ARCHIVE_FILE"
    exit 1
fi

echo "========================================"
echo "SonarQube Cold Storage Restore"
echo "========================================"
echo "Archive: $ARCHIVE_FILE"
echo "Database: $DB_NAME@$DB_HOST"
echo ""

read -p "⚠️  This will restore archived data. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Restoring data..."

# Determine file type and restore accordingly
if [[ "$ARCHIVE_FILE" == *"snapshots_archive"* ]]; then
    # Restore snapshots
    gunzip -c "$ARCHIVE_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\COPY snapshots FROM STDIN WITH CSV HEADER"
elif [[ "$ARCHIVE_FILE" == *"old_analyses"* ]]; then
    # Restore old analyses
    gunzip -c "$ARCHIVE_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\COPY snapshots FROM STDIN WITH CSV HEADER"
elif [[ "$ARCHIVE_FILE" == *"backup"* ]]; then
    # Full database restore
    echo "⚠️  This is a full database backup. Use restore-backup.sh instead."
    exit 1
else
    echo "❌ Unknown archive type"
    exit 1
fi

echo "✅ Data restored successfully!"
echo ""
echo "Run VACUUM ANALYZE to optimize database:"
echo "  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'VACUUM ANALYZE;'"
