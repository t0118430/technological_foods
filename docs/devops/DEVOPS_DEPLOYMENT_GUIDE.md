# 🚀 AgriTech Complete DevOps Deployment Guide

**Your Complete Raspberry Pi + GitHub Actions + Business Intelligence System**

---

## 📋 **What You're Building**

A **production-ready agricultural monitoring platform** with:

✅ **GitHub Actions CI/CD** - Automatic deployment on git push
✅ **Raspberry Pi 4 (4GB, 64GB SD)** - Edge computing with local data
✅ **USB SSD Backups** - Off-device disaster recovery
✅ **Multi-Channel Alerts** - Redundant ntfy notifications
✅ **Auto-Restart Services** - systemd watchdogs
✅ **B2B Client Management** - Calibration tracking + revenue
✅ **Business Intelligence** - Daily digest reports
✅ **Dual-Sensor Redundancy** - Automatic drift detection

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐          │
│  │   Backend  │  │   Arduino  │  │  systemd     │          │
│  │   Python   │  │   Sketch   │  │  Services    │          │
│  └────────────┘  └────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            ↓ (git push)
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Runner                     │
│  1. Run tests                                                │
│  2. Validate configs                                         │
│  3. Deploy via SSH to Raspberry Pi                          │
│  4. Health check                                            │
│  5. Rollback on failure                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓ (SSH rsync)
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi 4 (Production)                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Docker Compose (3 containers)                     │    │
│  │  ├─ InfluxDB:8086  → /data/influxdb               │    │
│  │  ├─ Grafana:3000   → /data/grafana                │    │
│  │  └─ Node-RED:1880  → /data/nodered                │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  API Server (systemd)                              │    │
│  │  └─ server.py:3001 → /data/sqlite/agritech.db     │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Automated Services (systemd timers)               │    │
│  │  ├─ Daily backups → /backups (USB SSD)            │    │
│  │  ├─ Health monitoring (every 5 min)               │    │
│  │  └─ Business digest (daily 2 AM)                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↑ (WiFi/LTE)
┌─────────────────────────────────────────────────────────────┐
│           Arduino UNO R4 WiFi (Sensors)                      │
│  ├─ DHT20 Temperature/Humidity                              │
│  └─ POST /api/data every 2 seconds                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **Quick Start (30 Minutes)**

### **Step 1: Prepare Raspberry Pi** (10 min)

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit) to SD card
# 2. Boot Pi, SSH in
ssh pi@raspberrypi.local

# 3. Run setup script
git clone <your-repo> ~/agritech
cd ~/agritech
sudo ./deploy/setup-pi.sh

# 4. Reboot
sudo reboot
```

### **Step 2: Configure Environment** (5 min)

```bash
# Copy and edit .env file
cd ~/agritech/backend
cp .env.example .env
nano .env

# Set these variables:
NTFY_TOPIC_CLIENT=agritech-client-yourname
NTFY_TOPIC_BUSINESS=agritech-business-yourname
NTFY_TOPIC_EMERGENCY=agritech-emergency-yourname
```

### **Step 3: Mount USB Backup Drive** (2 min)

```bash
# Plug in USB SSD, identify device
lsblk

# Mount it (replace /dev/sda1 with your device)
sudo ./deploy/mount-usb-backup.sh /dev/sda1
```

### **Step 4: Install systemd Services** (3 min)

```bash
sudo ./deploy/install-services.sh
sudo systemctl start agritech-docker
sudo systemctl start agritech-api
```

### **Step 5: Verify Everything Works** (5 min)

```bash
# Check service status
sudo systemctl status agritech-*

# Check Docker containers
docker ps

# Test API
curl http://localhost:3001/api/data/latest

# Send test notification
curl -X POST http://localhost:3001/api/notifications/test
```

### **Step 6: Configure GitHub Actions** (5 min)

```bash
# Generate SSH key on Pi
ssh-keygen -t ed25519 -f ~/.ssh/github_actions

# Display private key (copy this)
cat ~/.ssh/github_actions

# Add public key to authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
```

**On GitHub:**
1. Go to repository → Settings → Secrets and variables → Actions
2. Add secrets:
   - `PI_SSH_KEY` = (private key from above)
   - `PI_HOST` = (your Pi's IP address or hostname)
   - `PI_USER` = `pi`
   - `PI_PROJECT_PATH` = `/home/pi/agritech`
   - `NTFY_TOPIC_URL` = `https://ntfy.sh/agritech-business-yourname`

**Test deployment:**
```bash
# Push to GitHub
git add .
git commit -m "Initial deployment setup"
git push origin master

# Watch GitHub Actions run automatically!
```

---

## 📱 **Multi-Channel Notification Setup**

### **1. Install ntfy App**
- Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy
- iOS: https://apps.apple.com/app/ntfy/id1625396347

### **2. Subscribe to Your Topics**
- Open app → + button
- Add `agritech-client-yourname` (public client alerts)
- Add `agritech-business-yourname` (private business reports)
- Add `agritech-emergency-yourname` (critical system)

### **3. Configure WhatsApp (Optional)**

**Get Twilio Account:**
1. Sign up at https://www.twilio.com
2. Get phone number with WhatsApp enabled
3. Find Account SID and Auth Token

**Add to `.env`:**
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=+14155238886
TWILIO_WHATSAPP_TO=+351912345678
```

**Test:**
```bash
cd backend/api
python3 test_real_notification.py
```

---

## 🔧 **Client Management (B2B Features)**

### **Add Your First Client**

```bash
curl -X POST http://localhost:3001/api/clients \
  -H "Content-Type: application/json" \
  -H "X-API-Key: agritech-secret-key-2026" \
  -d '{
    "company_name": "Quinta do João",
    "contact_name": "João Silva",
    "contact_phone": "+351912345678",
    "contact_email": "joao@quinta.pt",
    "service_tier": "silver",
    "location": "Évora, Portugal"
  }'
```

### **Register Client Sensors**

```bash
# Add sensors for the client (ID=1)
curl -X POST http://localhost:3001/api/clients/1/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "temperature",
    "serial_number": "DHT20-00123"
  }'
```

### **Record Service Visit**

```bash
curl -X POST http://localhost:3001/api/clients/1/visits \
  -H "Content-Type: application/json" \
  -d '{
    "technician": "António Técnico",
    "service_type": "calibration",
    "sensors_serviced": [1, 2],
    "issues_found": "Sensor drift detected",
    "actions_taken": "Recalibrated both sensors",
    "revenue": 75.0
  }'
```

### **Get Daily Business Digest**

Automatically sent to **BUSINESS_PRIVATE** channel every day at 2 AM.

**Manual trigger:**
```bash
curl -X POST http://localhost:3001/api/business/send-digest
```

---

## 💾 **Backup Strategy**

### **Automatic Daily Backups** (systemd timer)

- **When:** Every day at 2:00 AM (±15 min random)
- **What:** SQLite database, InfluxDB data, configs
- **Where:** `/backups/daily/`
- **Retention:** 7 daily, 4 weekly, 12 monthly

### **Manual Backup**

```bash
# Full backup now
sudo systemctl start agritech-backup.service

# Check backup status
journalctl -u agritech-backup -n 50
```

### **Restore from Backup**

```bash
# List available backups
ls -lh /backups/daily/

# Restore specific backup
sudo ./deploy/restore.sh /backups/daily/agritech_20260208.db

# Verify restore worked
curl http://localhost:3001/api/crops
```

---

## 🔥 **Disaster Recovery Plan**

### **Scenario 1: SD Card Corrupts**

1. Flash new SD card with Raspberry Pi OS
2. Run `./deploy/setup-pi.sh`
3. Restore from USB backup:
   ```bash
   sudo ./deploy/restore.sh /backups/daily/latest.db
   ```
4. Start services:
   ```bash
   sudo systemctl start agritech-docker agritech-api
   ```

### **Scenario 2: Complete Pi Failure**

1. Buy new Raspberry Pi
2. Flash SD card, run setup script
3. Mount USB backup drive
4. Restore latest backup
5. Update GitHub Actions `PI_HOST` secret with new IP

**Downtime:** ~1 hour

### **Scenario 3: Accidental Data Deletion**

1. Stop services:
   ```bash
   sudo systemctl stop agritech-api
   ```
2. Restore from backup (select time before deletion)
3. Restart services

---

## 📊 **Monitoring & Maintenance**

### **Daily Tasks** (Automated)
- ✅ Backup database to USB
- ✅ Send business digest
- ✅ Check sensor health scores
- ✅ Monitor disk space

### **Weekly Tasks** (Manual)
- 📞 Call clients with health score < 70
- 📅 Schedule calibration visits
- 💰 Generate invoices

### **Monthly Tasks**
- 📊 Review revenue metrics
- 🎯 Identify upsell opportunities
- 🔧 Analyze sensor failure patterns

### **Check System Health**

```bash
# Service status
sudo systemctl status agritech-*

# Docker containers
docker ps
docker stats

# Disk usage (critical on 64GB SD)
df -h
du -sh /data/*

# System resources
htop

# Recent logs
journalctl -u agritech-api -n 100
journalctl -u agritech-docker -n 100
```

---

## 🚨 **Troubleshooting**

### **Problem: API Server Won't Start**

```bash
# Check logs
journalctl -u agritech-api.service -n 50

# Run manually to see errors
cd ~/agritech/backend/api
python3 server.py

# Common fixes:
sudo systemctl restart agritech-docker  # Ensure InfluxDB is up
sudo systemctl restart agritech-api
```

### **Problem: Docker Out of Memory**

```bash
# Check memory usage
free -h
docker stats

# Restart containers to clear memory
sudo systemctl restart agritech-docker
```

### **Problem: SD Card Full (64GB)**

```bash
# Check disk usage
df -h
du -sh /data/*

# Clean up old data
# Reduce InfluxDB retention
docker exec agritech-influxdb influx bucket update \
  --id <bucket-id> --retention 15d

# Clean Docker
docker system prune -a
```

### **Problem: Deployment Failed**

```bash
# Check GitHub Actions logs on GitHub.com

# Manual rollback on Pi
cd ~/agritech
git log  # Find previous commit
git checkout <previous-commit>
sudo systemctl restart agritech-api
```

---

## 📈 **Scaling to 10+ Clients**

When you outgrow the single Raspberry Pi:

### **Option 1: Upgrade to Mini Server**
- Intel NUC 11 Pro (16GB RAM, 500GB SSD)
- Cost: €500-800
- Supports: 30-50 clients

### **Option 2: Cloud VPS**
- Hetzner CPX31 (4 vCPU, 8GB RAM)
- Cost: €14/month
- Supports: Unlimited clients

### **Migration Steps**
1. Set up new server with PostgreSQL (replace SQLite)
2. Export data: `sqlite3 agritech.db .dump > backup.sql`
3. Import to PostgreSQL
4. Update `.env` with new database URL
5. Deploy to new server via GitHub Actions

---

## 💡 **Pro Tips**

### **Save Bandwidth on SIM Router**
```bash
# Disable Grafana analytics
GF_ANALYTICS_REPORTING_ENABLED=false
GF_ANALYTICS_CHECK_FOR_UPDATES=false

# Reduce InfluxDB logging
INFLUXDB_LOG_LEVEL=warn
```

### **Optimize SD Card Longevity**
- ✅ Use `/tmp` for temporary files (RAM disk)
- ✅ Disable swap (`sudo dphys-swapfile swapoff`)
- ✅ Use USB SSD for heavy writes
- ✅ Mount with `noatime` flag

### **Security Hardening**
```bash
# Change default password
passwd

# Disable SSH password auth (key-only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no

# Enable fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## 📚 **Complete File Structure**

```
technological_foods/
├── .github/
│   └── workflows/
│       └── deploy-to-pi.yml          # CI/CD pipeline
├── arduino/
│   └── temp_hum_light_sending_api/
│       ├── temp_hum_light_sending_api.ino
│       └── config.h.example           # WiFi credentials template
├── backend/
│   ├── .env.example                   # Configuration template
│   ├── docker-compose.yml             # Base Docker config
│   ├── docker-compose.override.yml    # Pi-optimized config
│   ├── api/
│   │   ├── server.py                  # Main API server
│   │   ├── rule_engine.py             # Decision logic
│   │   ├── notification_service.py    # Single-channel alerts
│   │   ├── multi_channel_notifier.py  # Multi-channel system
│   │   ├── alert_escalation.py        # Smart escalation
│   │   ├── growth_stage_manager.py    # Crop lifecycle
│   │   ├── database.py                # SQLite ORM
│   │   ├── client_manager.py          # B2B client tracking
│   │   ├── ac_controller.py           # Haier AC integration
│   │   └── rules_config.json          # Rules (persisted)
│   ├── config/
│   │   ├── base_hydroponics.json
│   │   ├── variety_rosso_premium.json
│   │   └── variety_curly_green.json
│   └── data/
│       └── agritech.db                # SQLite (local, gitignored)
├── deploy/
│   ├── setup-pi.sh                    # Initial Pi setup
│   ├── install-services.sh            # systemd installation
│   ├── mount-usb-backup.sh            # USB SSD mounting
│   ├── backup.sh                      # Daily backup script
│   ├── restore.sh                     # Restore from backup
│   ├── backup-verify.sh               # Test backup integrity
│   ├── health-check.sh                # Service monitoring
│   └── auto-recovery.sh               # Auto-restart failed services
├── systemd/
│   ├── agritech-api.service           # API auto-restart
│   ├── agritech-docker.service        # Docker compose
│   ├── agritech-backup.service        # Backup job
│   ├── agritech-backup.timer          # Daily trigger
│   └── agritech-monitor.service       # Health checks
├── docs/
│   ├── BUSINESS_INTELLIGENCE.md       # B2B features guide
│   ├── GROWTH_STAGE_SYSTEM.md
│   ├── ALERT_ESCALATION.md
│   ├── PREVENTIVE_ALERTS.md
│   └── VARIETY_CONFIGS.md
└── DEVOPS_DEPLOYMENT_GUIDE.md         # This file
```

---

## 🎓 **Learning Resources**

### **Docker**
- Docs: https://docs.docker.com/
- Compose: https://docs.docker.com/compose/

### **InfluxDB**
- Query language: https://docs.influxdata.com/influxdb/v2/query-data/
- Retention policies: https://docs.influxdata.com/influxdb/v2/admin/buckets/

### **systemd**
- Service files: https://www.freedesktop.org/software/systemd/man/systemd.service.html
- Timers: https://www.freedesktop.org/software/systemd/man/systemd.timer.html

### **ntfy**
- API: https://docs.ntfy.sh/
- Self-hosting: https://docs.ntfy.sh/install/

---

## ✅ **Deployment Checklist**

Before going live:

- [ ] Raspberry Pi setup complete
- [ ] USB backup drive mounted and tested
- [ ] All systemd services running
- [ ] ntfy channels configured and tested
- [ ] GitHub Actions secrets configured
- [ ] First deployment successful
- [ ] Health checks passing
- [ ] Backup restore tested
- [ ] Client added and tested
- [ ] Service visit recorded
- [ ] Daily digest received
- [ ] Documentation reviewed

---

## 🎯 **Next Steps**

1. **Complete deployment** using this guide
2. **Test all features** with dummy data
3. **Add your first real client**
4. **Monitor for 1 week** to ensure stability
5. **Scale to 5 clients** to validate revenue model
6. **Iterate and improve** based on real usage

---

## 🤝 **Support**

- **Documentation:** Check all MD files in `docs/`
- **GitHub Issues:** https://github.com/anthropics/claude-code/issues
- **Community:** (your Discord/Slack if applicable)

---

**Built with ❤️ for agricultural innovation**

**Last Updated:** 2026-02-08
