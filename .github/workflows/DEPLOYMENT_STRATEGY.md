# AgriTech Deployment Strategy

## Two-Tier Architecture

The system deploys to **two separate hardware targets** using a single unified pipeline (`deploy.yml`) that detects which components changed and deploys selectively.

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub (master)                       │
│         PR merged → deploy.yml triggered                │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │ detect-changes                │
        │ (dorny/paths-filter)          │
        └───────┬───────────────┬───────┘
                │               │
   backend/**   │               │  arduino/**
   or infra/**  │               │
                ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│   Raspberry Pi       │  │   Arduino R4 WiFi    │
│   (Server)           │  │   (IoT Device)       │
│                      │  │                      │
│  • Backend API       │  │  • Sensor readings   │
│  • InfluxDB          │  │  • Data transmission │
│  • Grafana           │  │  • Remote location   │
│  • Node-RED          │  │                      │
└──────────────────────┘  └──────────────────────┘
         │                         │
    Deploy via SSH            Deploy via OTA
    Selective rsync           Over WiFi
    (backend/ + infra/)       (firmware .bin)
```

---

## PR Gate

All code must pass through a pull request before reaching `master`. The `pr-checks.yml` workflow:

1. Detects which directories changed
2. Runs only the relevant checks (backend tests, arduino compile, etc.)
3. Posts a **deployment preview** comment on the PR showing exactly what will deploy where
4. All required checks must pass before merge is allowed

---

## Server Deployment (Raspberry Pi)

### Workflow: `deploy.yml` → `deploy-backend` job

**Trigger**: Push to `master` with changes in `backend/**` or `infra/**`
**Method**: SSH + selective rsync

### What Gets Deployed (targeted)

```bash
# Only backend files (NOT the entire repo)
rsync -avz backend/ pi@host:/path/backend/

# Only infra files (if changed)
rsync -avz infra/ pi@host:/path/infra/
```

### Deployment Flow

```
1. Run sanity tests (lint + unit)
2. SSH → Create backup on Pi
3. Selective rsync (backend/ and/or infra/ only)
4. Restart Docker + systemd services
5. Health check
6. On failure → automatic rollback + notify
7. On success → ntfy notification
```

---

## Arduino Deployment (IoT Device)

### Workflow: `deploy.yml` → `deploy-arduino` job

**Trigger**: Push to `master` with changes in `arduino/**`
**Method**: OTA (Over-The-Air) via WiFi

### Deployment Flow

```
1. Build firmware with arduino-cli
2. Calculate SHA256 checksum
3. Upload artifact
4. Deploy .bin via OTA to Arduino
5. Verify (health endpoint)
6. Create GitHub release with firmware
7. ntfy notification
```

---

## Deployment Scenarios

### Backend Only
```
PR changes: backend/api/server.py
Result:
  ✅ Backend tests run in PR checks
  ✅ deploy-backend job runs after merge
  ⏭️  deploy-arduino skipped (no arduino changes)
```

### Arduino Only
```
PR changes: arduino/temp_hum_light_sending_api/main.ino
Result:
  ✅ Arduino compile check runs in PR checks
  ⏭️  deploy-backend skipped (no backend changes)
  ✅ deploy-arduino job runs after merge
```

### Full System
```
PR changes: backend/ + arduino/
Result:
  ✅ All checks run in PR checks
  ✅ deploy-backend runs after merge
  ✅ deploy-arduino runs after merge (in parallel)
```

### Infra Only
```
PR changes: infra/systemd/agritech-api.service
Result:
  ✅ deploy-backend runs (infra triggers Pi deploy)
  ⏭️  deploy-arduino skipped
```

---

## Deployment Matrix

| Component | Target | Method | Trigger | Downtime |
|-----------|--------|--------|---------|----------|
| Backend API | Pi | SSH/rsync | `backend/**` | ~10s |
| Docker services | Pi | docker-compose | `backend/**` | ~30s |
| Infra configs | Pi | SSH/rsync | `infra/**` | ~5s |
| Arduino firmware | Arduino | OTA WiFi | `arduino/**` | ~15s |

---

## Rollback

### Backend (automatic)
Pipeline auto-rolls back if health check fails:
1. Restores from pre-deploy backup
2. Restarts systemd + Docker services
3. Sends failure notification

### Backend (manual)
```bash
ssh pi@<pi-ip>
cd /path/to/technological_foods
./deploy/restore.sh pre-deploy
sudo systemctl restart agritech-api.service
cd backend && docker-compose restart
```

### Arduino
```bash
# OTA rollback to previous version
cd arduino/ota-tools
python deploy_ota.py --ip <ip> --firmware ../backups/v1.2.0.bin

# USB fallback
arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port <port> --input-file backup.bin
```

---

## Network Topology

```
Internet
   │
   └─ GitHub Actions Runner
         │
         ├─── SSH ────► Raspberry Pi (Server)
         │              - Wired/WiFi connection
         │              - Accessible via VPN/port forward
         │
         └─── OTA ───► Arduino R4 WiFi (IoT Device)
                       - WiFi only
                       - Reachable from GitHub Actions or via Pi intermediary
```

### Arduino OTA via Pi Intermediary (recommended)

If GitHub Actions can't reach the Arduino directly:

```bash
# Upload firmware to Pi first
scp firmware.bin pi@<pi-ip>:/tmp/

# Pi deploys to Arduino (same local network)
ssh pi@<pi-ip> "cd /path/to/project/arduino/ota-tools && \
  python deploy_ota.py --ip $ARDUINO_IP --firmware /tmp/firmware.bin"
```

---

## Security

### Server (Pi)
- SSH key authentication (no passwords)
- Selective rsync (only deploys what changed, not entire repo)
- Pre-deploy backups with automatic rollback
- Health checks before declaring success

### Arduino (IoT)
- WPA2/WPA3 WiFi encryption
- OTA password protection
- API key for sensor data upload
- Firmware checksum verification

---

**Last Updated**: 2026-02-10
