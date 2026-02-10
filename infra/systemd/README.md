# systemd Service Files for AgriTech

These service files enable automatic startup, restart, and monitoring of AgriTech services on Raspberry Pi.

## Services Overview

| Service | Description | Auto-Start | Auto-Restart |
|---------|-------------|------------|--------------|
| `agritech-docker.service` | Docker Compose (InfluxDB, Grafana, Node-RED) | ✅ Yes | On failure |
| `agritech-api.service` | Python API server | ✅ Yes | Always |
| `agritech-backup.service` | Daily backup (triggered by timer) | ❌ Timer only | On failure |
| `agritech-backup.timer` | Backup scheduler (daily at 2 AM) | ✅ Yes | N/A |
| `agritech-monitor.service` | Health check monitor (every 5 min) | ✅ Yes | Always |

## Installation

Run the installation script on your Raspberry Pi:

```bash
cd /home/pi/agritech
sudo ./deploy/install-services.sh
```

Or manually install:

```bash
# Copy service files to systemd directory
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable agritech-docker.service
sudo systemctl enable agritech-api.service
sudo systemctl enable agritech-backup.timer
sudo systemctl enable agritech-monitor.service

# Start services immediately
sudo systemctl start agritech-docker.service
sudo systemctl start agritech-api.service
sudo systemctl start agritech-backup.timer
sudo systemctl start agritech-monitor.service
```

## Service Management

### Check Status

```bash
# All AgriTech services
sudo systemctl status agritech-*

# Individual service
sudo systemctl status agritech-api.service
```

### View Logs

```bash
# Real-time logs for API server
sudo journalctl -u agritech-api.service -f

# Last 100 lines from Docker services
sudo journalctl -u agritech-docker.service -n 100

# Backup logs (last 24 hours)
sudo journalctl -u agritech-backup.service --since "24 hours ago"
```

### Restart Services

```bash
# Restart API server
sudo systemctl restart agritech-api.service

# Restart Docker services
sudo systemctl restart agritech-docker.service

# Trigger manual backup
sudo systemctl start agritech-backup.service
```

### Stop Services

```bash
# Stop all AgriTech services
sudo systemctl stop agritech-api.service agritech-docker.service agritech-monitor.service
```

## Service Dependencies

```
Docker Service (system)
    ↓
agritech-docker.service (InfluxDB, Grafana, Node-RED)
    ↓
agritech-api.service (Python API)
    ↓
agritech-monitor.service (Health checks)

Parallel:
agritech-backup.timer → agritech-backup.service (Independent)
```

## Automatic Restart Behavior

### Docker Service (`agritech-docker.service`)
- **Restart on failure:** Yes (after 30 seconds)
- **Stop behavior:** Graceful shutdown with `docker-compose down`
- **Timeout:** 10 minutes for startup (Docker pulls), 2 minutes for shutdown

### API Service (`agritech-api.service`)
- **Restart always:** Even on clean exit (exits could be errors)
- **Watchdog:** Kills service if no response for 2 minutes
- **Memory limit:** 512MB (prevents OOM on Pi 4)
- **CPU limit:** 50% (leaves resources for Docker)

### Backup Service (`agritech-backup.service`)
- **Triggered by timer:** Daily at 2:00 AM (±15 min randomization)
- **Timeout:** 30 minutes (InfluxDB export can be large)
- **Notification on failure:** Sends ntfy alert if backup fails
- **Persistent:** Runs on next boot if Pi was off during scheduled time

### Monitor Service (`agritech-monitor.service`)
- **Runs continuously:** Checks health every 5 minutes
- **Auto-restart:** If monitoring script crashes
- **Resource limits:** 128MB memory, 10% CPU

## Resource Allocation (Total)

On Raspberry Pi 4 (4GB RAM):
- **Docker Compose:** ~2.5GB (InfluxDB 1.5GB, Grafana 512MB, Node-RED 512MB)
- **API Server:** ~512MB
- **System:** ~512MB
- **Monitor:** ~128MB
- **Free:** ~512MB buffer

## Troubleshooting

### Service fails to start
```bash
# Check detailed error logs
sudo journalctl -xe -u agritech-api.service

# Check if dependencies are running
sudo systemctl status docker.service
sudo systemctl status agritech-docker.service
```

### Service keeps restarting
```bash
# Disable auto-restart temporarily to debug
sudo systemctl stop agritech-api.service

# Run manually to see errors
cd /home/pi/agritech/backend/api
python3 server.py
```

### Backup timer not running
```bash
# Check timer status
sudo systemctl status agritech-backup.timer

# List all timers
sudo systemctl list-timers

# Check when next backup is scheduled
sudo systemctl list-timers agritech-backup.timer
```

### Memory issues (OOM)
```bash
# Check memory usage
free -h
docker stats

# Restart services to clear memory
sudo systemctl restart agritech-docker.service
sudo systemctl restart agritech-api.service
```

## Performance Monitoring

```bash
# Watch system resources in real-time
htop

# Monitor Docker container resources
docker stats

# Check systemd service resource usage
systemd-cgtop

# Check disk space (critical for 64GB SD card)
df -h
```

## Security Notes

- Services run as `pi` user (not root) for security
- `NoNewPrivileges=true` prevents privilege escalation
- `PrivateTmp=true` isolates /tmp directory
- Environment variables loaded from `.env` file (gitignored)
- API key authentication required for all endpoints

## Backup Verification

The backup timer runs daily, but you should verify backups work:

```bash
# Run test restore on a copy
cd /home/pi/agritech
./deploy/backup-verify.sh

# Check backup directory
ls -lh /backups/daily/
ls -lh /backups/weekly/
ls -lh /backups/monthly/
```

## Uninstallation

To remove all services:

```bash
# Stop and disable services
sudo systemctl stop agritech-*.service agritech-*.timer
sudo systemctl disable agritech-*.service agritech-*.timer

# Remove service files
sudo rm /etc/systemd/system/agritech-*.service
sudo rm /etc/systemd/system/agritech-*.timer

# Reload systemd
sudo systemctl daemon-reload
```
