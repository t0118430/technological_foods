#!/bin/bash
# AgriTech Raspberry Pi Setup - Quick install script
set -e
REAL_USER=${SUDO_USER:-pi}
apt-get update && apt-get upgrade -y
apt-get install -y git python3 python3-pip curl docker.io docker-compose
usermod -aG docker $REAL_USER
pip3 install influxdb-client python-dotenv
mkdir -p /data/{influxdb,grafana,nodered,sqlite}
chown -R $REAL_USER:$REAL_USER /data
echo "✅ Setup complete. Reboot required."
