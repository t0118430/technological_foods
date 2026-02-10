#!/bin/bash
# Quick Start: Set Up Dev & Prod Environments on Your Raspberry Pi

# 🎯 Goal: Get your Pi configured with both development and production environments

echo "=================================================="
echo "🥧 Raspberry Pi Two-Environment Setup"
echo "=================================================="

## Part 1: Connect to Your Pi (First Time Only)

### You have a Pi with Ubuntu Server, powered on, but no network configured yet.

# Option A: Using Monitor + Keyboard (Easiest for first time)
# 1. Connect HDMI monitor and USB keyboard to Pi
# 2. Login with default credentials:
#    Username: ubuntu
#    Password: ubuntu
# 3. Change password when prompted
# 4. Continue to Part 2 below

# Option B: Using Ethernet Cable
# 1. Connect Pi to router via ethernet cable
# 2. Find Pi's IP from router admin panel (usually http://192.168.1.1)
# 3. SSH to Pi: ssh ubuntu@192.168.1.XXX
# 4. Login: ubuntu / ubuntu
# 5. Change password when prompted

## Part 2: Configure WiFi (If using WiFi)

cat <<'NETPLAN_EOF'
# Edit netplan configuration
sudo nano /etc/netplan/50-cloud-init.yaml

# Add this (replace YOUR_WIFI_SSID and YOUR_WIFI_PASSWORD):

network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: true
      optional: true
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      access-points:
        "YOUR_WIFI_SSID":
          password: "YOUR_WIFI_PASSWORD"

# Save file (Ctrl+O, Enter, Ctrl+X)

# Apply configuration
sudo netplan apply

# Wait 10 seconds, then check WiFi IP
hostname -I
# Note your WiFi IP (e.g., 192.168.1.151)

# Test internet
ping -c 4 8.8.8.8
NETPLAN_EOF

## Part 3: Install Required Software

cat <<'INSTALL_EOF'
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Install other tools
sudo apt install -y git python3 python3-pip curl wget vim htop

# Reboot to apply all changes
sudo reboot
INSTALL_EOF

## Part 4: Clone Project & Set Up Environments

cat <<'SETUP_EOF'
# SSH back to Pi after reboot
ssh ubuntu@192.168.1.151  # Use your Pi's actual IP

# Create project directory
sudo mkdir -p /opt/agritech
sudo chown ubuntu:ubuntu /opt/agritech
cd /opt/agritech

# Clone repository
git clone https://github.com/t0118430/technological_foods.git
cd technological_foods

# Run environment setup script
chmod +x deploy/setup-environments.sh
./deploy/setup-environments.sh

# This creates:
# - envs/dev/.env (development config)
# - envs/prod/.env (production config)
# - envs/dev/docker-compose.yml
# - envs/prod/docker-compose.yml
# - Secure API keys and tokens
SETUP_EOF

## Part 5: Start Both Environments

cat <<'START_EOF'
# Start Development Environment
cd /opt/agritech/technological_foods/envs/dev
docker-compose up -d

# Wait a moment for services to start
sleep 10

# Check dev services
docker ps | grep dev

# Start Production Environment
cd /opt/agritech/technological_foods/envs/prod
docker-compose up -d

# Wait a moment
sleep 10

# Check prod services
docker ps | grep prod

# You should see 4 containers running:
# - agritech-influxdb-dev
# - agritech-grafana-dev
# - agritech-influxdb-prod
# - agritech-grafana-prod
START_EOF

## Part 6: Access Your Environments

cat <<'ACCESS_EOF'
# Get your Pi's IP
PI_IP=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "🌐 Your Environment URLs"
echo "=========================================="
echo ""
echo "🧪 DEVELOPMENT:"
echo "   Grafana:  http://$PI_IP:3000"
echo "   InfluxDB: http://$PI_IP:8086"
echo "   API:      http://$PI_IP:3001"
echo ""
echo "   Credentials:"
echo "   - Username: admin"
echo "   - Password: devadmin123"
echo ""
echo "🚀 PRODUCTION:"
echo "   Grafana:  http://$PI_IP:3001"
echo "   InfluxDB: http://$PI_IP:8087"
echo "   API:      http://$PI_IP:3002"
echo ""
echo "   Credentials: (check envs/ENVIRONMENT_INFO.md)"
echo ""

# View complete environment info
cat /opt/agritech/technological_foods/envs/ENVIRONMENT_INFO.md
ACCESS_EOF

## Part 7: Configure Arduino to Send to Both Environments

cat <<'ARDUINO_EOF'
# Your Arduino can send data to either environment:

# Development - For testing new sensor code
API_ENDPOINT_DEV="http://192.168.1.151:3001/api/data"
API_KEY_DEV="[from envs/ENVIRONMENT_INFO.md]"

# Production - For live production data
API_ENDPOINT_PROD="http://192.168.1.151:3002/api/data"
API_KEY_PROD="[from envs/ENVIRONMENT_INFO.md]"

# In your Arduino sketch, you can:
# 1. Use dev endpoint while testing
# 2. Switch to prod endpoint when ready for live data
# 3. Or send to BOTH for comparison!
ARDUINO_EOF

## Part 8: Set Up GitHub Actions Deployment

cat <<'GITHUB_EOF'
# Add these secrets to your GitHub repository:
# (Settings → Secrets and variables → Actions)

# Pi Access
PI_SSH_KEY=[Your SSH private key content]
PI_HOST=192.168.1.151  # Your Pi's IP
PI_USER=ubuntu
PI_PROJECT_PATH=/opt/agritech/technological_foods

# Arduino Access
ARDUINO_IP=192.168.1.100  # Your Arduino's IP
ARDUINO_OTA_PASSWORD=[Optional]

# Environment-Specific API Keys (from envs/ENVIRONMENT_INFO.md)
API_KEY_DEV=[Your dev API key]
API_KEY_PROD=[Your prod API key]

# Notifications
NTFY_TOPIC_URL=https://ntfy.sh/techfoods
GITHUB_EOF

## Part 9: Test Deployments

cat <<'DEPLOY_EOF'
# Test manual deployment to dev environment
cd /opt/agritech/technological_foods
./deploy/deploy-env.sh dev

# Test manual deployment to prod environment
./deploy/deploy-env.sh prod

# View logs
cd envs/dev && docker-compose logs -f  # Dev logs
cd envs/prod && docker-compose logs -f  # Prod logs

# Check health
curl http://localhost:3001/health  # Dev API
curl http://localhost:3002/health  # Prod API
DEPLOY_EOF

## Part 10: Workflow Summary

cat <<'WORKFLOW_EOF'
========================================
📋 Development Workflow
========================================

1. Make code changes
2. Push to feature branch
3. GitHub Actions runs tests
4. If tests pass, deploy to DEV environment
5. Test manually on dev: http://pi-ip:3001
6. If works, merge to master
7. Auto-deploy to PROD environment
8. Monitor prod: http://pi-ip:3002

========================================
🔄 Environment Comparison
========================================

Feature          | Dev (3001)      | Prod (3002)
-----------------|-----------------|------------------
Data Retention   | 30 days         | 365 days
Debug Logs       | Enabled         | Disabled
Auto-Restart     | On code save    | Manual only
Sensor Data      | Test Arduino    | Live Arduino
Uptime SLA       | No guarantee    | High availability
Backups          | Daily           | Hourly + offsite

========================================
🎯 When to Use Each Environment
========================================

DEV:
✓ Testing new features
✓ Experimenting with configs
✓ Debugging issues
✓ Learning the system
✓ Safe to break things!

PROD:
✓ Live production data
✓ Business decisions
✓ Customer-facing dashboards
✓ Critical monitoring
✓ Must be stable!
WORKFLOW_EOF

echo ""
echo "=========================================="
echo "✅ You're All Set!"
echo "=========================================="
echo ""
echo "🎉 You now have:"
echo "   ✓ Pi connected to network"
echo "   ✓ Dev environment on ports 3001, 8086, 3000"
echo "   ✓ Prod environment on ports 3002, 8087, 3001"
echo "   ✓ Both environments isolated"
echo "   ✓ Ready for deployments"
echo ""
echo "📚 Next:"
echo "   1. Access Grafana and set up dashboards"
echo "   2. Configure Arduino to send to dev first"
echo "   3. Test everything works"
echo "   4. Switch Arduino to prod when ready"
echo "   5. Set up automated deployments"
echo ""
echo "🔗 Useful Commands:"
echo "   View this guide: cat deploy/QUICKSTART_TWO_ENVS.md"
echo "   Full setup guide: cat deploy/INITIAL_PI_SETUP.md"
echo "   Environment info: cat envs/ENVIRONMENT_INFO.md"
echo "   Deploy to dev:    ./deploy/deploy-env.sh dev"
echo "   Deploy to prod:   ./deploy/deploy-env.sh prod"
echo ""
