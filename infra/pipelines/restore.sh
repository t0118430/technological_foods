#!/bin/bash
# AgriTech Restore Script
set -e
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <backup_file.db>"
  exit 1
fi
systemctl stop agritech-api
cp $BACKUP_FILE backend/data/agritech.db
systemctl start agritech-api
echo "✅ Restore complete"
