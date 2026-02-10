# 🎯 PRODUCT BACKLOG - AgriTech SaaS Platform
**Project:** Technological Foods - Hydroponics Monitoring System
**Version:** 2.0.0 (SaaS Platform Upgrade)
**Last Updated:** 2026-02-09

---

## 📊 BACKLOG SUMMARY

| Priority | Epics | Stories | Tasks | Est. Hours |
|----------|-------|---------|-------|------------|
| 🔴 P0 - Critical (Blocking Merge) | 1 | 5 | 12 | 8h |
| 🟠 P1 - High (Pre-Production) | 2 | 8 | 24 | 40h |
| 🟡 P2 - Medium (Launch Ready) | 3 | 12 | 36 | 80h |
| 🟢 P3 - Low (Future) | 4 | 15 | 45 | 120h |
| **TOTAL** | **10** | **40** | **117** | **248h** |

---

# 🔴 EPIC 1: Code Quality & Test Coverage (P0 - CRITICAL)
**Goal:** Fix blocking issues preventing merge to dev branch
**Business Value:** Enable deployment of SaaS platform features
**Sprint:** Immediate (Today)
**Estimated Effort:** 8 hours

---

## 📖 User Story 1.1: Fix Test Suite Execution
**As a** DevOps engineer
**I want** the test suite to run without errors
**So that** CI/CD pipelines can validate code quality automatically

### Acceptance Criteria
- [ ] All 148 tests can be collected by pytest
- [ ] Tests pass without InfluxDB running (use mocks/skips)
- [ ] CI/CD pipeline executes tests successfully
- [ ] Test execution time < 60 seconds

### Tasks
- [ ] **TASK-101** [2h] Fix test_real_notification.py sys.exit() error
  - **Description:** Move integration test to scripts/ directory or use pytest.skip
  - **Files:** `backend/test_real_notification.py`
  - **Acceptance:** `pytest --collect-only` shows 148 tests
  - **Priority:** P0 - Critical
  ```bash
  # Implementation
  git mv backend/test_real_notification.py backend/scripts/manual_test_notification.py
  # OR add pytest.skip decorator
  ```

- [ ] **TASK-102** [1h] Verify test isolation and fixtures
  - **Description:** Ensure all test fixtures properly clean up resources
  - **Files:** `backend/api/test_*.py`
  - **Acceptance:** Tests can run in any order without failures
  - **Priority:** P0 - Critical

- [ ] **TASK-103** [0.5h] Update CI/CD workflow for test execution
  - **Description:** Ensure GitHub Actions runs pytest correctly
  - **Files:** `.github/workflows/test-backend.yml`
  - **Acceptance:** Workflow badge shows passing status
  - **Priority:** P0 - Critical

---

## 📖 User Story 1.2: Add Business Model Test Coverage
**As a** Product Manager
**I want** automated tests for revenue calculations
**So that** billing logic is guaranteed to be correct

### Acceptance Criteria
- [ ] Test coverage for subscription tier limits (Bronze: 3 crops max)
- [ ] Test coverage for MRR/ARR calculations
- [ ] Test coverage for client health score system
- [ ] Test coverage for upselling triggers (calibration due)
- [ ] All tests pass with >95% code coverage

### Tasks
- [ ] **TASK-104** [3h] Create test_business_model.py
  - **Description:** Comprehensive tests for subscription tiers and revenue
  - **Files:** `backend/api/test_business_model.py`
  - **Acceptance:** 15+ tests covering all business logic
  - **Priority:** P0 - Critical
  ```python
  # Test cases required:
  # - test_bronze_tier_crop_limit()
  # - test_silver_tier_data_retention()
  # - test_gold_tier_features_enabled()
  # - test_platinum_unlimited_crops()
  # - test_monthly_revenue_calculation()
  # - test_annual_revenue_projection()
  # - test_client_health_score_degrade()
  # - test_calibration_due_alert_trigger()
  # - test_tier_upgrade_revenue_impact()
  # - test_inactive_client_exclusion()
  ```

- [ ] **TASK-105** [1h] Create test_client_manager.py
  - **Description:** Tests for client CRUD and sensor tracking
  - **Files:** `backend/api/test_client_manager.py`
  - **Acceptance:** 10+ tests for client management
  - **Priority:** P0 - Critical

- [ ] **TASK-106** [1h] Add pytest-cov configuration
  - **Description:** Generate code coverage reports
  - **Files:** `backend/pytest.ini`, `.github/workflows/test-backend.yml`
  - **Acceptance:** Coverage report shows >95% for business logic
  - **Priority:** P0 - Critical

---

## 📖 User Story 1.3: Remove Sensitive Files from Version Control
**As a** Security Engineer
**I want** local configuration files excluded from git
**So that** sensitive settings don't leak to repository

### Acceptance Criteria
- [ ] .claude/settings.local.json not in changeset
- [ ] .gitignore prevents future commits of local configs
- [ ] No .env files with real credentials in git history
- [ ] Security audit passes

### Tasks
- [ ] **TASK-107** [0.5h] Remove .claude/settings.local.json from commit
  - **Description:** Restore file and add to .gitignore
  - **Priority:** P0 - Critical
  ```bash
  git restore .claude/settings.local.json
  echo ".claude/settings.local.json" >> .gitignore
  git add .gitignore
  git commit -m "chore: Prevent local settings from being tracked"
  ```

---

## 📖 User Story 1.4: Replace Placeholder Values
**As a** System Administrator
**I want** production code free of placeholder values
**So that** system works correctly in production

### Acceptance Criteria
- [ ] No "XXX-XXXX" phone numbers in code
- [ ] All placeholder values use environment variables
- [ ] .env.example has clear instructions for required values
- [ ] Deployment guide documents all required environment variables

### Tasks
- [ ] **TASK-108** [0.5h] Replace placeholder phone numbers
  - **Description:** Use env vars for support contact numbers
  - **Files:** `backend/api/tier_notification_router.py`
  - **Priority:** P0 - Critical
  ```python
  # Before: "Call +351-XXX-XXXX"
  # After:
  support_phone = os.getenv('SUPPORT_PHONE_GOLD', 'Contact your account manager')
  ```

---

## 📖 User Story 1.5: Strengthen Security Configuration
**As a** Security Engineer
**I want** strong default API keys generated
**So that** developers don't use weak passwords in production

### Acceptance Criteria
- [ ] .env.example has "CHANGE_ME" placeholders (not weak defaults)
- [ ] Documentation explains how to generate strong keys
- [ ] Example commands provided (openssl rand)
- [ ] Warning message about security best practices

### Tasks
- [ ] **TASK-109** [0.5h] Update .env.example with strong key generation
  - **Description:** Replace weak defaults with CHANGE_ME + instructions
  - **Files:** `backend/.env.example`
  - **Priority:** P0 - Critical
  ```bash
  # Add header comment:
  # SECURITY: Generate strong random keys for production
  # API_KEY=$(openssl rand -hex 32)
  # INFLUXDB_TOKEN=$(openssl rand -base64 32)
  ```

---

# 🟠 EPIC 2: Production Security (P1 - HIGH)
**Goal:** Secure API endpoints and data transmission
**Business Value:** Prevent data breaches, maintain customer trust
**Sprint:** Pre-Production (Before Launch)
**Estimated Effort:** 20 hours

---

## 📖 User Story 2.1: Add HTTPS Encryption
**As a** Customer
**I want** my sensor data encrypted in transit
**So that** competitors can't intercept my greenhouse metrics

### Acceptance Criteria
- [ ] All API requests use HTTPS (not HTTP)
- [ ] SSL certificate auto-renews (Let's Encrypt)
- [ ] HTTP requests redirect to HTTPS
- [ ] Security headers configured (HSTS, CSP)

### Tasks
- [ ] **TASK-201** [4h] Install and configure Caddy reverse proxy
  - **Description:** Add HTTPS termination with auto-SSL
  - **Files:** New `Caddyfile`, deployment docs
  - **Priority:** P1 - High
  ```bash
  # Install Caddy
  sudo apt install caddy

  # Caddyfile
  api.agritech.com {
      reverse_proxy localhost:3001
      tls your-email@example.com
  }
  ```

- [ ] **TASK-202** [2h] Update API endpoints to enforce HTTPS
  - **Description:** Reject non-HTTPS requests in production
  - **Files:** `backend/api/server.py`
  - **Priority:** P1 - High

- [ ] **TASK-203** [1h] Add security headers
  - **Description:** HSTS, X-Frame-Options, CSP
  - **Files:** `Caddyfile` or `backend/api/server.py`
  - **Priority:** P1 - High

- [ ] **TASK-204** [1h] Update documentation
  - **Description:** Document HTTPS setup in deployment guide
  - **Files:** `deploy/QUICKSTART_TWO_ENVS.md`
  - **Priority:** P1 - High

---

## 📖 User Story 2.2: Implement API Key Rotation
**As a** System Administrator
**I want** ability to rotate API keys without manual .env edits
**So that** leaked keys can be quickly invalidated

### Acceptance Criteria
- [ ] Admin endpoint to generate new API key
- [ ] Old key invalidated immediately after rotation
- [ ] New key returned securely (one-time display)
- [ ] Audit log records all key rotations
- [ ] Documentation for rotation procedure

### Tasks
- [ ] **TASK-205** [4h] Create API key rotation endpoint
  - **Description:** POST /api/admin/rotate-key (requires current key)
  - **Files:** `backend/api/server.py`, `backend/api/auth.py`
  - **Priority:** P1 - High
  ```python
  @admin_required
  def rotate_api_key(self):
      new_key = secrets.token_hex(32)
      # Update .env file or database
      # Log rotation event
      return {"new_key": new_key, "expires_old_key_in": "30s"}
  ```

- [ ] **TASK-206** [2h] Add audit logging for API key usage
  - **Description:** Track which key was used for each request
  - **Files:** `backend/api/server.py`, `backend/api/database.py`
  - **Priority:** P1 - High

- [ ] **TASK-207** [2h] Create admin CLI tool for key management
  - **Description:** Script to rotate keys via command line
  - **Files:** `backend/scripts/rotate_api_key.sh`
  - **Priority:** P1 - High

---

## 📖 User Story 2.3: Complete Twilio Integration or Remove Stubs
**As a** System Administrator
**I want** notification channels to either work or be clearly disabled
**So that** I don't think WhatsApp alerts are working when they're not

### Acceptance Criteria
- [ ] WhatsApp/SMS channels send real messages (if enabled)
- [ ] OR WhatsApp/SMS channels removed from code (if not using Twilio)
- [ ] Channel availability clearly shown in /api/notifications
- [ ] Documentation explains which channels are production-ready

### Tasks
- [ ] **TASK-208** [4h] Complete Twilio WhatsApp integration
  - **Description:** Implement actual Twilio API calls
  - **Files:** `backend/api/notification_service.py`
  - **Priority:** P1 - High (if using Twilio)
  ```python
  from twilio.rest import Client

  def send(self, subject: str, body: str) -> bool:
      client = Client(self.account_sid, self.auth_token)
      message = client.messages.create(
          body=f"{subject}\n{body}",
          from_=f"whatsapp:{self.from_number}",
          to=f"whatsapp:{self.to_number}"
      )
      return message.sid is not None
  ```

- [ ] **TASK-209** [1h] Add Twilio webhook for delivery status
  - **Description:** Track message delivery (delivered, failed, read)
  - **Files:** `backend/api/server.py` (new endpoint)
  - **Priority:** P1 - Medium

- [ ] **TASK-210** [1h] Remove stub channels if not using Twilio
  - **Description:** Delete WhatsAppChannel and SMSChannel classes
  - **Files:** `backend/api/notification_service.py`
  - **Priority:** P1 - High (if NOT using Twilio)

---

# 🟠 EPIC 3: Database Scalability (P1 - HIGH)
**Goal:** Prepare database for 100+ clients
**Business Value:** Support multi-city expansion without performance degradation
**Sprint:** Pre-Production
**Estimated Effort:** 20 hours

---

## 📖 User Story 3.1: Add PostgreSQL Migration Path
**As a** DevOps Engineer
**I want** documented migration from SQLite to PostgreSQL
**So that** system scales beyond 100 clients

### Acceptance Criteria
- [ ] Migration script converts SQLite → PostgreSQL
- [ ] Database abstraction layer supports both databases
- [ ] Performance benchmarks documented (SQLite vs PostgreSQL)
- [ ] Zero-downtime migration procedure documented

### Tasks
- [ ] **TASK-301** [8h] Create database abstraction layer
  - **Description:** Support SQLite and PostgreSQL with same API
  - **Files:** `backend/api/database.py`
  - **Priority:** P1 - High
  ```python
  class Database:
      def __init__(self, db_type='sqlite'):
          if db_type == 'postgresql':
              self.engine = create_engine(DATABASE_URL)
          else:
              self.engine = create_engine(f'sqlite:///{DB_PATH}')
  ```

- [ ] **TASK-302** [4h] Write SQLite → PostgreSQL migration script
  - **Description:** Export data and import to PostgreSQL
  - **Files:** `backend/scripts/migrate_to_postgres.py`
  - **Priority:** P1 - High

- [ ] **TASK-303** [4h] Performance benchmarking
  - **Description:** Compare query performance at 10, 50, 100, 500 clients
  - **Files:** `docs/PERFORMANCE_BENCHMARKS.md`
  - **Priority:** P1 - Medium

- [ ] **TASK-304** [4h] Document zero-downtime migration
  - **Description:** Step-by-step migration guide
  - **Files:** `deploy/POSTGRES_MIGRATION.md`
  - **Priority:** P1 - High

---

# 🟡 EPIC 4: Business Intelligence Dashboard (P2 - MEDIUM)
**Goal:** Complete real-time business metrics dashboard
**Business Value:** Enable data-driven decision making for expansion
**Sprint:** Launch Ready
**Estimated Effort:** 24 hours

---

## 📖 User Story 4.1: Real-Time Revenue Tracking
**As a** Business Owner
**I want** live MRR/ARR metrics on dashboard
**So that** I can track revenue growth daily

### Acceptance Criteria
- [ ] Dashboard shows current MRR (Monthly Recurring Revenue)
- [ ] Dashboard shows projected ARR (Annual Recurring Revenue)
- [ ] Revenue breakdown by tier (Bronze/Silver/Gold/Platinum)
- [ ] Historical revenue chart (last 12 months)
- [ ] Churn rate displayed

### Tasks
- [ ] **TASK-401** [4h] Implement revenue calculation endpoints
  - **Description:** GET /api/business/revenue/current, /historical
  - **Files:** `backend/api/business_dashboard.py`
  - **Priority:** P2 - Medium

- [ ] **TASK-402** [4h] Create revenue visualization dashboard
  - **Description:** Charts.js or similar for revenue graphs
  - **Files:** `backend/dashboard.html`
  - **Priority:** P2 - Medium

- [ ] **TASK-403** [2h] Add tier distribution pie chart
  - **Description:** Show % of clients in each tier
  - **Files:** `backend/dashboard.html`
  - **Priority:** P2 - Medium

---

## 📖 User Story 4.2: Client Health Monitoring
**As a** Customer Success Manager
**I want** real-time client health scores
**So that** I can proactively reach out to at-risk clients

### Acceptance Criteria
- [ ] Dashboard shows all clients with health scores (0-100)
- [ ] Color-coded alerts (Green >80, Yellow 60-80, Red <60)
- [ ] List of clients requiring attention (calibration due, sensor drift)
- [ ] One-click action to schedule service visit
- [ ] Health score trend chart (last 30 days)

### Tasks
- [ ] **TASK-404** [6h] Create client health dashboard view
  - **Description:** Table with health scores, alerts, actions
  - **Files:** `backend/dashboard.html`, `backend/api/client_manager.py`
  - **Priority:** P2 - Medium

- [ ] **TASK-405** [4h] Add health score trend tracking
  - **Description:** Store daily health score snapshots
  - **Files:** `backend/api/database.py` (new table)
  - **Priority:** P2 - Medium

- [ ] **TASK-406** [2h] Implement service visit scheduling
  - **Description:** Create service visit from dashboard
  - **Files:** `backend/api/business_dashboard.py`
  - **Priority:** P2 - Low

---

## 📖 User Story 4.3: Upselling Opportunity Alerts
**As a** Sales Manager
**I want** automated upsell recommendations
**So that** I can increase ARPU (Average Revenue Per User)

### Acceptance Criteria
- [ ] Dashboard shows clients exceeding tier limits
- [ ] Recommended tier upgrade displayed (e.g., Bronze → Silver)
- [ ] Revenue impact calculation (e.g., +€150/month)
- [ ] One-click email template for upsell outreach
- [ ] Upsell conversion tracking

### Tasks
- [ ] **TASK-407** [4h] Create upsell recommendation engine
  - **Description:** Analyze client usage vs tier limits
  - **Files:** `backend/api/business_model.py`
  - **Priority:** P2 - Medium
  ```python
  def get_upsell_opportunities():
      # Find clients near tier limits
      # Example: Bronze client with 3 crops (at max)
      # Recommend: Upgrade to Silver (10 crops, +€150/mo)
  ```

- [ ] **TASK-408** [2h] Add upsell dashboard widget
  - **Description:** Show top 10 upsell opportunities
  - **Files:** `backend/dashboard.html`
  - **Priority:** P2 - Medium

- [ ] **TASK-409** [2h] Create email templates for upselling
  - **Description:** Pre-filled email for tier upgrades
  - **Files:** `backend/api/email_templates.py`
  - **Priority:** P2 - Low

---

# 🟡 EPIC 5: Multi-Location Deployment (P2 - MEDIUM)
**Goal:** Prepare for Porto → Lisbon → Algarve expansion
**Business Value:** Enable 3x revenue growth (€1,900 → €4,550/month)
**Sprint:** Pre-Launch
**Estimated Effort:** 32 hours

---

## 📖 User Story 5.1: VPN Network Setup
**As a** System Administrator
**I want** secure VPN connecting remote sites to Porto central server
**So that** sensor data from Lisbon/Algarve reaches central database

### Acceptance Criteria
- [ ] WireGuard VPN server running on Porto Raspberry Pi
- [ ] Remote sites can connect and send data
- [ ] Encrypted traffic (ChaCha20 cipher)
- [ ] Auto-reconnect on connection loss
- [ ] VPN health monitoring dashboard

### Tasks
- [ ] **TASK-501** [8h] Configure WireGuard VPN server (Porto)
  - **Description:** Central VPN server with 10.200.0.0/24 network
  - **Files:** `/etc/wireguard/wg0.conf`, `deploy/setup-vpn-server.sh`
  - **Priority:** P2 - High
  ```bash
  # WireGuard config
  [Interface]
  Address = 10.200.0.1/24
  PrivateKey = <generated>
  ListenPort = 51820

  [Peer] # Lisbon
  PublicKey = <lisbon-public-key>
  AllowedIPs = 10.200.0.2/32

  [Peer] # Algarve
  PublicKey = <algarve-public-key>
  AllowedIPs = 10.200.0.3/32
  ```

- [ ] **TASK-502** [4h] Create VPN client setup scripts
  - **Description:** Auto-configure remote Raspberry Pis
  - **Files:** `deploy/setup-vpn-client.sh`
  - **Priority:** P2 - High

- [ ] **TASK-503** [2h] Add VPN monitoring to dashboard
  - **Description:** Show connected sites and latency
  - **Files:** `backend/api/server.py`, `backend/dashboard.html`
  - **Priority:** P2 - Medium

---

## 📖 User Story 5.2: Multi-Site Data Synchronization
**As a** DevOps Engineer
**I want** data from remote sites automatically synced to central server
**So that** Lisbon/Algarve data appears in Porto dashboard

### Acceptance Criteria
- [ ] Remote Raspberry Pis store data locally (InfluxDB)
- [ ] Data auto-syncs to Porto when VPN available
- [ ] Queue mechanism prevents data loss during outages
- [ ] Conflict resolution for overlapping timestamps
- [ ] Sync status visible in dashboard

### Tasks
- [ ] **TASK-504** [8h] Implement sync queue system
  - **Description:** Buffer data when VPN down, sync when up
  - **Files:** `backend/api/sync_manager.py`
  - **Priority:** P2 - High
  ```python
  # Hybrid architecture
  # 1. Write to local InfluxDB (always works)
  # 2. Add to sync queue
  # 3. Background task: If VPN up, push to central
  # 4. On success, remove from queue
  ```

- [ ] **TASK-505** [4h] Add sync status monitoring
  - **Description:** Track last successful sync per site
  - **Files:** `backend/api/database.py`, `backend/dashboard.html`
  - **Priority:** P2 - Medium

- [ ] **TASK-506** [2h] Test sync with simulated outages
  - **Description:** Verify no data loss during 1-hour VPN outage
  - **Files:** `backend/tests/test_sync_resilience.py`
  - **Priority:** P2 - High

---

## 📖 User Story 5.3: Remote Site Health Monitoring
**As a** System Administrator
**I want** alerts when remote sites go offline
**So that** I can dispatch technician before crops are affected

### Acceptance Criteria
- [ ] Dashboard shows online/offline status per site
- [ ] Alert sent if site offline >15 minutes
- [ ] Last heartbeat timestamp displayed
- [ ] CPU, RAM, disk usage visible for each site
- [ ] One-click reboot command (via VPN)

### Tasks
- [ ] **TASK-507** [4h] Implement heartbeat system
  - **Description:** Remote sites ping central every 60 seconds
  - **Files:** `backend/api/heartbeat_monitor.py`
  - **Priority:** P2 - High

- [ ] **TASK-508** [2h] Add site health dashboard
  - **Description:** Map view showing Porto, Lisbon, Algarve status
  - **Files:** `backend/dashboard.html`
  - **Priority:** P2 - Medium

- [ ] **TASK-509** [2h] Create remote reboot command
  - **Description:** SSH-based reboot via VPN (for troubleshooting)
  - **Files:** `backend/api/remote_management.py`
  - **Priority:** P2 - Low

---

# 🟢 EPIC 6: Customer Portal (P3 - LOW / FUTURE)
**Goal:** Self-service portal for B2B clients
**Business Value:** Reduce support burden, improve customer satisfaction
**Sprint:** Post-Launch Enhancement
**Estimated Effort:** 40 hours

---

## 📖 User Story 6.1: Client Dashboard Access
**As a** Greenhouse Owner (B2B Client)
**I want** web dashboard to view my sensor data
**So that** I don't need to call support for basic metrics

### Acceptance Criteria
- [ ] Client login with email/password
- [ ] Dashboard shows only their greenhouses
- [ ] Real-time sensor data (temperature, humidity, pH, EC)
- [ ] Historical charts (last 7/30/90 days based on tier)
- [ ] Mobile-responsive design

### Tasks
- [ ] **TASK-601** [8h] Create client authentication system
  - **Description:** Login/logout, password reset
  - **Files:** `backend/api/auth.py`, `backend/client_portal.html`
  - **Priority:** P3 - Future

- [ ] **TASK-602** [8h] Build client dashboard UI
  - **Description:** React or Vue.js dashboard
  - **Files:** `frontend/src/ClientDashboard.vue`
  - **Priority:** P3 - Future

- [ ] **TASK-603** [4h] Add data filtering by date range
  - **Description:** Client can select 7/30/90 day views
  - **Files:** `backend/api/data_access.py`
  - **Priority:** P3 - Future

---

## 📖 User Story 6.2: Self-Service Tier Upgrades
**As a** Greenhouse Owner
**I want** to upgrade my subscription tier online
**So that** I can unlock more features without calling sales

### Acceptance Criteria
- [ ] Client can view current tier and features
- [ ] Side-by-side tier comparison table
- [ ] One-click upgrade to higher tier
- [ ] Payment processing (Stripe or similar)
- [ ] Prorated billing for mid-month upgrades

### Tasks
- [ ] **TASK-604** [8h] Integrate Stripe payment gateway
  - **Description:** Subscription management via Stripe
  - **Files:** `backend/api/billing.py`
  - **Priority:** P3 - Future

- [ ] **TASK-605** [4h] Create tier comparison UI
  - **Description:** Show features per tier with upgrade CTA
  - **Files:** `frontend/src/TierComparison.vue`
  - **Priority:** P3 - Future

- [ ] **TASK-606** [4h] Implement prorated billing logic
  - **Description:** Calculate refund + new charge for mid-month upgrade
  - **Files:** `backend/api/billing.py`
  - **Priority:** P3 - Future

---

# 🟢 EPIC 7: Advanced Notifications (P3 - FUTURE)
**Goal:** Add Slack, Discord, Telegram channels
**Business Value:** Meet customer preferences for notification platforms
**Sprint:** Post-Launch
**Estimated Effort:** 24 hours

---

## 📖 User Story 7.1: Slack Integration
**As a** Tech-Savvy Grower
**I want** alerts sent to my Slack workspace
**So that** I see notifications where my team already collaborates

### Acceptance Criteria
- [ ] Client can configure Slack webhook URL
- [ ] Alerts formatted with Slack blocks (rich formatting)
- [ ] Severity shown with emoji (🟢🟡🔴)
- [ ] Sensor charts embedded in Slack messages
- [ ] Test notification button in settings

### Tasks
- [ ] **TASK-701** [4h] Create SlackChannel class
  - **Description:** Implement NotificationChannel for Slack
  - **Files:** `backend/api/notification_service.py`
  - **Priority:** P3 - Future

- [ ] **TASK-702** [2h] Design Slack message templates
  - **Description:** Use Slack Block Kit for rich alerts
  - **Files:** `backend/api/slack_templates.py`
  - **Priority:** P3 - Future

- [ ] **TASK-703** [2h] Add Slack webhook configuration UI
  - **Description:** Client portal settings page
  - **Files:** `frontend/src/NotificationSettings.vue`
  - **Priority:** P3 - Future

---

# 🟢 EPIC 8: AI/ML Predictive Alerts (P3 - FUTURE)
**Goal:** Predict sensor failures before they happen
**Business Value:** Reduce downtime, improve crop yields
**Sprint:** Innovation Track
**Estimated Effort:** 60 hours

---

## 📖 User Story 8.1: Sensor Drift Prediction
**As a** Greenhouse Owner
**I want** alerts BEFORE sensor fails
**So that** I can schedule calibration proactively

### Acceptance Criteria
- [ ] ML model trained on historical sensor data
- [ ] Predict sensor drift 7 days in advance (80% accuracy)
- [ ] Alert sent: "pH sensor likely to drift in 5 days"
- [ ] Model retrains weekly with new data
- [ ] Prediction accuracy tracked in dashboard

### Tasks
- [ ] **TASK-801** [16h] Collect training data from 100+ sensors
  - **Description:** Export historical data for ML training
  - **Files:** `ml/data/sensor_history.csv`
  - **Priority:** P3 - Future

- [ ] **TASK-802** [16h] Train drift prediction model
  - **Description:** LSTM or Prophet model for time-series
  - **Files:** `ml/models/drift_predictor.py`
  - **Priority:** P3 - Future

- [ ] **TASK-803** [8h] Integrate model into API
  - **Description:** GET /api/sensors/{id}/drift-prediction
  - **Files:** `backend/api/ml_predictions.py`
  - **Priority:** P3 - Future

---

# 📋 IMMEDIATE ACTIONS (Next 2-4 Hours)

## Sprint 0: Critical Bug Fixes (Today)
**Goal:** Merge feature/dashboard → dev

### Action List
```bash
# 1. Fix pytest collection error (30 min)
cd backend
git mv test_real_notification.py scripts/manual_test_notification.py
pytest --collect-only  # Verify 148 tests

# 2. Remove local settings (5 min)
git restore .claude/settings.local.json
echo ".claude/settings.local.json" >> .gitignore

# 3. Add business model tests (2 hours)
touch backend/api/test_business_model.py
# Copy test template from PRE_MERGE_CHECKLIST.md
pytest backend/api/test_business_model.py -v

# 4. Replace placeholders (30 min)
# Edit tier_notification_router.py
# Replace +351-XXX-XXXX with env vars

# 5. Strengthen API keys (10 min)
cd backend
# Update .env.example with CHANGE_ME + instructions

# 6. Run full test suite (5 min)
pytest -v
# Expected: 148 passed

# 7. Commit and push
git add .
git commit -m "fix: Address pre-merge review items

- Fix pytest collection error
- Add comprehensive business model tests
- Replace placeholder values
- Strengthen API key configuration
- Remove local settings from tracking

All 148 tests passing ✅"

git push origin feature/dashboard

# 8. Create pull request
gh pr create \
  --base dev \
  --head feature/dashboard \
  --title "feat: SaaS Platform Upgrade - Multi-Tenant Architecture" \
  --body "$(cat CODE_REVIEW_feature-dashboard.md)"
```

---

# 📊 STORY POINT ESTIMATION

| Epic | Stories | Story Points | Priority |
|------|---------|--------------|----------|
| 1. Code Quality & Test Coverage | 5 | 13 | P0 |
| 2. Production Security | 3 | 21 | P1 |
| 3. Database Scalability | 1 | 21 | P1 |
| 4. Business Intelligence | 3 | 34 | P2 |
| 5. Multi-Location Deployment | 3 | 40 | P2 |
| 6. Customer Portal | 2 | 55 | P3 |
| 7. Advanced Notifications | 1 | 21 | P3 |
| 8. AI/ML Predictive Alerts | 1 | 89 | P3 |
| **TOTAL** | **19** | **294** | - |

**Velocity Assumptions:**
- 1 Story Point = ~1 hour (solo developer)
- Sprint Capacity: 40 SP/week (full-time)
- Part-time (20h/week): 20 SP/week

**Timeline Projection:**
- P0 (Critical): 1 day (today)
- P1 (High): 2 weeks
- P2 (Medium): 4 weeks
- P3 (Future): 12+ weeks

---

# 🎯 RECOMMENDED SPRINT PLAN

## Sprint 1: Critical Fixes (Today - 1 day)
- Fix test suite execution
- Add business model tests
- Security configuration
- **Goal:** Merge to dev ✅

## Sprint 2: Production Security (Week 1-2)
- HTTPS with Caddy
- API key rotation
- Twilio integration
- **Goal:** Production-ready security ✅

## Sprint 3: Database Scalability (Week 3-4)
- PostgreSQL migration path
- Performance benchmarks
- **Goal:** Support 100+ clients ✅

## Sprint 4: Multi-Location Prep (Week 5-6)
- VPN setup (Porto → Lisbon)
- Data sync system
- Remote monitoring
- **Goal:** Ready for Lisbon expansion ✅

## Sprint 5: Business Intelligence (Week 7-8)
- Revenue dashboard
- Client health monitoring
- Upselling engine
- **Goal:** Data-driven decisions ✅

## Sprint 6+: Future Enhancements
- Customer portal
- Advanced notifications (Slack, Discord)
- AI/ML predictive alerts

---

**Document Version:** 1.0.0
**Last Updated:** 2026-02-09
**Maintained By:** Product Team
**Review Frequency:** Weekly during active development

---

## 📦 EXPORT INSTRUCTIONS

### Import to Jira
```bash
# Convert to CSV for Jira import
# Epic,Summary,Description,Story Points,Priority
# EPIC-1,"Code Quality & Test Coverage","...",13,Highest
# ...
```

### Import to GitHub Issues
```bash
# Use GitHub CLI
gh issue create \
  --title "TASK-101: Fix test_real_notification.py" \
  --body "$(cat TASK_101_description.md)" \
  --label "P0,bug,testing" \
  --assignee @me
```

### Import to Linear
```bash
# Use Linear API or CSV import
# Check Linear docs: https://linear.app/docs/import
```
