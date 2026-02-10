#!/bin/bash
# Mount USB SSD for backups
set -e
USB_DEVICE=${1:-/dev/sda1}
mkdir -p /backups
mount $USB_DEVICE /backups
echo "$USB_DEVICE /backups ext4 defaults,nofail 0 2" >> /etc/fstab
mkdir -p /backups/{daily,weekly,monthly}
chown -R ${SUDO_USER:-pi}:${SUDO_USER:-pi} /backups
echo "✅ USB backup drive mounted at /backups"
