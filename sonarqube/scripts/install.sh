#!/bin/bash
# SonarQube Installation Script for Raspberry Pi
# Installs and configures SonarQube with data retention policies

set -e

INSTALL_DIR="/opt/sonarqube"
BACKUP_MOUNT="/mnt/usb-backup"

echo "========================================"
echo "SonarQube Installation for Raspberry Pi"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (sudo)"
    exit 1
fi

# Check prerequisites
echo "Step 1: Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is not installed"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is not installed"; exit 1; }
echo "✅ Prerequisites met"

# Configure system for SonarQube (Elasticsearch requirements)
echo ""
echo "Step 2: Configuring system parameters..."
sysctl -w vm.max_map_count=524288
sysctl -w fs.file-max=131072
ulimit -n 131072
ulimit -u 8192

# Make changes permanent
if ! grep -q "vm.max_map_count=524288" /etc/sysctl.conf; then
    echo "vm.max_map_count=524288" >> /etc/sysctl.conf
    echo "fs.file-max=131072" >> /etc/sysctl.conf
fi

if ! grep -q "sonarqube" /etc/security/limits.conf; then
    cat >> /etc/security/limits.conf <<EOF
sonarqube   -   nofile   131072
sonarqube   -   nproc    8192
EOF
fi
echo "✅ System parameters configured"

# Create installation directory
echo ""
echo "Step 3: Creating installation directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Copy files from repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Copying files from: $SCRIPT_DIR"

cp "$SCRIPT_DIR/docker-compose.yml" .
cp "$SCRIPT_DIR/.env.example" .env
mkdir -p scripts backups
cp "$SCRIPT_DIR"/scripts/*.sh scripts/
chmod +x scripts/*.sh

# Create cold storage directory
echo ""
echo "Step 4: Setting up backup storage..."
mkdir -p "$BACKUP_MOUNT/sonarqube-backups"
mkdir -p "$BACKUP_MOUNT/sonarqube-cold-storage"

# Update .env file
echo ""
echo "Step 5: Configuring environment..."
read -sp "Enter PostgreSQL password: " DB_PASSWORD
echo ""
sed -i "s/sonar_password_change_me/$DB_PASSWORD/" .env

# Install systemd services
echo ""
echo "Step 6: Installing systemd services..."
cp "$SCRIPT_DIR"/systemd/*.service /etc/systemd/system/
cp "$SCRIPT_DIR"/systemd/*.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable sonarqube.service
systemctl enable sonarqube-backup.timer
systemctl enable sonarqube-cold-storage.timer
systemctl enable sonarqube-health-check.timer

echo "✅ Systemd services installed"

# Start SonarQube
echo ""
echo "Step 7: Starting SonarQube..."
systemctl start sonarqube.service

echo ""
echo "Waiting for SonarQube to start (this may take 2-3 minutes)..."
for i in {1..60}; do
    if curl -sf http://localhost:9000/api/system/status >/dev/null 2>&1; then
        echo "✅ SonarQube is running!"
        break
    fi
    echo -n "."
    sleep 5
done
echo ""

# Start timers
systemctl start sonarqube-backup.timer
systemctl start sonarqube-cold-storage.timer
systemctl start sonarqube-health-check.timer

# Display status
echo ""
echo "========================================"
echo "✅ Installation Complete!"
echo "========================================"
echo ""
echo "SonarQube Status:"
systemctl status sonarqube.service --no-pager -l
echo ""
echo "Access SonarQube at:"
echo "  http://$(hostname -I | awk '{print $1}'):9000"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin"
echo "  ⚠️  CHANGE THE PASSWORD ON FIRST LOGIN!"
echo ""
echo "Automated tasks:"
echo "  ✅ Daily backups (2:00 AM)"
echo "  ✅ Weekly cold storage archival (Sunday 3:00 AM)"
echo "  ✅ Health checks every 15 minutes"
echo ""
echo "Useful commands:"
echo "  systemctl status sonarqube.service"
echo "  systemctl restart sonarqube.service"
echo "  docker-compose logs -f sonarqube"
echo "  journalctl -u sonarqube.service -f"
echo ""
echo "Manual operations:"
echo "  Backup:  docker-compose run --rm sonarqube-backup /scripts/backup-db.sh"
echo "  Archive: docker-compose run --rm sonarqube-backup /scripts/cold-storage-archival.sh"
echo ""
