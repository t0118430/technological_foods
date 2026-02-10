# 🚀 AgriTech Deployment Strategy

## Two-Tier Architecture

Our system has **two separate deployment targets** that require different strategies:

```
┌─────────────────────────────────────────────────────────┐
│                    AgriTech System                      │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌──────────────────────┐        ┌──────────────────────┐
│   Raspberry Pi       │        │   Arduino R4 WiFi    │
│   (Server)           │◄───────┤   (IoT Device)       │
│                      │  WiFi  │                      │
│  • Backend API       │        │  • Sensor readings   │
│  • InfluxDB          │        │  • Data transmission │
│  • Grafana           │        │  • Remote location   │
│  • Node-RED          │        │                      │
└──────────────────────┘        └──────────────────────┘
         │                               │
         │                               │
    Deploy via SSH                  Deploy via OTA
    (wired/VPN)                     (over WiFi)
```

---

## 🖥️ Server Deployment (Raspberry Pi)

### Workflow: `deploy-server-pi.yml`

**Target**: Raspberry Pi server
**Method**: SSH + rsync
**Triggers**: Push to `master` affecting `backend/**`

### What Gets Deployed

- ✅ Python backend API
- ✅ Docker services (InfluxDB, Grafana, Node-RED)
- ✅ Configuration files
- ✅ Database schemas
- ✅ Systemd services

### Deployment Flow

```
1. Run Tests
   ├─ Unit tests (pytest)
   ├─ Integration tests
   ├─ Config validation
   └─ Security scan
      │
2. Create Backup
   └─ Backup database & configs
      │
3. Deploy Code
   └─ rsync to Raspberry Pi
      │
4. Restart Services
   ├─ Docker containers
   └─ systemd services
      │
5. Health Check
   └─ Verify all endpoints
      │
6. Rollback if Failed ─┐
                       │
7. Send Notification ──┘
```

### Requirements

**GitHub Secrets:**
- `PI_SSH_KEY` - SSH private key
- `PI_HOST` - Pi hostname/IP (e.g., `192.168.1.10`)
- `PI_USER` - SSH username (e.g., `pi`)
- `PI_PROJECT_PATH` - Project directory on Pi

**Commands:**
```bash
# Manual deployment
ssh pi@<pi-ip>
cd /path/to/project
git pull origin master
./deploy/backup.sh pre-manual
docker-compose up -d
systemctl restart agritech-api
./deploy/health-check.sh
```

---

## 🤖 Arduino Deployment (IoT Device)

### Workflow: `deploy-arduino-ota.yml`

**Target**: Arduino R4 WiFi (remote IoT device)
**Method**: OTA (Over-The-Air) via WiFi
**Triggers**: Push to `master` affecting `arduino/**`

### What Gets Deployed

- ✅ Firmware binary (.bin)
- ✅ Sensor reading logic
- ✅ WiFi configuration
- ✅ API client code

### Deployment Flow

```
1. Build Firmware
   ├─ Compile Arduino sketch
   ├─ Generate .bin file
   └─ Calculate checksum
      │
2. Upload to Artifact
   └─ Store .bin for download
      │
3. Deploy via OTA
   ├─ Connect to Arduino over WiFi
   ├─ Upload firmware binary
   └─ Arduino reboots automatically
      │
4. Verify Deployment
   └─ Check new firmware version
      │
5. Create Release ─────┐
                       │
6. Send Notification ──┘
```

### Requirements

**GitHub Secrets:**
- `ARDUINO_IP` - Arduino IP address (e.g., `192.168.1.100`)
- `ARDUINO_OTA_PASSWORD` - OTA password (optional but recommended)

**Commands:**
```bash
# Manual OTA deployment
cd arduino/ota-tools
python deploy_ota.py \
  --ip 192.168.1.100 \
  --password secret \
  --firmware ../build/sketch.bin

# USB fallback (if OTA fails)
arduino-cli upload \
  --fqbn arduino:renesas_uno:unor4wifi \
  --port COM3 \
  --input-file sketch.bin
```

---

## 🔄 Deployment Scenarios

### 1. Backend Change Only

**Example**: Update business logic, add API endpoint

```bash
# Triggers: deploy-server-pi.yml
git add backend/api/new_feature.py
git commit -m "feat: add new API endpoint"
git push origin master

# Result:
✅ Server tests run
✅ Pi gets new code
❌ Arduino NOT redeployed (no firmware change)
```

### 2. Firmware Change Only

**Example**: Fix sensor reading bug, update Arduino code

```bash
# Triggers: deploy-arduino-ota.yml
git add arduino/temp_hum_light_sending_api/temp_hum_light_sending_api.ino
git commit -m "fix: correct humidity calculation"
git push origin master

# Result:
✅ Firmware compiled
✅ Arduino gets OTA update
❌ Pi NOT redeployed (no backend change)
```

### 3. Full System Update

**Example**: Change API protocol affecting both server and Arduino

```bash
# Triggers: BOTH workflows
git add backend/api/protocol.py arduino/temp_hum_light_sending_api/api_client.cpp
git commit -m "feat: update API protocol to v2"
git push origin master

# Result:
✅ Both workflows run in parallel
✅ Server deployed first (faster)
✅ Arduino OTA deployed second
✅ Both systems updated independently
```

---

## ⚠️ Important Considerations

### Network Topology

```
Internet
   │
   └─ GitHub Actions Runner
         │
         ├─── SSH ────► Raspberry Pi (Server)
         │              192.168.1.10
         │              - Wired/WiFi connection
         │              - Always accessible via VPN/port forward
         │
         └─── WiFi OTA ► Arduino R4 WiFi (IoT Device)
                        192.168.1.100
                        - Wireless only
                        - May move locations
                        - Dynamic IP possible
```

### Arduino OTA Limitations

⚠️ **OTA Requires**:
- Arduino connected to WiFi
- Arduino IP must be reachable from GitHub Actions
- Network allows outbound connections from GitHub
- Firewall permits traffic to Arduino OTA port (8080)

🔧 **Solutions**:
- **Option A**: Port forward Arduino OTA port through router
- **Option B**: Use VPN tunnel (WireGuard/Tailscale)
- **Option C**: Manual deployment via laptop on same network
- **Option D**: Deploy via Pi as intermediary (Pi flashes Arduino)

### Deployment via Pi (Recommended)

If GitHub Actions can't reach Arduino directly:

**Modified workflow** - Deploy Arduino **through** Pi:

```yaml
# In deploy-arduino-ota.yml
- name: Deploy via Pi as intermediary
  run: |
    # Upload firmware to Pi first
    scp firmware.bin pi@<pi-ip>:/tmp/

    # Pi deploys to Arduino (same local network)
    ssh pi@<pi-ip> "cd /path/to/project/arduino/ota-tools && \
      python deploy_ota.py --ip $ARDUINO_IP --firmware /tmp/firmware.bin"
```

**Advantages**:
- ✅ Pi always accessible (VPN/SSH)
- ✅ Pi and Arduino on same local network
- ✅ No need to expose Arduino to internet
- ✅ Works even with dynamic Arduino IP

---

## 📊 Deployment Matrix

| Component | Method | Trigger | Frequency | Downtime |
|-----------|--------|---------|-----------|----------|
| **Backend API** | SSH/rsync | `backend/**` change | Multiple/day | ~10s |
| **Docker services** | docker-compose | Backend change | Rare | ~30s |
| **Database schema** | Migration scripts | Schema change | Weekly | ~5s |
| **Arduino firmware** | OTA WiFi | `arduino/**` change | Weekly | ~15s |
| **Config files** | SSH/rsync | Config change | As needed | 0s |

---

## 🚨 Rollback Procedures

### Server Rollback

```bash
# Automatic (in CI/CD)
./deploy/restore.sh pre-deploy

# Manual
ssh pi@<pi-ip>
cd /path/to/project
./deploy/restore.sh <backup-name>
systemctl restart agritech-api
docker-compose restart
```

### Arduino Rollback

```bash
# OTA rollback to previous version
cd arduino/ota-tools
python deploy_ota.py --ip 192.168.1.100 --firmware ../backups/v1.2.0.bin

# USB rollback (if OTA fails)
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port COM3 --input-file backup.bin
```

---

## 🔐 Security

### Server (Pi)

- ✅ SSH key authentication (no passwords)
- ✅ Firewall (only open required ports)
- ✅ VPN access (WireGuard recommended)
- ✅ Regular security updates
- ✅ Fail2ban for SSH protection

### Arduino (IoT)

- ✅ WPA2/WPA3 WiFi encryption
- ✅ OTA password protection
- ✅ API key for sensor data upload
- ✅ HTTPS for API calls (if supported)
- ⚠️ OTA updates not encrypted (use VPN if sensitive)

---

## 📈 Deployment Metrics

### Success Rate Targets

- Server deployment: **>99%** success
- Arduino OTA: **>95%** success (network dependent)
- Average deploy time: **<5 minutes**
- Rollback time: **<2 minutes**

### Monitoring

```bash
# Check deployment status
gh run list --workflow=deploy-server-pi.yml
gh run list --workflow=deploy-arduino-ota.yml

# View logs
gh run view <run-id> --log
```

---

## 🎯 Best Practices

### Before Deployment

- [ ] All tests passing locally
- [ ] Code reviewed and approved
- [ ] Database migrations prepared
- [ ] Backup verified
- [ ] Rollback plan documented

### During Deployment

- [ ] Monitor logs in real-time
- [ ] Verify health checks pass
- [ ] Test critical endpoints
- [ ] Check sensor data flowing

### After Deployment

- [ ] Verify new features working
- [ ] Monitor error rates
- [ ] Check system resources
- [ ] Update documentation
- [ ] Notify stakeholders

---

## 🔮 Future Enhancements

### Planned

- [ ] **Blue-green deployment** for zero-downtime server updates
- [ ] **Canary deployment** for Arduino (test on one device first)
- [ ] **Automatic rollback** on health check failure
- [ ] **Deploy via Pi intermediary** for better Arduino access
- [ ] **Multi-Arduino fleet management** (deploy to multiple devices)

### Under Consideration

- [ ] **Kubernetes** for server orchestration
- [ ] **A/B testing** framework for features
- [ ] **Staged rollout** (dev → staging → production)
- [ ] **Smoke tests** after deployment

---

**Status**: ✅ Production Ready
**Last Updated**: 2026-02-08
**Architecture**: Two-tier (Server + IoT)
**Deployment Methods**: SSH (Server) + OTA (Arduino)
