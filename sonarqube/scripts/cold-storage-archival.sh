#!/bin/bash
# SonarQube Cold Storage Archival Script
# Moves data older than 180 days to cold storage
# Keeps only 250 most recent analyses in active storage

set -e

COLD_STORAGE_DAYS="${COLD_STORAGE_DAYS:-180}"
MAX_ACTIVE_ANALYSES="${MAX_ACTIVE_ANALYSES:-250}"
COLD_STORAGE_DIR="${COLD_STORAGE_PATH:-/mnt/usb-backup/sonarqube-cold-storage}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database credentials
DB_HOST="${PGHOST:-sonarqube-db}"
DB_USER="${PGUSER:-sonar}"
DB_NAME="${PGDATABASE:-sonarqube}"

echo "========================================"
echo "SonarQube Cold Storage Archival"
echo "========================================"
echo "Started at: $(date)"
echo "Cold storage threshold: $COLD_STORAGE_DAYS days"
echo "Max active analyses: $MAX_ACTIVE_ANALYSES"
echo "Cold storage location: $COLD_STORAGE_DIR"
echo ""

# Create cold storage directory
mkdir -p "$COLD_STORAGE_DIR"

# Archive snapshot data older than 180 days
echo "Step 1: Archiving old snapshots..."
ARCHIVE_FILE="$COLD_STORAGE_DIR/snapshots_archive_$TIMESTAMP.sql.gz"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<EOF | gzip > "$ARCHIVE_FILE"
-- Export snapshots older than $COLD_STORAGE_DAYS days
COPY (
    SELECT * FROM snapshots
    WHERE created_at < NOW() - INTERVAL '$COLD_STORAGE_DAYS days'
) TO STDOUT WITH CSV HEADER;
EOF

if [ -s "$ARCHIVE_FILE" ]; then
    SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)
    echo "✅ Archived old snapshots: $SIZE"
else
    echo "ℹ️  No old snapshots to archive"
    rm -f "$ARCHIVE_FILE"
fi

# Keep only 250 most recent analyses per project
echo ""
echo "Step 2: Limiting active analyses to $MAX_ACTIVE_ANALYSES per project..."

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Archive and delete old analyses beyond the limit
WITH ranked_snapshots AS (
    SELECT
        uuid,
        component_uuid,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY component_uuid ORDER BY created_at DESC) as rn
    FROM snapshots
)
-- Export to cold storage before deletion
COPY (
    SELECT s.*
    FROM snapshots s
    INNER JOIN ranked_snapshots rs ON s.uuid = rs.uuid
    WHERE rs.rn > $MAX_ACTIVE_ANALYSES
) TO '/tmp/old_analyses_$TIMESTAMP.csv' WITH CSV HEADER;

-- Delete old analyses
DELETE FROM snapshots
WHERE uuid IN (
    SELECT uuid
    FROM ranked_snapshots
    WHERE rn > $MAX_ACTIVE_ANALYSES
);
EOF

# Compress and move exported data
if [ -f "/tmp/old_analyses_$TIMESTAMP.csv" ]; then
    gzip "/tmp/old_analyses_$TIMESTAMP.csv"
    mv "/tmp/old_analyses_$TIMESTAMP.csv.gz" "$COLD_STORAGE_DIR/"
    echo "✅ Archived excess analyses"
fi

# Vacuum database to reclaim space
echo ""
echo "Step 3: Optimizing database (VACUUM)..."
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "VACUUM ANALYZE;"
echo "✅ Database optimized"

# Generate archival report
REPORT_FILE="$COLD_STORAGE_DIR/archival_report_$TIMESTAMP.txt"
cat > "$REPORT_FILE" <<EOF
SonarQube Cold Storage Archival Report
========================================
Date: $(date)
Threshold: $COLD_STORAGE_DAYS days
Max Active Analyses: $MAX_ACTIVE_ANALYSES

Archived Files:
$(ls -lh "$COLD_STORAGE_DIR"/*_$TIMESTAMP.* 2>/dev/null || echo "None")

Database Statistics:
$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT
        'Total Snapshots' as metric,
        COUNT(*) as count
    FROM snapshots
    UNION ALL
    SELECT
        'Oldest Snapshot',
        EXTRACT(DAY FROM (NOW() - MIN(created_at)))::TEXT || ' days ago'
    FROM snapshots;
" -t)

Disk Usage:
$(df -h "$COLD_STORAGE_DIR" | tail -1)

Cold Storage Contents:
$(du -sh "$COLD_STORAGE_DIR"/* | tail -10)
EOF

echo ""
echo "✅ Archival report generated: $REPORT_FILE"
cat "$REPORT_FILE"

echo ""
echo "========================================"
echo "Cold storage archival completed at $(date)"
echo "========================================"
