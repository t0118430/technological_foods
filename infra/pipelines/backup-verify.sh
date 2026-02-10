#!/bin/bash
# Verify backup integrity
LATEST_BACKUP=$(ls -t /backups/daily/*.db | head -1)
sqlite3 $LATEST_BACKUP "PRAGMA integrity_check;" | grep -q "ok" && echo "✅ Backup valid" || echo "❌ Backup corrupted"
