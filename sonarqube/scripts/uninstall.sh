#!/bin/bash
# SonarQube Uninstallation Script

set -e

INSTALL_DIR="/opt/sonarqube"

echo "========================================"
echo "SonarQube Uninstallation"
echo "========================================"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (sudo)"
    exit 1
fi

read -p "⚠️  This will remove SonarQube. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Uninstallation cancelled"
    exit 0
fi

read -p "Delete all data including backups? (yes/no): " DELETE_DATA

# Stop and disable services
echo ""
echo "Stopping services..."
systemctl stop sonarqube.service || true
systemctl stop sonarqube-backup.timer || true
systemctl stop sonarqube-cold-storage.timer || true
systemctl stop sonarqube-health-check.timer || true

systemctl disable sonarqube.service || true
systemctl disable sonarqube-backup.timer || true
systemctl disable sonarqube-cold-storage.timer || true
systemctl disable sonarqube-health-check.timer || true

# Remove systemd files
echo "Removing systemd files..."
rm -f /etc/systemd/system/sonarqube*.service
rm -f /etc/systemd/system/sonarqube*.timer
systemctl daemon-reload

# Stop Docker containers
echo "Stopping Docker containers..."
cd "$INSTALL_DIR" && docker-compose down -v || true

# Remove installation directory
if [ "$DELETE_DATA" = "yes" ]; then
    echo "Removing all data..."
    rm -rf "$INSTALL_DIR"
    echo "✅ All data removed"
else
    echo "ℹ️  Data preserved in $INSTALL_DIR"
    echo "   Backups preserved in /mnt/usb-backup/sonarqube-*"
fi

echo ""
echo "✅ SonarQube uninstalled"
