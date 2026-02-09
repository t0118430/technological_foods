# SonarQube Self-Hosted on Raspberry Pi

**Enterprise-grade code quality platform running 24/7 on Raspberry Pi with automated data retention and cold storage.**

![SonarQube](https://img.shields.io/badge/SonarQube-10.3-4E9BCD?logo=sonarqube)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python)
![C++](https://img.shields.io/badge/C++-Arduino-00599C?logo=cplusplus)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## 🎯 Features

✅ **Self-hosted SonarQube Community Edition** - No cloud dependency
✅ **Optimized for Raspberry Pi** - ARM64 architecture support
✅ **Automated backups** - Daily PostgreSQL dumps
✅ **Data retention policies** - 180-day active storage + cold storage
✅ **Smart archival** - Keeps 250 most recent analyses per project
✅ **24/7 operation** - Systemd services with auto-restart
✅ **Health monitoring** - Auto-recovery every 15 minutes
✅ **Zero maintenance** - Fully automated operations

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Retention Strategy](#data-retention-strategy)
- [Backup & Restore](#backup--restore)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              SonarQube Container                    │ │
│  │  - Web UI (Port 9000)                              │ │
│  │  - Analysis Engine                                 │ │
│  │  - Elasticsearch (embedded)                        │ │
│  └────────────────┬───────────────────────────────────┘ │
│                   │                                      │
│  ┌────────────────▼───────────────────────────────────┐ │
│  │         PostgreSQL Container                       │ │
│  │  - SonarQube database                             │ │
│  │  - Analysis data                                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Systemd Services                         │ │
│  │  - Auto-start on boot                             │ │
│  │  - Daily backups (2:00 AM)                        │ │
│  │  - Weekly archival (Sunday 3:00 AM)               │ │
│  │  - Health checks (every 15 min)                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────┐
            │   USB Backup Drive      │
            │  ┌──────────────────┐   │
            │  │ Active Backups   │   │
            │  │ (30 days)        │   │
            │  └──────────────────┘   │
            │  ┌──────────────────┐   │
            │  │ Cold Storage     │   │
            │  │ (180+ days)      │   │
            │  └──────────────────┘   │
            └─────────────────────────┘
```

---

## 🔧 Prerequisites

### Hardware Requirements

- **Raspberry Pi 4 (4GB RAM minimum, 8GB recommended)**
- **32GB+ SD card** for OS and Docker
- **USB storage** (500GB+) for backups and cold storage
- **Stable internet** for initial setup and updates

### Software Requirements

```bash
# Operating System
Raspberry Pi OS (64-bit) or Ubuntu Server 22.04 ARM64

# Required packages
- Docker (20.10+)
- Docker Compose (2.x)
- Git
```

### Network Requirements

- Port 9000 accessible (for SonarQube web interface)
- Outbound internet access (for analysis and plugins)

---

## 🚀 Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/technological-foods.git
cd technological-foods/sonarqube

# Run installation script
sudo ./scripts/install.sh
```

The installer will:
1. ✅ Configure system parameters (vm.max_map_count, etc.)
2. ✅ Set up Docker Compose
3. ✅ Install systemd services
4. ✅ Start SonarQube
5. ✅ Enable automated backups and health checks

**Installation time: ~10 minutes** (first Docker image pull)

### Manual Installation

<details>
<summary>Click to expand manual steps</summary>

```bash
# 1. Configure system parameters
sudo sysctl -w vm.max_map_count=524288
sudo sysctl -w fs.file-max=131072
echo "vm.max_map_count=524288" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=131072" | sudo tee -a /etc/sysctl.conf

# 2. Create installation directory
sudo mkdir -p /opt/sonarqube
sudo cp docker-compose.yml /opt/sonarqube/
sudo cp .env.example /opt/sonarqube/.env

# 3. Configure environment
cd /opt/sonarqube
sudo nano .env  # Update SONAR_DB_PASSWORD

# 4. Copy scripts
sudo mkdir -p /opt/sonarqube/scripts
sudo cp scripts/*.sh /opt/sonarqube/scripts/
sudo chmod +x /opt/sonarqube/scripts/*.sh

# 5. Install systemd services
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 6. Start services
sudo systemctl enable --now sonarqube.service
sudo systemctl enable --now sonarqube-backup.timer
sudo systemctl enable --now sonarqube-cold-storage.timer
sudo systemctl enable --now sonarqube-health-check.timer
```

</details>

---

## ⚙️ Configuration

### Initial Setup

1. **Access SonarQube Web UI**
   ```
   http://<raspberry-pi-ip>:9000
   ```

2. **Login with default credentials**
   - Username: `admin`
   - Password: `admin`
   - ⚠️ **Change password immediately!**

3. **Generate authentication token**
   ```
   User Menu → My Account → Security → Generate Token
   ```

4. **Add to GitHub Secrets** (for CI/CD)
   ```
   SONAR_TOKEN: <your-token>
   SONAR_HOST_URL: http://<raspberry-pi-ip>:9000
   ```

### Environment Variables

Edit `/opt/sonarqube/.env`:

```bash
# Database password (REQUIRED)
SONAR_DB_PASSWORD=your_secure_password

# Backup retention (optional, defaults shown)
BACKUP_RETENTION_DAYS=30
COLD_STORAGE_DAYS=180
MAX_ACTIVE_ANALYSES=250

# Storage paths
COLD_STORAGE_PATH=/mnt/usb-backup/sonarqube-cold-storage
BACKUP_PATH=/opt/sonarqube/backups
```

### Performance Tuning

For **Raspberry Pi 4 with 4GB RAM**:
```yaml
# docker-compose.yml (already optimized)
SONAR_WEB_JAVAOPTS: -Xmx512m -Xms128m
SONAR_CE_JAVAOPTS: -Xmx512m -Xms128m
SONAR_SEARCH_JAVAOPTS: -Xmx512m -Xms512m
```

For **Raspberry Pi 4 with 8GB RAM**:
```yaml
SONAR_WEB_JAVAOPTS: -Xmx1024m -Xms256m
SONAR_CE_JAVAOPTS: -Xmx1024m -Xms256m
SONAR_SEARCH_JAVAOPTS: -Xmx1024m -Xms1024m
```

---

## 💻 Usage

### Analyze Your Project

#### Method 1: GitHub Actions (Automated)

```yaml
# .github/workflows/sonarqube-analysis.yml
# (Already created - just push to trigger)
```

#### Method 2: Local Analysis

```bash
# Install SonarScanner
wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip
unzip sonar-scanner-cli-5.0.1.3006-linux.zip
export PATH=$PATH:$PWD/sonar-scanner-5.0.1.3006-linux/bin

# Run analysis
cd /path/to/technological-foods
sonar-scanner \
  -Dsonar.host.url=http://<raspberry-pi-ip>:9000 \
  -Dsonar.login=<your-token>
```

### View Results

1. Open SonarQube Web UI
2. Navigate to **Projects → technological-foods**
3. Review:
   - 🐛 Bugs
   - 🔒 Security vulnerabilities
   - 💩 Code smells
   - 📊 Coverage
   - 🔄 Duplications

---

## 🗄️ Data Retention Strategy

### Active Storage (0-180 days)

- **All analysis data** immediately available
- **Quick access** for recent reports
- **Full history** for trend analysis
- **Maximum 250 analyses per project**

### Cold Storage (180+ days)

- **Archived to compressed files** (`.sql.gz`)
- **Stored on USB backup drive**
- **Restorable on demand**
- **Keeps all historical data**

### Automatic Cleanup

```bash
# Daily (2:00 AM)
- Database backup created
- Old backups deleted (30+ days)

# Weekly (Sunday 3:00 AM)
- Data older than 180 days archived
- Excess analyses moved to cold storage
- Database vacuumed and optimized
```

---

## 💾 Backup & Restore

### Manual Backup

```bash
# Backup database now
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  run --rm sonarqube-backup /scripts/backup-db.sh

# View backups
ls -lh /opt/sonarqube/backups/
```

### Restore from Backup

```bash
# List available backups
ls -lh /opt/sonarqube/backups/

# Restore specific backup
sudo /opt/sonarqube/scripts/restore-backup.sh \
  /opt/sonarqube/backups/sonarqube_backup_20260209_020001.sql.gz

# Restart SonarQube
sudo systemctl restart sonarqube.service
```

### Cold Storage Operations

```bash
# Run archival now
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  run --rm sonarqube-backup /scripts/cold-storage-archival.sh

# View cold storage
ls -lh /mnt/usb-backup/sonarqube-cold-storage/

# Restore from cold storage
sudo /opt/sonarqube/scripts/restore-from-cold-storage.sh \
  /mnt/usb-backup/sonarqube-cold-storage/snapshots_archive_20260101.sql.gz
```

---

## 🔧 Maintenance

### Interactive Maintenance Menu

```bash
sudo /opt/sonarqube/scripts/maintenance.sh
```

**Available operations:**
1. Check system status
2. View logs
3. Backup database now
4. Run cold storage archival
5. List backups
6. Database statistics
7. Disk usage report
8. Update SonarQube

### Service Management

```bash
# Check status
sudo systemctl status sonarqube.service

# Restart
sudo systemctl restart sonarqube.service

# View logs
sudo journalctl -u sonarqube.service -f

# Check health
curl -s http://localhost:9000/api/system/status | jq
```

### Timer Status

```bash
# View all timers
sudo systemctl list-timers sonarqube-*

# Check next backup time
sudo systemctl status sonarqube-backup.timer

# Trigger backup manually
sudo systemctl start sonarqube-backup.service
```

---

## 🐛 Troubleshooting

### SonarQube won't start

```bash
# Check system parameters
sysctl vm.max_map_count  # Should be 524288
ulimit -n                # Should be 131072

# Check Docker logs
sudo docker-compose -f /opt/sonarqube/docker-compose.yml logs sonarqube

# Check disk space
df -h /
```

### Database connection issues

```bash
# Check PostgreSQL status
sudo docker-compose -f /opt/sonarqube/docker-compose.yml ps sonarqube-db

# Check database logs
sudo docker-compose -f /opt/sonarqube/docker-compose.yml logs sonarqube-db

# Restart database
sudo docker-compose -f /opt/sonarqube/docker-compose.yml restart sonarqube-db
```

### Out of memory errors

```bash
# Check memory usage
free -h
docker stats

# Reduce memory limits in docker-compose.yml
# For 4GB Pi, use:
SONAR_WEB_JAVAOPTS: -Xmx384m
SONAR_CE_JAVAOPTS: -Xmx384m
SONAR_SEARCH_JAVAOPTS: -Xmx384m
```

### Backup fails

```bash
# Check backup directory permissions
ls -la /opt/sonarqube/backups/

# Check USB mount
df -h /mnt/usb-backup

# Run backup manually with verbose output
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  run --rm sonarqube-backup /scripts/backup-db.sh
```

---

## 📚 Advanced Topics

### Multi-Project Setup

```bash
# Create separate quality profiles per project
SonarQube UI → Quality Profiles → Create

# Set project-specific quality gates
SonarQube UI → Quality Gates → Create
```

### Custom Rules

```bash
# Install additional plugins
SonarQube UI → Administration → Marketplace

# Recommended for Python:
- SonarPython (included)
- SonarLint

# Recommended for C/C++:
- SonarCFamily (community edition limitations)
```

### Integration with IDEs

**VS Code:**
```bash
# Install SonarLint extension
code --install-extension SonarSource.sonarlint-vscode

# Configure connection
{
  "sonarlint.connectedMode.connections.sonarqube": [
    {
      "serverUrl": "http://<raspberry-pi-ip>:9000",
      "token": "<your-token>"
    }
  ]
}
```

### Performance Optimization

```bash
# Reduce analysis frequency
# Edit .github/workflows/sonarqube-analysis.yml
# Change from "on: push" to "on: pull_request"

# Disable unnecessary plugins
SonarQube UI → Administration → Marketplace → Uninstall unused

# Enable branch analysis cache
sonar-project.properties:
sonar.scm.provider=git
```

---

## 📊 Monitoring

### Key Metrics

```bash
# Database size
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  exec sonarqube-db psql -U sonar -d sonarqube -c \
  "SELECT pg_size_pretty(pg_database_size('sonarqube'));"

# Number of snapshots
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  exec sonarqube-db psql -U sonar -d sonarqube -c \
  "SELECT COUNT(*) FROM snapshots;"

# Oldest snapshot age
sudo docker-compose -f /opt/sonarqube/docker-compose.yml \
  exec sonarqube-db psql -U sonar -d sonarqube -c \
  "SELECT EXTRACT(DAY FROM (NOW() - MIN(created_at))) || ' days' FROM snapshots;"
```

### Health Endpoints

```bash
# System status
curl http://localhost:9000/api/system/status

# Database status
curl http://localhost:9000/api/system/health

# Metrics
curl http://localhost:9000/api/monitoring/metrics
```

---

## 🔗 Resources

- [SonarQube Documentation](https://docs.sonarqube.org/)
- [SonarQube Community Forum](https://community.sonarsource.com/)
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [Project Repository](https://github.com/your-org/technological-foods)

---

## 📝 License

This configuration is part of the Technological Foods AgriTech Platform.

---

## 🤝 Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [SonarQube logs](#service-management)
3. Open an issue on GitHub
4. Contact the DevOps team

---

**Built with ❤️ for sustainable agriculture technology**
