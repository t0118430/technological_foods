# 🥧 Raspberry Pi Initial Setup Guide

## 🔌 Connecting to Your Pi for the First Time

Your Pi has Ubuntu Server but no network configured yet. Here are your options:

---

## Option 1: Direct Connection (Easiest)

### What You Need:
- 🖥️ Monitor + HDMI cable
- ⌨️ USB Keyboard
- 🔌 Power supply (already connected)

### Steps:

1. **Connect peripherals:**
   ```
   Pi → HDMI → Monitor
   Pi → USB → Keyboard
   Pi → Power (already done)
   ```

2. **Boot up and login:**
   ```
   Ubuntu Server login screen appears

   Default credentials:
   Username: ubuntu
   Password: ubuntu

   (You'll be forced to change password on first login)
   ```

3. **Set new password:**
   ```bash
   # System will prompt:
   Current password: ubuntu
   New password: [your-secure-password]
   Retype password: [your-secure-password]
   ```

4. **You're in!** ✅

---

## Option 2: Ethernet Cable (Recommended)

### What You Need:
- 🔌 Ethernet cable
- 🌐 Router with available port

### Steps:

1. **Connect Ethernet:**
   ```
   Pi → Ethernet Cable → Router
   Pi → Power (already connected)
   ```

2. **Wait 2 minutes** for Pi to boot and get IP from DHCP

3. **Find Pi's IP address:**

   **Option A - Check Router:**
   - Login to your router admin panel (usually http://192.168.1.1)
   - Look for connected devices
   - Find device named "ubuntu" or "raspberrypi"
   - Note the IP (e.g., 192.168.1.150)

   **Option B - Network Scan (from your PC):**
   ```bash
   # Windows (install Advanced IP Scanner)
   # Download: https://www.advanced-ip-scanner.com/

   # Linux/Mac
   sudo nmap -sn 192.168.1.0/24
   # Look for "ubuntu" or Raspberry Pi MAC address (starts with b8:27:eb or dc:a6:32)
   ```

   **Option C - Router DHCP Leases:**
   ```bash
   # Login to router, check DHCP leases table
   # Look for "ubuntu" hostname
   ```

4. **SSH to Pi:**
   ```bash
   ssh ubuntu@192.168.1.150  # Replace with your Pi's IP

   Password: ubuntu
   # (Change password on first login)
   ```

5. **You're in!** ✅

---

## Option 3: USB Serial Console (Advanced)

### What You Need:
- 🔌 USB-to-TTL serial adapter
- 🔧 GPIO pin access on Pi

### Steps:
(Less common, skip if you have monitor or ethernet)

---

## 🌐 Step 2: Configure WiFi

Once connected (via monitor or SSH), configure WiFi:

### Ubuntu Server WiFi Setup

1. **Check network interfaces:**
   ```bash
   ip a
   # Look for wlan0 or similar WiFi interface
   ```

2. **Configure netplan:**
   ```bash
   sudo nano /etc/netplan/50-cloud-init.yaml
   ```

3. **Add WiFi configuration:**
   ```yaml
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
   ```

4. **Apply configuration:**
   ```bash
   sudo netplan generate
   sudo netplan apply
   ```

5. **Test WiFi connection:**
   ```bash
   # Wait 10 seconds, then check
   ip a show wlan0
   # Should show IP address

   # Test internet
   ping -c 4 8.8.8.8
   ```

6. **Get WiFi IP address:**
   ```bash
   hostname -I
   # Note the WiFi IP (e.g., 192.168.1.151)
   ```

7. **You can now disconnect Ethernet!** ✅

---

## 🔐 Step 3: Set Up SSH for Remote Access

### Enable SSH (should already be enabled on Ubuntu Server)

1. **Check SSH status:**
   ```bash
   sudo systemctl status ssh
   # Should show "active (running)"
   ```

2. **If not running:**
   ```bash
   sudo systemctl enable ssh
   sudo systemctl start ssh
   ```

### Set Up SSH Key (from your PC)

**From your Windows PC:**

```powershell
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter for default location
# Set passphrase (optional but recommended)

# Copy public key to Pi
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh ubuntu@192.168.1.151 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Enter Pi password one last time

# Test passwordless login
ssh ubuntu@192.168.1.151
# Should login without password! ✅
```

---

## 📦 Step 4: Install Required Software

### Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Logout and login for group to take effect
exit
ssh ubuntu@192.168.1.151

# Test Docker
docker --version
docker-compose --version
```

### Install Python & Dependencies

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### Install Essential Tools

```bash
sudo apt install -y \
  curl \
  wget \
  vim \
  htop \
  tmux \
  net-tools \
  ufw
```

---

## 🔥 Step 5: Configure Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow API port
sudo ufw allow 3001/tcp

# Allow Grafana
sudo ufw allow 3000/tcp

# Allow InfluxDB
sudo ufw allow 8086/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 📂 Step 6: Set Up Project Directory

```bash
# Create project directory
sudo mkdir -p /opt/agritech
sudo chown ubuntu:ubuntu /opt/agritech

# Clone repository (or create manually)
cd /opt/agritech
git clone https://github.com/t0118430/technological_foods.git
cd technological_foods

# Or create directory structure manually
mkdir -p backend/api backend/data backend/logs
```

---

## 🎯 Step 7: Set Up Two Environments (Dev & Prod)

### Create Environment Structure

```bash
cd /opt/agritech/technological_foods

# Create environment-specific configs
mkdir -p envs/dev envs/prod

# Create dev environment file
cat > envs/dev/.env <<EOF
# Development Environment
ENVIRONMENT=development
API_PORT=3001
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=dev-token-change-me
INFLUXDB_ORG=agritech-dev
INFLUXDB_BUCKET=hydroponics-dev
API_KEY=agritech-dev-key-2026
NTFY_TOPIC=techfoods-dev
LOG_LEVEL=DEBUG
EOF

# Create prod environment file
cat > envs/prod/.env <<EOF
# Production Environment
ENVIRONMENT=production
API_PORT=3002
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=prod-token-change-me-secure
INFLUXDB_ORG=agritech-prod
INFLUXDB_BUCKET=hydroponics-prod
API_KEY=agritech-prod-key-2026
NTFY_TOPIC=techfoods
LOG_LEVEL=INFO
EOF

# Secure the files
chmod 600 envs/dev/.env envs/prod/.env
```

### Create Environment-Specific Docker Compose

```bash
# Development docker-compose
cat > envs/dev/docker-compose.yml <<EOF
version: '3.8'

services:
  influxdb-dev:
    image: influxdb:2.7
    container_name: agritech-influxdb-dev
    ports:
      - "8086:8086"
    volumes:
      - ./data/influxdb-dev:/var/lib/influxdb2
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: devpassword
      DOCKER_INFLUXDB_INIT_ORG: agritech-dev
      DOCKER_INFLUXDB_INIT_BUCKET: hydroponics-dev
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: dev-token-change-me
    restart: unless-stopped

  grafana-dev:
    image: grafana/grafana:latest
    container_name: agritech-grafana-dev
    ports:
      - "3000:3000"
    volumes:
      - ./data/grafana-dev:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: devpassword
      GF_INSTALL_PLUGINS: grafana-clock-panel
    restart: unless-stopped
EOF

# Production docker-compose
cat > envs/prod/docker-compose.yml <<EOF
version: '3.8'

services:
  influxdb-prod:
    image: influxdb:2.7
    container_name: agritech-influxdb-prod
    ports:
      - "8087:8086"  # Different port!
    volumes:
      - ./data/influxdb-prod:/var/lib/influxdb2
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: CHANGE_THIS_SECURE_PASSWORD
      DOCKER_INFLUXDB_INIT_ORG: agritech-prod
      DOCKER_INFLUXDB_INIT_BUCKET: hydroponics-prod
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: prod-token-change-me-secure
    restart: unless-stopped

  grafana-prod:
    image: grafana/grafana:latest
    container_name: agritech-grafana-prod
    ports:
      - "3001:3000"  # Different port!
    volumes:
      - ./data/grafana-prod:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: CHANGE_THIS_SECURE_PASSWORD
      GF_INSTALL_PLUGINS: grafana-clock-panel
    restart: unless-stopped
EOF
```

---

## 🚀 Step 8: Start Services

### Start Development Environment

```bash
cd /opt/agritech/technological_foods/envs/dev
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Start Production Environment

```bash
cd /opt/agritech/technological_foods/envs/prod
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Verify Services

```bash
# Check running containers
docker ps

# Should see:
# - agritech-influxdb-dev (port 8086)
# - agritech-grafana-dev (port 3000)
# - agritech-influxdb-prod (port 8087)
# - agritech-grafana-prod (port 3001)
```

---

## 🌐 Access Your Environments

### Development Environment

```
API:      http://192.168.1.151:3001
InfluxDB: http://192.168.1.151:8086
Grafana:  http://192.168.1.151:3000
          (admin / devpassword)
```

### Production Environment

```
API:      http://192.168.1.151:3002
InfluxDB: http://192.168.1.151:8087
Grafana:  http://192.168.1.151:3001
          (admin / [your-secure-password])
```

---

## ✅ Quick Verification Checklist

- [ ] Pi connected and powered on
- [ ] SSH access working
- [ ] WiFi configured and connected
- [ ] Docker installed and running
- [ ] Dev environment running (ports 3001, 8086, 3000)
- [ ] Prod environment running (ports 3002, 8087, 3001)
- [ ] Firewall configured
- [ ] Can access Grafana dashboards
- [ ] Can access InfluxDB UI

---

## 🛠️ Troubleshooting

### Can't Find Pi's IP

```bash
# Method 1: Check router DHCP table
# Login to router at http://192.168.1.1

# Method 2: Network scan from PC
# Windows: Use Advanced IP Scanner
# Linux/Mac:
nmap -sn 192.168.1.0/24 | grep -B 2 "Raspberry"
```

### WiFi Not Working

```bash
# Check WiFi interface
ip link show wlan0

# If down, bring it up
sudo ip link set wlan0 up

# Scan for networks
sudo iwlist wlan0 scan | grep ESSID

# Check netplan config
cat /etc/netplan/50-cloud-init.yaml

# Reapply netplan
sudo netplan --debug apply
```

### SSH Connection Refused

```bash
# Check SSH service on Pi (via monitor/keyboard)
sudo systemctl status ssh

# Start if not running
sudo systemctl start ssh
sudo systemctl enable ssh

# Check firewall
sudo ufw status
sudo ufw allow 22/tcp
```

### Docker Containers Won't Start

```bash
# Check Docker service
sudo systemctl status docker

# Check container logs
docker logs agritech-influxdb-dev

# Restart containers
cd envs/dev
docker-compose down
docker-compose up -d
```

---

## 📝 Next Steps

1. ✅ Pi connected and accessible
2. 🔄 Configure GitHub Actions to deploy to both environments
3. 🔐 Set up proper secrets and passwords
4. 🤖 Configure Arduino to send data to both environments
5. 📊 Set up Grafana dashboards for both environments

---

**Status**: Pi Setup Complete! 🎉
**Environments**: Dev (3001) & Prod (3002) running side-by-side
**Ready for**: Automated deployments from GitHub Actions
