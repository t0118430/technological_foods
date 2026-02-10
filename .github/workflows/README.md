# 🚀 AgriTech CI/CD Pipeline

## Overview

Complete CI/CD pipeline for the AgriTech Hydroponics SaaS Platform with automated testing, deployment, and monitoring.

## Workflows

### 1. **test-hello-world.yml** - Pipeline Verification
- **Purpose**: Quick test to verify GitHub Actions is working
- **Triggers**: Push to `feature/ci-cd-pipeline` or `master`
- **What it does**:
  - Prints environment info
  - Validates basic GitHub Actions functionality
  - Shows project structure
  - Checks Python and Docker availability

### 2. **test-backend.yml** - Comprehensive Testing
- **Purpose**: Full backend test suite with quality checks
- **Triggers**: Push to feature branches or `master`, PRs affecting backend
- **Jobs**:
  - **Lint & Validate**: JSON configs, Python syntax, OpenAPI spec
  - **Unit Tests**: All pytest tests with coverage reporting
  - **Integration Tests**: Tests with live InfluxDB service
  - **Docker Build**: Validates docker-compose configuration
  - **Security Scan**: Checks for vulnerabilities (safety, bandit)
  - **Test Summary**: Overall results

### 3. **deploy-server-pi.yml** - Server Deployment
- **Purpose**: Deploy backend to Raspberry Pi server with health checks and rollback
- **Triggers**: Push to `master` affecting `backend/**`, manual dispatch
- **What it deploys**: Backend API, Docker services, configs, database

### 4. **deploy-arduino-ota.yml** - Arduino OTA Deployment
- **Purpose**: Deploy firmware to Arduino R4 WiFi over WiFi (no USB needed!)
- **Triggers**: Push to `master` affecting `arduino/**`, manual dispatch
- **What it deploys**: Compiled firmware binary to IoT device
- **Jobs**:
  - **Test**: Run all tests before deployment
  - **Deploy**:
    - Create backup
    - Deploy code via rsync
    - Restart services (Docker + systemd)
    - Health check
    - Rollback on failure
    - Send notifications

## GitHub Secrets Required

Set these in your repository settings (Settings → Secrets and variables → Actions):

### Raspberry Pi Server Access
- `PI_SSH_KEY` - SSH private key for Pi access
- `PI_HOST` - Raspberry Pi hostname or IP (e.g., `192.168.1.10`)
- `PI_USER` - SSH username (e.g., `pi`)
- `PI_PROJECT_PATH` - Project path on Pi (e.g., `/home/pi/technological_foods`)

### Arduino IoT Device Access
- `ARDUINO_IP` - Arduino IP address (e.g., `192.168.1.100`)
- `ARDUINO_OTA_PASSWORD` - OTA password (optional but recommended)

### Notifications
- `NTFY_TOPIC_URL` - ntfy.sh topic URL (e.g., `https://ntfy.sh/techfoods`)

## Deployment Flows

### Server Deployment (Pi)
```
Backend code push to master
    ↓
Run Tests (all must pass)
    ↓
Create Backup on Pi
    ↓
Deploy Code via rsync
    ↓
Restart Services (Docker + systemd)
    ↓
Health Check
    ↓
✅ Success → Notification
❌ Failure → Rollback + notify
```

### Arduino Deployment (OTA)
```
Arduino code push to master
    ↓
Build Firmware (.bin)
    ↓
Upload Artifact
    ↓
Deploy via OTA (WiFi)
    ↓
Arduino Reboots
    ↓
Verify New Version
    ↓
✅ Success → Create Release
❌ Failure → Notify (manual USB flash)
```

**Note**: These run **independently** - changing backend doesn't redeploy Arduino and vice versa!

## Local Testing

### Test GitHub Actions Locally (using act)

```bash
# Install act (GitHub Actions local runner)
# Windows: choco install act-cli
# macOS: brew install act
# Linux: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run hello-world workflow
act -W .github/workflows/test-hello-world.yml

# Run backend tests
act -W .github/workflows/test-backend.yml

# Run specific job
act -j unit-tests
```

### Manual Deployment

```bash
# SSH to Raspberry Pi
ssh pi@<pi-ip>

# Navigate to project
cd /path/to/technological_foods

# Pull latest code
git pull origin master

# Run deployment manually
./deploy/backup.sh pre-manual-deploy
sudo systemctl restart agritech-api.service
cd backend && docker-compose up -d
./deploy/health-check.sh
```

## Health Checks

### Basic Health Check
```bash
./deploy/health-check.sh
```
Checks:
- Docker services (InfluxDB, Grafana, Node-RED)
- API endpoint availability
- Disk space usage

### SaaS Platform Health Check
```bash
./deploy/health-check-saas.sh
```
Checks:
- All basic checks
- SaaS business endpoints
- Memory usage
- Database status
- Resource usage

## Rollback Procedure

### Automatic Rollback
If health check fails after deployment, the pipeline automatically:
1. Restores from backup
2. Restarts services
3. Sends failure notification

### Manual Rollback
```bash
ssh pi@<pi-ip>
cd /path/to/technological_foods
./deploy/restore.sh pre-deploy
sudo systemctl restart agritech-api.service
cd backend && docker-compose restart
```

## Monitoring

### GitHub Actions Dashboard
- View workflow runs: Repository → Actions
- Check logs for failed jobs
- Re-run failed workflows

### Real-time Notifications
All deployments send notifications via ntfy:
- ✅ Success: Default priority
- ❌ Failure: High priority with alert

Subscribe to notifications:
```bash
# Mobile app or browser
https://ntfy.sh/techfoods
```

## CI/CD Best Practices

### Branch Strategy
- `master` - Production, deploys automatically
- `feature/*` - Feature branches, runs tests only
- `hotfix/*` - Urgent fixes, runs tests then deploy

### Pre-commit Checks
Run locally before pushing:
```bash
# Run all tests
cd backend/api
pytest test_*.py -v

# Validate configs
python -m json.tool backend/api/rules_config.json
python -m json.tool backend/config/base_hydroponics.json

# Check Python syntax
python -m py_compile backend/api/*.py
```

### Deployment Schedule
- **Push to master**: Immediate deployment (automated)
- **Off-hours**: Manual dispatch preferred for major changes
- **Backup verification**: Weekly (automated)

## Troubleshooting

### Pipeline Fails at Test Stage
1. Check test logs in GitHub Actions
2. Run tests locally: `cd backend/api && pytest -v`
3. Fix issues and push again

### Deployment Fails
1. Check deployment logs
2. SSH to Pi and check service status:
   ```bash
   systemctl status agritech-api.service
   docker-compose ps
   ```
3. Check health-check.sh output
4. Review backup files in `/tmp/agritech-backups/`

### Health Check Fails
1. Check individual service status
2. Review API logs: `journalctl -u agritech-api.service -f`
3. Check Docker logs: `docker-compose logs -f`
4. Verify network connectivity

### Rollback Issues
1. List available backups: `ls -lh /tmp/agritech-backups/`
2. Restore specific backup: `./deploy/restore.sh <backup-name>`
3. Verify services: `./deploy/health-check.sh`

## Performance Metrics

### Build Times (approximate)
- Hello World Test: ~30 seconds
- Backend Tests: ~3-5 minutes
- Full Deployment: ~5-8 minutes

### Success Criteria
- All tests pass: ✅
- Coverage >80%: ✅
- Security scan clean: ✅
- Health check passes: ✅

## Future Enhancements

### Planned
- [ ] Staging environment deployment
- [ ] Blue-green deployment strategy
- [ ] Automated database migrations
- [ ] Performance benchmarking
- [ ] Load testing

### Consideration
- [ ] Multi-region deployment
- [ ] Kubernetes orchestration
- [ ] Infrastructure as Code (Terraform)
- [ ] Automated scaling

## Links

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [InfluxDB Documentation](https://docs.influxdata.com/)

---

**Status**: ✅ Production Ready
**Last Updated**: 2026-02-08
**Maintained by**: AgriTech DevOps Team
