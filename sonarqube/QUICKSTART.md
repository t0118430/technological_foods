# SonarQube on Raspberry Pi - Quick Start Guide

**Get SonarQube running in 15 minutes!**

---

## ⚡ Prerequisites Check

```bash
# 1. Verify you have Raspberry Pi OS 64-bit
uname -m
# Should output: aarch64

# 2. Check Docker is installed
docker --version
docker-compose --version

# 3. If not installed, install Docker:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in
```

---

## 🚀 Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/your-org/technological-foods.git
cd technological-foods/sonarqube

# 2. Run installer
sudo ./scripts/install.sh
# Follow prompts (will ask for database password)

# 3. Wait for services to start (~2-3 minutes)
```

---

## 🎯 First Login (2 minutes)

1. **Open browser**: `http://<your-pi-ip>:9000`

   ```bash
   # Find your Pi's IP
   hostname -I
   ```

2. **Login**:
   - Username: `admin`
   - Password: `admin`

3. **Change password immediately** (security requirement)

4. **Generate token**:
   - Click user icon → My Account → Security
   - Generate token named `github-actions`
   - **Copy and save it!** (You'll need it for CI/CD)

---

## 📊 Analyze Your First Project (5 minutes)

### Option A: GitHub Actions (Automated)

```bash
# 1. Add secrets to your GitHub repository
# Go to: Settings → Secrets and variables → Actions → New repository secret

SONAR_TOKEN: <paste-your-token>
SONAR_HOST_URL: http://<your-pi-ip>:9000

# 2. Push code to trigger analysis
git push origin master
# GitHub Actions will automatically run SonarQube analysis

# 3. View results in SonarQube web UI
```

### Option B: Local Analysis (Manual)

```bash
# 1. Install SonarScanner
cd ~
wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip
unzip sonar-scanner-cli-5.0.1.3006-linux.zip
export PATH=$PATH:$HOME/sonar-scanner-5.0.1.3006-linux/bin

# 2. Run analysis
cd /path/to/technological-foods
sonar-scanner \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.login=<your-token>

# 3. View results at http://<your-pi-ip>:9000
```

---

## ✅ Verify Everything Works

```bash
# Check SonarQube is running
sudo systemctl status sonarqube.service

# Check automated backups are scheduled
sudo systemctl status sonarqube-backup.timer

# Check health monitoring is active
sudo systemctl status sonarqube-health-check.timer

# View recent logs
sudo journalctl -u sonarqube.service -n 50

# Check API status
curl http://localhost:9000/api/system/status
```

---

## 🎉 You're Done!

Your SonarQube is now:
- ✅ Running 24/7
- ✅ Backing up daily (2:00 AM)
- ✅ Archiving old data weekly
- ✅ Monitoring health every 15 minutes
- ✅ Ready to analyze code!

---

## 📱 Quick Commands

```bash
# View logs
sudo docker-compose -f /opt/sonarqube/docker-compose.yml logs -f

# Restart SonarQube
sudo systemctl restart sonarqube.service

# Backup now
sudo systemctl start sonarqube-backup.service

# Maintenance menu
sudo /opt/sonarqube/scripts/maintenance.sh

# Check disk usage
df -h /
du -sh /opt/sonarqube/
```

---

## 🐛 Quick Troubleshooting

**Can't access web UI?**
```bash
# Check if port is listening
sudo netstat -tulpn | grep 9000

# Check firewall
sudo ufw status
sudo ufw allow 9000/tcp  # If using ufw
```

**SonarQube stuck on "Starting"?**
```bash
# Check system parameters
sudo sysctl -w vm.max_map_count=524288
sudo systemctl restart sonarqube.service
```

**Out of memory?**
```bash
# Check available memory
free -h

# Reduce memory in /opt/sonarqube/docker-compose.yml
# Change from 512m to 384m
```

---

## 📚 Next Steps

- [ ] Configure quality gates
- [ ] Set up project-specific rules
- [ ] Integrate with IDE (VS Code SonarLint)
- [ ] Review data retention settings
- [ ] Set up email notifications

**Read full documentation**: [README.md](./README.md)

---

**Need help?** Check the [Troubleshooting section](./README.md#troubleshooting) in README.md
