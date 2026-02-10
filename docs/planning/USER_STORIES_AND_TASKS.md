# 📝 AgriTech Hydroponics - User Stories & Tasks

**Project**: AgriTech SaaS Platform
**Version**: 2.0.0
**Last Updated**: 2026-02-09

---

## 📊 Project Overview

### Epics

1. **🔒 Security & Deployment** - Fix critical issues before production
2. **🌱 Farmer Experience** - Core monitoring and alerting
3. **💼 Business Platform** - SaaS features and revenue tracking
4. **🌍 Multi-Location Support** - Porto → Lisbon → Algarve expansion
5. **🤖 Automation & AI** - Smart rules and predictive maintenance
6. **📱 Mobile Experience** - ntfy app integration
7. **🔧 DevOps & Infrastructure** - CI/CD and monitoring

---

## 🚨 IMMEDIATE ACTIONS (Before Merge to Dev)

### Priority: 🔴 CRITICAL - Must complete before deployment

| # | Action | Assignee | Estimate | Status |
|---|--------|----------|----------|--------|
| 1 | Fix hardcoded passwords in `.env.example` | DevOps | 5 min | ⏸️ TODO |
| 2 | Fix hardcoded API key in `config.h.example` | DevOps | 5 min | ⏸️ TODO |
| 3 | Add `.claude/settings.local.json` to `.gitignore` | DevOps | 2 min | ⏸️ TODO |
| 4 | Create new root `README.md` | Tech Writer | 30 min | ⏸️ TODO |
| 5 | Generate strong production API keys | DevOps | 10 min | ⏸️ TODO |
| 6 | Review and test all API endpoints | QA | 2 hours | ⏸️ TODO |
| 7 | Run full test suite | QA | 30 min | ⏸️ TODO |
| 8 | Code review with team | Team Lead | 1 hour | ⏸️ TODO |
| 9 | Merge `feature/dashboard` → `dev` | DevOps | 15 min | ⏸️ TODO |
| 10 | Tag release `v2.0.0-beta` | DevOps | 5 min | ⏸️ TODO |

**Total Effort**: ~5 hours
**Blocking**: All other work depends on this

---

## 📅 POST-MERGE ACTIONS (Week 1-2)

### Priority: 🟡 HIGH - Deploy to dev environment

| # | Action | Assignee | Estimate | Dependencies |
|---|--------|----------|----------|--------------|
| 11 | Deploy to dev Raspberry Pi | DevOps | 1 hour | #9 |
| 12 | Configure dev environment variables | DevOps | 30 min | #11 |
| 13 | Set up InfluxDB on dev | DevOps | 30 min | #11 |
| 14 | Configure ntfy topics | DevOps | 15 min | #12 |
| 15 | Test Arduino → Server connection | QA | 30 min | #12 |
| 16 | Create Grafana dashboards | DevOps | 2 hours | #13 |
| 17 | Set up automated backups | DevOps | 1 hour | #11 |
| 18 | Configure firewall rules | Security | 1 hour | #11 |
| 19 | Set up monitoring/alerts | DevOps | 1 hour | #16 |
| 20 | Documentation review | Tech Writer | 2 hours | - |

**Total Effort**: ~11 hours

---

## 👥 USER STORIES BY ROLE

### 🌱 As a Farmer (Greenhouse Operator)

#### Epic: Farmer Experience

**US-001: Monitor Greenhouse Conditions**
```
As a farmer,
I want to see real-time temperature, humidity, and pH readings,
So that I know my crops are growing in optimal conditions.

Acceptance Criteria:
- ✅ Dashboard shows latest readings (< 5 seconds old)
- ✅ Visual indicators (green/yellow/red) for status
- ✅ Historical graphs show 24-hour trends
- ✅ Mobile-friendly responsive design

Priority: 🔴 CRITICAL
Effort: 3 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-002: Receive Critical Alerts**
```
As a farmer,
I want to receive push notifications when conditions are dangerous,
So that I can take action before crops are damaged.

Acceptance Criteria:
- ✅ ntfy push notification arrives within 10 seconds
- ✅ Alert includes: sensor value, threshold, location
- ✅ Different sounds for critical vs. warning alerts
- ✅ Can acknowledge alert to stop escalation

Priority: 🔴 CRITICAL
Effort: 5 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-003: Configure Alert Thresholds**
```
As a farmer,
I want to customize alert thresholds for my specific crops,
So that I only get notified about real issues.

Acceptance Criteria:
- ✅ Can load pre-configured crop profiles (basil, lettuce, etc.)
- ✅ Can manually adjust temperature/humidity/pH ranges
- ✅ Changes take effect immediately
- ✅ Can test alerts before saving

Priority: 🟡 HIGH
Effort: 8 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-004: Track Crop Growth Stages**
```
As a farmer,
I want the system to adjust settings as my crop matures,
So that environmental conditions match each growth stage.

Acceptance Criteria:
- ✅ Can set current growth stage (germination, vegetative, flowering, etc.)
- ✅ System automatically adjusts temperature/humidity/light targets
- ✅ Dashboard shows expected duration for each stage
- ✅ Receives notification when ready to transition stages

Priority: 🟢 MEDIUM
Effort: 5 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-005: View Historical Data**
```
As a farmer,
I want to see graphs of temperature/humidity over the past week,
So that I can identify patterns and optimize growing conditions.

Acceptance Criteria:
- ✅ Can select date range (24 hours, 7 days, 30 days)
- ✅ Can overlay multiple sensors on one graph
- ✅ Can export data as CSV for analysis
- ✅ Can compare current crop to previous harvests

Priority: 🟢 MEDIUM
Effort: 8 story points
Status: ⏸️ TODO (Grafana integration needed)
```

---

### 💼 As a Business Owner

#### Epic: Business Platform

**US-006: Track Revenue Metrics**
```
As a business owner,
I want to see MRR, ARR, and customer lifetime value,
So that I can make data-driven business decisions.

Acceptance Criteria:
- ✅ Dashboard shows current MRR, ARR, LTV
- ✅ Growth charts show month-over-month trends
- ✅ Can filter by client tier (Free, Pro, Enterprise)
- ✅ Can export reports as PDF

Priority: 🟡 HIGH
Effort: 8 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-007: Manage Clients and Tiers**
```
As a business owner,
I want to upgrade/downgrade client subscriptions,
So that I can adjust pricing based on usage.

Acceptance Criteria:
- ✅ Can view all clients with current tier
- ✅ Can upgrade client to higher tier (Pro, Enterprise)
- ✅ Can downgrade client (with confirmation)
- ✅ System enforces tier limits (sensors, locations, API calls)

Priority: 🟡 HIGH
Effort: 13 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-008: Generate Lead List for Porto**
```
As a business owner,
I want to find potential customers in Porto,
So that I can grow my customer base legally and ethically.

Acceptance Criteria:
- ✅ Can search Google Business for "vertical farms Porto"
- ✅ Can import leads from business directories
- ✅ Email addresses are hashed (SHA-256) for privacy
- ✅ GDPR-compliant (explicit consent required)
- ❌ NO illegal social media scraping

Priority: 🟡 HIGH
Effort: 13 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-009: Monitor System Health**
```
As a business owner,
I want to see which sensors are failing or degrading,
So that I can schedule preventive maintenance.

Acceptance Criteria:
- ✅ Dashboard shows sensor health scores (0-100%)
- ✅ Color-coded status: healthy, degraded, failing
- ✅ Drift detection identifies sensor discrepancies
- ✅ Predictive alerts warn 2-4 weeks before failure

Priority: 🟡 HIGH
Effort: 13 story points
Status: ✅ DONE (in feature/dashboard)
```

---

**US-010: Analyze Customer Churn**
```
As a business owner,
I want to see which customers are at risk of canceling,
So that I can reach out proactively.

Acceptance Criteria:
- ✅ Dashboard shows churn rate (%)
- ✅ Identifies clients with declining usage
- ✅ Shows clients who haven't logged in 30+ days
- ✅ Can export at-risk client list

Priority: 🟢 MEDIUM
Effort: 8 story points
Status: ⏸️ TODO (future enhancement)
```

---

### 🔧 As a System Administrator

#### Epic: DevOps & Infrastructure

**US-011: Deploy System to Raspberry Pi**
```
As a system administrator,
I want an automated deployment script,
So that I can deploy updates without manual errors.

Acceptance Criteria:
- ✅ Can deploy with single command
- ✅ Automated backup before deployment
- ✅ Health checks after deployment
- ✅ Automatic rollback on failure

Priority: 🔴 CRITICAL
Effort: 13 story points
Status: ✅ DONE (in feature/dashboard - CI/CD)
```

---

**US-012: Monitor Server Resources**
```
As a system administrator,
I want to receive alerts when server resources are low,
So that I can prevent system crashes.

Acceptance Criteria:
- ✅ Alerts when CPU > 80% for 5 minutes
- ✅ Alerts when RAM > 90%
- ✅ Alerts when disk > 85% full
- ✅ Alerts when temperature > 75°C

Priority: 🟡 HIGH
Effort: 5 story points
Status: ⏸️ TODO (monitoring service needed)
```

---

**US-013: Backup and Restore Data**
```
As a system administrator,
I want automated daily backups,
So that I can recover from hardware failures.

Acceptance Criteria:
- ✅ Automated daily backup to USB drive
- ✅ Weekly backup to cloud (B2/S3)
- ✅ Can restore backup with single command
- ✅ Backup verification (check integrity)

Priority: 🔴 CRITICAL
Effort: 8 story points
Status: ✅ DONE (scripts in feature/dashboard)
```

---

**US-014: Update Arduino Firmware Remotely**
```
As a system administrator,
I want to update Arduino firmware over-the-air,
So that I don't need to physically visit each location.

Acceptance Criteria:
- ✅ Can upload new firmware from web interface
- ✅ Arduino downloads and installs update automatically
- ✅ Rollback to previous version if update fails
- ✅ Can schedule updates during off-hours

Priority: 🟡 HIGH
Effort: 13 story points
Status: ✅ DONE (OTA tools in feature/dashboard)
```

---

**US-015: View System Logs**
```
As a system administrator,
I want to search and filter system logs,
So that I can troubleshoot issues quickly.

Acceptance Criteria:
- ✅ Can view logs from web interface
- ✅ Can filter by severity (error, warning, info)
- ✅ Can search by keyword or timestamp
- ✅ Logs retained for 90 days

Priority: 🟢 MEDIUM
Effort: 8 story points
Status: ⏸️ TODO (log viewer UI needed)
```

---

### 📱 As a Mobile User

#### Epic: Mobile Experience

**US-016: Receive Push Notifications**
```
As a mobile user,
I want to receive push notifications on my phone,
So that I'm alerted even when away from my computer.

Acceptance Criteria:
- ✅ ntfy app installed on iOS/Android
- ✅ Subscribed to correct topic
- ✅ Notifications arrive within 10 seconds
- ✅ Different notification sounds for priorities

Priority: 🔴 CRITICAL
Effort: 5 story points
Status: ✅ DONE (ntfy integration in feature/dashboard)
```

---

**US-017: View Dashboard on Phone**
```
As a mobile user,
I want to view the dashboard on my phone,
So that I can check conditions while traveling.

Acceptance Criteria:
- ✅ Dashboard is mobile-responsive
- ✅ All features work on touchscreen
- ✅ Graphs are readable on small screens
- ✅ Can acknowledge alerts from phone

Priority: 🟡 HIGH
Effort: 8 story points
Status: ⏸️ TODO (mobile UI optimization needed)
```

---

**US-018: Control AC from Phone**
```
As a mobile user,
I want to turn AC on/off from my phone,
So that I can respond to alerts remotely.

Acceptance Criteria:
- ✅ Can toggle AC power from mobile dashboard
- ✅ Can adjust target temperature
- ✅ Can change mode (cool/heat/fan)
- ✅ Receives confirmation notification

Priority: 🟢 MEDIUM
Effort: 5 story points
Status: ⏸️ TODO (mobile AC controls needed)
```

---

### 🌍 As a Multi-Location Manager

#### Epic: Multi-Location Support

**US-019: Monitor Multiple Greenhouses**
```
As a multi-location manager,
I want to see all my greenhouses on one dashboard,
So that I can monitor the entire operation at a glance.

Acceptance Criteria:
- ✅ Dashboard shows all locations (Porto, Lisbon, Algarve)
- ✅ Each location shows current status (healthy/warning/critical)
- ✅ Can click location to see detailed view
- ✅ Can compare metrics across locations

Priority: 🟡 HIGH
Effort: 13 story points
Status: ⏸️ TODO (multi-location dashboard needed)
```

---

**US-020: Set Up VPN Between Locations**
```
As a multi-location manager,
I want secure encrypted connections between sites,
So that data stays private and accessible remotely.

Acceptance Criteria:
- ✅ WireGuard VPN configured on central server (Porto)
- ✅ Remote sites (Lisbon, Algarve) connect automatically
- ✅ Can access remote sensors via VPN (10.200.0.x)
- ✅ VPN reconnects automatically if disconnected

Priority: 🟡 HIGH
Effort: 13 story points
Status: ⏸️ TODO (VPN setup needed)
```

---

**US-021: Replicate Data to Central Server**
```
As a multi-location manager,
I want all sensor data centralized in Porto,
So that I can analyze trends across all locations.

Acceptance Criteria:
- ✅ Remote sites sync data to Porto every 60 seconds
- ✅ Local backup if VPN connection lost
- ✅ Automatic catch-up when connection restored
- ✅ No data loss during network outages

Priority: 🟡 HIGH
Effort: 13 story points
Status: ⏸️ TODO (data sync service needed)
```

---

## 📋 TASK BREAKDOWN BY EPIC

### Epic 1: 🔒 Security & Deployment (Before Merge)

#### Sprint 0 (Before Production)

**TASK-001: Fix Hardcoded Credentials**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 5 minutes
- **Description**: Replace hardcoded passwords in `.env.example` and `config.h.example`
- **Steps**:
  1. Edit `backend/.env.example`
  2. Replace `agritech2026` with `your-secure-password-here`
  3. Edit `arduino/dual_sensor_system/config.h.example`
  4. Replace `agritech-secret-key-2026` with `your-secret-api-key-here`
  5. Commit changes
- **Acceptance**: No actual credentials in example files
- **Blocked By**: None

---

**TASK-002: Generate Production API Keys**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 10 minutes
- **Description**: Generate strong, unique API keys for production
- **Steps**:
  1. Generate 32-character random key: `openssl rand -base64 32`
  2. Add to production `.env` file (NOT example)
  3. Configure Arduino with matching key
  4. Test authentication
- **Acceptance**: API key is 32+ characters, random
- **Blocked By**: TASK-001

---

**TASK-003: Add .gitignore Rules**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 2 minutes
- **Description**: Prevent local config from being committed
- **Steps**:
  1. Add `.claude/settings.local.json` to `.gitignore`
  2. Add `backend/.env` (if not already)
  3. Add `arduino/*/config.h` (if not already)
  4. Commit `.gitignore` changes
- **Acceptance**: Local config files not tracked by git
- **Blocked By**: None

---

**TASK-004: Create Root README.md**
- **Priority**: 🟡 HIGH
- **Assignee**: Tech Writer
- **Effort**: 30 minutes
- **Description**: Write comprehensive root README with quick start
- **Steps**:
  1. Project overview (what it does)
  2. Features list
  3. Quick start guide (5 steps)
  4. Link to detailed documentation
  5. Screenshots/diagrams
- **Acceptance**: README clearly explains project and how to start
- **Blocked By**: None

---

**TASK-005: Run Full Test Suite**
- **Priority**: 🔴 CRITICAL
- **Assignee**: QA
- **Effort**: 30 minutes
- **Description**: Verify all tests pass before merge
- **Steps**:
  1. `cd backend`
  2. `python3 -m pytest api/test_*.py -v`
  3. Verify 25/25 tests pass
  4. Check coverage: `pytest --cov=api`
  5. Document any failures
- **Acceptance**: All tests pass, coverage > 80%
- **Blocked By**: None

---

**TASK-006: Code Review**
- **Priority**: 🔴 CRITICAL
- **Assignee**: Team Lead
- **Effort**: 1 hour
- **Description**: Review all changes before merge
- **Steps**:
  1. Review `CODE_REVIEW_feature-dashboard-to-dev.md`
  2. Check for security issues
  3. Verify coding standards
  4. Test critical paths manually
  5. Approve or request changes
- **Acceptance**: No blocking issues found
- **Blocked By**: TASK-001, TASK-005

---

**TASK-007: Merge to Dev Branch**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 15 minutes
- **Description**: Merge feature/dashboard into dev
- **Steps**:
  1. `git checkout dev`
  2. `git pull origin dev`
  3. `git merge feature/dashboard`
  4. Resolve conflicts (if any)
  5. `git push origin dev`
- **Acceptance**: Merge successful, no conflicts
- **Blocked By**: TASK-001, TASK-006

---

**TASK-008: Tag Release**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 5 minutes
- **Description**: Create git tag for this release
- **Steps**:
  1. `git tag -a v2.0.0-beta -m "SaaS platform beta release"`
  2. `git push origin v2.0.0-beta`
  3. Create GitHub release notes
  4. Attach change log
- **Acceptance**: Tag created and pushed to remote
- **Blocked By**: TASK-007

---

### Epic 2: 🌱 Farmer Experience (Week 1-2)

**TASK-009: Deploy to Dev Raspberry Pi**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 1 hour
- **Description**: Deploy merged code to dev environment
- **Steps**:
  1. SSH to dev Pi: `ssh pi@dev-pi-ip`
  2. `cd /opt/technological_foods`
  3. `git pull origin dev`
  4. `pip3 install -r backend/requirements.txt`
  5. Copy `.env.example` to `.env`, configure
  6. `sudo systemctl restart agritech-api`
- **Acceptance**: API running, health check passes
- **Blocked By**: TASK-007

---

**TASK-010: Configure InfluxDB**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 30 minutes
- **Description**: Set up time-series database
- **Steps**:
  1. `sudo systemctl start influxdb`
  2. Create org: `agritech`
  3. Create bucket: `hydroponics`
  4. Generate token, add to `.env`
  5. Test write: `curl -X POST ...`
- **Acceptance**: Can write and query data
- **Blocked By**: TASK-009

---

**TASK-011: Set Up ntfy Notifications**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 15 minutes
- **Description**: Configure push notification service
- **Steps**:
  1. Choose topic name: `agritech-dev-alerts`
  2. Add to `.env`: `NTFY_TOPIC=agritech-dev-alerts`
  3. Install ntfy app on test phone
  4. Subscribe to topic
  5. Test: `python3 backend/test_real_notification.py`
- **Acceptance**: Test notification received on phone
- **Blocked By**: TASK-009

---

**TASK-012: Create First Rule**
- **Priority**: 🟡 HIGH
- **Assignee**: QA
- **Effort**: 15 minutes
- **Description**: Test rule engine with simple rule
- **Steps**:
  1. POST to `/api/rules` with temperature threshold
  2. Send data above threshold
  3. Verify notification received
  4. Check alert history
  5. Delete test rule
- **Acceptance**: Rule triggers correctly, notification sent
- **Blocked By**: TASK-011

---

**TASK-013: Load Basil Config**
- **Priority**: 🟢 MEDIUM
- **Assignee**: QA
- **Effort**: 10 minutes
- **Description**: Test variety-specific configuration
- **Steps**:
  1. POST to `/api/config/load` with `variety: basil_genovese`
  2. Verify thresholds loaded correctly
  3. Test that rules use new thresholds
  4. Check growth stage set to vegetative
- **Acceptance**: Config loaded, thresholds applied
- **Blocked By**: TASK-012

---

**TASK-014: Test Arduino Connection**
- **Priority**: 🔴 CRITICAL
- **Assignee**: Hardware Tech
- **Effort**: 30 minutes
- **Description**: Verify Arduino sends data to server
- **Steps**:
  1. Flash Arduino with firmware
  2. Configure WiFi in `config.h`
  3. Set API_HOST to dev Pi IP
  4. Monitor serial output
  5. Verify data arrives in InfluxDB
- **Acceptance**: Data sent every 2 seconds, no errors
- **Blocked By**: TASK-010

---

**TASK-015: Create Grafana Dashboard**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 2 hours
- **Description**: Build visualization dashboard
- **Steps**:
  1. Access Grafana: `http://dev-pi-ip:3000`
  2. Add InfluxDB data source
  3. Create panels: temperature, humidity, pH, EC
  4. Add time selector (24h, 7d, 30d)
  5. Add alert indicators
- **Acceptance**: Dashboard shows real-time data
- **Blocked By**: TASK-010

---

### Epic 3: 💼 Business Platform (Week 2-3)

**TASK-016: Create First Client**
- **Priority**: 🟡 HIGH
- **Assignee**: QA
- **Effort**: 15 minutes
- **Description**: Test client management system
- **Steps**:
  1. POST to `/api/clients` with test client data
  2. Assign tier: Pro
  3. Verify tier limits enforced
  4. Test usage tracking
- **Acceptance**: Client created, limits work
- **Blocked By**: TASK-009

---

**TASK-017: Test Business Dashboard**
- **Priority**: 🟡 HIGH
- **Assignee**: QA
- **Effort**: 30 minutes
- **Description**: Verify revenue metrics
- **Steps**:
  1. Access `/api/business/dashboard`
  2. Check MRR calculation
  3. Verify client count
  4. Test sensor health aggregation
  5. Export report
- **Acceptance**: Metrics accurate, export works
- **Blocked By**: TASK-016

---

**TASK-018: Import Porto Leads**
- **Priority**: 🟢 MEDIUM
- **Assignee**: Sales
- **Effort**: 1 hour
- **Description**: Find potential customers in Porto
- **Steps**:
  1. Search Google Maps: "vertical farms Porto"
  2. Search LinkedIn: "hydroponics Porto"
  3. Use `/api/leads/add` to import
  4. Verify emails are hashed
  5. Tag leads: "Porto", "2026-Q1"
- **Acceptance**: 20+ leads imported, GDPR-compliant
- **Blocked By**: TASK-009

---

### Epic 4: 🌍 Multi-Location Support (Week 3-4)

**TASK-019: Set Up WireGuard VPN (Porto)**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 2 hours
- **Description**: Configure VPN server on Porto Pi
- **Steps**:
  1. `sudo apt install wireguard`
  2. Generate server keys: `wg genkey | tee server_private.key | wg pubkey > server_public.key`
  3. Create `/etc/wireguard/wg0.conf`
  4. Configure interface: `10.200.0.1/24`
  5. Open port 51820 on router
  6. Start VPN: `sudo wg-quick up wg0`
- **Acceptance**: VPN server running, port open
- **Blocked By**: None (can do in parallel)

---

**TASK-020: Configure VPN Client (Lisbon)**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 1 hour
- **Description**: Connect Lisbon Pi to Porto VPN
- **Steps**:
  1. Generate client keys on Lisbon Pi
  2. Add peer configuration to Porto server
  3. Configure Lisbon client: `10.200.0.2`
  4. Test connection: `ping 10.200.0.1`
  5. Verify encryption: `sudo wg show`
- **Acceptance**: Can ping Porto from Lisbon via VPN
- **Blocked By**: TASK-019

---

**TASK-021: Test Multi-Location Dashboard**
- **Priority**: 🟢 MEDIUM
- **Assignee**: QA
- **Effort**: 30 minutes
- **Description**: Verify can monitor both locations
- **Steps**:
  1. Access Porto dashboard
  2. Add Lisbon location
  3. Verify both locations visible
  4. Compare sensor readings
  5. Test location-specific alerts
- **Acceptance**: Both locations monitored from single dashboard
- **Blocked By**: TASK-020

---

### Epic 5: 🤖 Automation & AI (Week 4-5)

**TASK-022: Create AC Automation Rule**
- **Priority**: 🟢 MEDIUM
- **Assignee**: Automation Engineer
- **Effort**: 30 minutes
- **Description**: Auto-control AC based on temperature
- **Steps**:
  1. Create rule: temp > 28°C → AC cool to 24°C
  2. Create rule: temp < 18°C → AC heat to 20°C
  3. Test triggering rules
  4. Verify AC responds
  5. Add safety limits (prevent rapid cycling)
- **Acceptance**: AC controlled automatically, no rapid on/off
- **Blocked By**: TASK-012

---

**TASK-023: Implement Drift Detection**
- **Priority**: 🟡 HIGH
- **Assignee**: Data Scientist
- **Effort**: 4 hours
- **Description**: Detect when sensors drift apart
- **Steps**:
  1. Deploy dual sensor Arduino
  2. Collect 24 hours of data from both sensors
  3. Calculate drift metrics
  4. Set drift thresholds (0.5°C warning, 2.0°C critical)
  5. Test drift alerts
- **Acceptance**: Drift detected within 0.1°C accuracy
- **Blocked By**: TASK-014

---

**TASK-024: Train Predictive Maintenance Model**
- **Priority**: 🟢 MEDIUM
- **Assignee**: Data Scientist
- **Effort**: 8 hours
- **Description**: Predict sensor failures 2-4 weeks early
- **Steps**:
  1. Collect historical drift data
  2. Identify patterns before failures
  3. Train ML model (scikit-learn)
  4. Deploy model to server
  5. Test predictions
- **Acceptance**: Predicts failures with >80% accuracy
- **Blocked By**: TASK-023

---

### Epic 6: 📱 Mobile Experience (Week 5-6)

**TASK-025: Optimize Dashboard for Mobile**
- **Priority**: 🟡 HIGH
- **Assignee**: Frontend Dev
- **Effort**: 4 hours
- **Description**: Make dashboard mobile-responsive
- **Steps**:
  1. Add CSS media queries
  2. Test on iPhone (Safari)
  3. Test on Android (Chrome)
  4. Optimize touch targets (44px minimum)
  5. Test graphs on small screens
- **Acceptance**: All features work on mobile
- **Blocked By**: TASK-015

---

**TASK-026: Add Mobile AC Controls**
- **Priority**: 🟢 MEDIUM
- **Assignee**: Frontend Dev
- **Effort**: 2 hours
- **Description**: Control AC from phone dashboard
- **Steps**:
  1. Add AC control buttons to mobile UI
  2. Add temperature slider
  3. Add mode selector (cool/heat/fan)
  4. Test on mobile devices
  5. Add confirmation notifications
- **Acceptance**: Can control AC from phone
- **Blocked By**: TASK-025

---

**TASK-027: Create Progressive Web App (PWA)**
- **Priority**: 🔵 LOW
- **Assignee**: Frontend Dev
- **Effort**: 4 hours
- **Description**: Enable "Add to Home Screen"
- **Steps**:
  1. Create `manifest.json`
  2. Add service worker for offline support
  3. Add app icons (192px, 512px)
  4. Test installation on iOS/Android
  5. Cache critical assets
- **Acceptance**: Can install app on home screen
- **Blocked By**: TASK-025

---

### Epic 7: 🔧 DevOps & Infrastructure (Ongoing)

**TASK-028: Set Up Automated Backups**
- **Priority**: 🔴 CRITICAL
- **Assignee**: DevOps
- **Effort**: 1 hour
- **Description**: Daily automated backups
- **Steps**:
  1. Configure backup script: `deploy/backup.sh`
  2. Set up systemd timer (daily at 2 AM)
  3. Configure USB drive mount
  4. Test backup/restore
  5. Set up Backblaze B2 for cloud backup (weekly)
- **Acceptance**: Backups run daily, can restore successfully
- **Blocked By**: TASK-009

---

**TASK-029: Configure Monitoring Alerts**
- **Priority**: 🟡 HIGH
- **Assignee**: DevOps
- **Effort**: 1 hour
- **Description**: Server health monitoring
- **Steps**:
  1. Install Prometheus Node Exporter
  2. Configure alerts: CPU, RAM, disk, temp
  3. Add to Grafana
  4. Test alert notifications
  5. Document runbook
- **Acceptance**: Alerts sent when resources exceed thresholds
- **Blocked By**: TASK-015

---

**TASK-030: Set Up SonarQube**
- **Priority**: 🟢 MEDIUM
- **Assignee**: DevOps
- **Effort**: 2 hours
- **Description**: Code quality analysis
- **Steps**:
  1. Run `sonarqube/scripts/install.sh`
  2. Configure project in SonarQube UI
  3. Run first analysis
  4. Fix critical issues
  5. Set up quality gates
- **Acceptance**: Code analysis runs, no critical issues
- **Blocked By**: None

---

## 📅 SPRINT PLANNING

### Sprint 0: Pre-Deployment (1-2 days)
**Goal**: Fix security issues, merge to dev

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-001 | 5 min | DevOps |
| TASK-002 | 10 min | DevOps |
| TASK-003 | 2 min | DevOps |
| TASK-004 | 30 min | Tech Writer |
| TASK-005 | 30 min | QA |
| TASK-006 | 1 hour | Team Lead |
| TASK-007 | 15 min | DevOps |
| TASK-008 | 5 min | DevOps |

**Total**: ~3 hours

---

### Sprint 1: Dev Environment Setup (Week 1)
**Goal**: Deploy to dev, basic functionality working

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-009 | 1 hour | DevOps |
| TASK-010 | 30 min | DevOps |
| TASK-011 | 15 min | DevOps |
| TASK-012 | 15 min | QA |
| TASK-013 | 10 min | QA |
| TASK-014 | 30 min | Hardware Tech |
| TASK-015 | 2 hours | DevOps |
| TASK-028 | 1 hour | DevOps |

**Total**: ~6 hours

---

### Sprint 2: Business Features (Week 2)
**Goal**: SaaS platform functional

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-016 | 15 min | QA |
| TASK-017 | 30 min | QA |
| TASK-018 | 1 hour | Sales |
| TASK-029 | 1 hour | DevOps |

**Total**: ~3 hours

---

### Sprint 3: Multi-Location (Week 3)
**Goal**: VPN working, can monitor 2 locations

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-019 | 2 hours | DevOps |
| TASK-020 | 1 hour | DevOps |
| TASK-021 | 30 min | QA |

**Total**: ~4 hours

---

### Sprint 4: Automation (Week 4)
**Goal**: Smart rules, drift detection

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-022 | 30 min | Automation Engineer |
| TASK-023 | 4 hours | Data Scientist |
| TASK-024 | 8 hours | Data Scientist |

**Total**: ~13 hours

---

### Sprint 5: Mobile (Week 5)
**Goal**: Mobile-optimized experience

| Task | Effort | Assignee |
|------|--------|----------|
| TASK-025 | 4 hours | Frontend Dev |
| TASK-026 | 2 hours | Frontend Dev |
| TASK-027 | 4 hours | Frontend Dev |

**Total**: ~10 hours

---

## 🎯 DEFINITION OF DONE

A task/story is considered "DONE" when:

### Code
- ✅ Code written and committed
- ✅ Code reviewed by peer
- ✅ No security vulnerabilities
- ✅ No hardcoded credentials

### Testing
- ✅ Unit tests written (if applicable)
- ✅ All tests pass
- ✅ Manual testing completed
- ✅ Edge cases covered

### Documentation
- ✅ Code comments added
- ✅ API docs updated (if API changes)
- ✅ User manual updated (if user-facing)
- ✅ README updated (if setup changes)

### Deployment
- ✅ Deployed to dev environment
- ✅ Smoke tests pass
- ✅ No errors in logs
- ✅ Rollback plan documented

### Business
- ✅ Acceptance criteria met
- ✅ Product owner approved
- ✅ Demo completed
- ✅ Customers notified (if needed)

---

## 📊 PROGRESS TRACKING

### Kanban Board Columns

1. **📋 Backlog** - Not started
2. **🔄 In Progress** - Currently working
3. **👀 Review** - Code review / QA
4. **🧪 Testing** - QA testing
5. **✅ Done** - Completed

### Priority Levels

- 🔴 **CRITICAL** - Blocking production deployment
- 🟡 **HIGH** - Needed for core functionality
- 🟢 **MEDIUM** - Important but not urgent
- 🔵 **LOW** - Nice to have

### Story Points Scale

- **1 point** = 15 minutes (trivial change)
- **3 points** = 1 hour (simple feature)
- **5 points** = 2-3 hours (moderate feature)
- **8 points** = 1 day (complex feature)
- **13 points** = 2-3 days (very complex)
- **21 points** = 1 week (epic, break down further)

---

## 🎉 NEXT STEPS

**Immediate (Today):**
1. Complete Sprint 0 tasks (security fixes)
2. Merge to dev branch
3. Tag release

**This Week:**
1. Deploy to dev Raspberry Pi
2. Test all features
3. Fix any critical bugs

**Next Week:**
1. Begin multi-location setup (Porto VPN)
2. Start lead generation (Porto market)
3. Create customer onboarding materials

**This Month:**
1. Deploy first production customer
2. Monitor performance/stability
3. Iterate based on feedback

---

**Questions?** Refer to:
- `USER_MANUAL.md` - How to use the system
- `TESTING_GUIDE.md` - How to test features
- `DEV_BRANCH_STATUS.md` - What's in dev vs feature/dashboard
- `CODE_REVIEW_feature-dashboard-to-dev.md` - Security review

**Ready to start?** Begin with **Sprint 0** tasks! 🚀
