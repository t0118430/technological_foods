#!/bin/bash
# Remote Raspberry Pi configuration script
# Run from your dev machine — connects via SSH and configures WiFi + API port
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

# Load credentials
if [ -f "$INFRA_DIR/.env" ]; then
    export $(grep -v '^#' "$INFRA_DIR/.env" | xargs)
else
    echo "ERROR: infra/.env not found. Copy infra/.env.example to infra/.env and fill in values."
    exit 1
fi

PI_HOST="${PI_HOST:-192.168.1.135}"
PI_USER="${PI_USER:-techfoods}"
WIFI_SSID="${WIFI_SSID}"
WIFI_PASSWORD="${WIFI_PASSWORD}"

SSH_CMD="ssh -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST}"

echo "=========================================="
echo "  Raspberry Pi Configuration"
echo "  Host: ${PI_USER}@${PI_HOST}"
echo "=========================================="

# Test connection
echo ""
echo "[1/5] Testing SSH connection..."
$SSH_CMD "echo 'Connected to $(hostname)'" || { echo "ERROR: Cannot SSH to Pi"; exit 1; }

# Configure WiFi
if [ -n "$WIFI_SSID" ] && [ -n "$WIFI_PASSWORD" ]; then
    echo ""
    echo "[2/5] Configuring WiFi (SSID: ${WIFI_SSID})..."

    $SSH_CMD "sudo tee /etc/netplan/99-wifi.yaml > /dev/null" <<EOF
network:
  version: 2
  renderer: networkd
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      access-points:
        "${WIFI_SSID}":
          password: "${WIFI_PASSWORD}"
EOF

    $SSH_CMD "sudo netplan generate && sudo netplan apply"
    echo "  WiFi configured. Waiting for connection..."
    sleep 5
    $SSH_CMD "ip a show wlan0 2>/dev/null | grep 'inet ' || echo '  WiFi not yet connected (may take a moment)'"
else
    echo ""
    echo "[2/5] Skipping WiFi (WIFI_SSID not set in .env)"
fi

# Open firewall for API
echo ""
echo "[3/5] Configuring firewall (port 3001 for API)..."
$SSH_CMD "sudo ufw allow 22/tcp && sudo ufw allow 3001/tcp && sudo ufw allow 3000/tcp && sudo ufw allow 8086/tcp && sudo ufw --force enable && sudo ufw status" 2>/dev/null || echo "  ufw not installed — skipping firewall config"

# Install essentials
echo ""
echo "[4/5] Installing essential packages..."
$SSH_CMD "sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv git curl docker.io docker-compose"
$SSH_CMD "sudo usermod -aG docker ${PI_USER}" 2>/dev/null || true

# System info
echo ""
echo "[5/5] System info:"
$SSH_CMD "echo '  Hostname: '$(hostname) && echo '  IP (eth0): '$(ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo 'N/A') && echo '  IP (wlan0): '$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo 'N/A') && echo '  Disk: '$(df -h / | tail -1 | awk '{print $3\"/\"$2\" used\"}') && echo '  RAM: '$(free -h | grep Mem | awk '{print $3\"/\"$2\" used\"}')"

echo ""
echo "=========================================="
echo "  Pi configured successfully!"
echo "  API port 3001 is open"
echo "=========================================="
