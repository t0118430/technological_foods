#!/bin/bash
# AgriTech Backup Script
set -e
BACKUP_TYPE=${1:-daily}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$BACKUP_TYPE"
mkdir -p $BACKUP_DIR

# Backup SQLite database
cp backend/data/agritech.db $BACKUP_DIR/agritech_${TIMESTAMP}.db

# Backup InfluxDB
docker exec agritech-influxdb influx backup /tmp/influx_backup
docker cp agritech-influxdb:/tmp/influx_backup $BACKUP_DIR/influx_${TIMESTAMP}

# Backup configs
tar czf $BACKUP_DIR/configs_${TIMESTAMP}.tar.gz backend/config backend/api/rules_config.json

# Cleanup old backups (keep 7 daily, 4 weekly, 12 monthly)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete 2>/dev/null || true

echo "✅ Backup complete: $BACKUP_DIR"
