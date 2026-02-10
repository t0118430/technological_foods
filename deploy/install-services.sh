#!/bin/bash
# Install systemd services
set -e
cp systemd/*.service systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable agritech-docker agritech-api agritech-backup.timer agritech-monitor
echo "✅ Services installed. Start with: systemctl start agritech-docker agritech-api"
