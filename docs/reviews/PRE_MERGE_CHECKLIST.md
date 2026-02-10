# ✅ PRE-MERGE CHECKLIST: feature/dashboard → dev

**Status:** 🟡 REQUIRES FIXES (2-4 hours estimated)
**Current Test Status:** 147/148 passing

---

## 🔴 CRITICAL (Must Fix Before Merge)

### 1. Fix pytest Collection Error
**File:** `backend/test_real_notification.py:57`
**Issue:** `sys.exit(1)` kills pytest collection when InfluxDB is unavailable

**Option A: Move to scripts directory (Recommended)**
```bash
git mv backend/test_real_notification.py backend/scripts/test_real_notification.py
```

**Option B: Use pytest.skip**
```python
# Replace lines 54-57 with:
if not real_sensor_data:
    pytest.skip("No data in InfluxDB - Arduino not running")
```

**Verification:**
```bash
cd backend/api && python -m pytest --collect-only
# Should show 148 tests collected
```

---

### 2. Remove Local Settings from Changeset
**File:** `.claude/settings.local.json`
**Issue:** Local config file should not be committed

**Fix:**
```bash
git restore .claude/settings.local.json
echo ".claude/settings.local.json" >> .gitignore
git add .gitignore
git commit -m "chore: Prevent .claude/settings.local.json from being tracked"
```

---

### 3. Add Business Model Tests
**Missing:** `backend/api/test_business_model.py`
**Impact:** Core revenue logic has no automated tests

**Required Tests:**
```bash
cd backend/api
touch test_business_model.py
```

**Test Template:**
```python
import pytest
from business_model import BusinessModel, SUBSCRIPTION_TIERS

class TestSubscriptionTiers:
    def test_tier_limits_enforced(self):
        """Verify Bronze tier can't exceed 3 crops"""
        biz = BusinessModel()
        client_id = biz.create_client("Test Farm", tier="bronze")

        # Should succeed (under limit)
        for i in range(3):
            assert biz.add_crop(client_id, f"crop_{i}") is not None

        # Should fail (over limit)
        with pytest.raises(ValueError, match="Tier limit exceeded"):
            biz.add_crop(client_id, "crop_4")

    def test_revenue_calculation(self):
        """Verify MRR calculation is correct"""
        biz = BusinessModel()
        biz.create_client("Farm A", tier="bronze")   # €49
        biz.create_client("Farm B", tier="silver")   # €199
        biz.create_client("Farm C", tier="gold")     # €499

        mrr = biz.calculate_monthly_revenue()
        assert mrr == 747  # 49 + 199 + 499

    def test_client_health_score(self):
        """Verify negative points system for health score"""
        biz = BusinessModel()
        client_id = biz.create_client("Test Farm")

        # Start at 100
        assert biz.get_client_health(client_id) == 100

        # Sensor drift detected → -10 points
        biz.record_sensor_drift(client_id, "temperature")
        assert biz.get_client_health(client_id) == 90

        # Calibration overdue → -15 points
        biz.record_calibration_overdue(client_id)
        assert biz.get_client_health(client_id) == 75
```

**Add Tests For:**
- ✅ Tier limit enforcement (crops, zones, data retention)
- ✅ Revenue calculations (MRR, ARR, projected growth)
- ✅ Client health scores (negative points system)
- ✅ Calibration due alerts (upselling trigger)
- ✅ Service visit revenue tracking

---

### 4. Replace Placeholder Values
**Files:** `backend/api/tier_notification_router.py`
**Issue:** Production code has placeholder phone numbers

**Find and Replace:**
```bash
grep -r "XXX-XXXX" backend/
# Expected output:
# backend/api/tier_notification_router.py:150: +351-XXX-XXXX
# backend/api/tier_notification_router.py:152: +351-XXX-XXXX
```

**Fix:**
```python
# Option A: Use environment variable
support_phone = os.getenv('SUPPORT_PHONE_GOLD', '+351-XXX-XXXX')
recommended_action = f"Call 24/7 support: {support_phone}"

# Option B: Remove phone numbers until service is set up
recommended_action = "Your dedicated account manager will contact you shortly."
```

**Update .env.example:**
```bash
# Emergency Contact Numbers (leave empty until service contracts signed)
# SUPPORT_PHONE_SILVER=+351-XXX-XXXX
# SUPPORT_PHONE_GOLD=+351-XXX-XXXX
# SUPPORT_PHONE_PLATINUM=+351-XXX-XXXX
```

---

### 5. Generate Strong API Keys
**File:** `backend/.env.example`
**Issue:** Weak default passwords (agritech2026, easily guessable)

**Fix:**
```bash
cd backend
cp .env.example .env.example.backup

# Generate strong keys
echo "# Generate strong random keys for production:"
echo "API_KEY=$(openssl rand -hex 32)"
echo "INFLUXDB_TOKEN=$(openssl rand -base64 32)"
echo "INFLUXDB_PASSWORD=$(openssl rand -base64 16)"
echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)"
```

**Update .env.example:**
```bash
# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=CHANGE_ME_GENERATE_RANDOM  # openssl rand -base64 16
INFLUXDB_ORG=agritech
INFLUXDB_BUCKET=hydroponics
INFLUXDB_TOKEN=CHANGE_ME_GENERATE_RANDOM  # openssl rand -base64 32

# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=CHANGE_ME_GENERATE_RANDOM  # openssl rand -base64 16

# API Authentication
API_KEY=CHANGE_ME_GENERATE_RANDOM  # openssl rand -hex 32
```

**Add Security Note:**
```bash
# SECURITY WARNING:
# - NEVER commit .env files with real credentials to git
# - Generate unique random keys for each environment (dev, prod)
# - Rotate API keys every 90 days
# - Use strong passwords (16+ chars, random)
```

---

## ✅ VERIFICATION STEPS

### Run Full Test Suite
```bash
cd backend/api
python -m pytest -v

# Expected output:
# ==================== 148 passed in 30s ====================
```

### Check for Uncommitted Changes
```bash
git status
# Expected: Only intentional changes (no .claude/settings.local.json)
```

### Verify Security
```bash
# Check for hardcoded secrets
grep -r "agritech2026" backend/
grep -r "CHANGE_ME" backend/

# Should only find .env.example (not real .env files)
```

### Test Build
```bash
cd backend
docker-compose build

# Expected: No errors
```

---

## 🟡 OPTIONAL (Before Production - Not Blocking Merge)

### 6. Complete Twilio Integration
**Files:** `backend/api/notification_service.py`
**Status:** Stubbed out (returns True but doesn't send)

**Decision Required:**
- [ ] Remove WhatsApp/SMS stubs (if not using Twilio)
- [ ] Complete Twilio integration (if using paid service)
- [ ] Keep stubs for future implementation

### 7. Add HTTPS Enforcement
**Goal:** Secure API communication in production

**Implementation:**
```bash
# Install Caddy reverse proxy
sudo apt install caddy

# Configure Caddyfile
echo "agritech.yourdomain.com {
    reverse_proxy localhost:3001
    tls your-email@example.com
}" | sudo tee /etc/caddy/Caddyfile

sudo systemctl restart caddy
```

### 8. Extract server.py Route Handlers
**File:** `backend/api/server.py:do_GET()` (200+ lines)

**Refactor:**
```python
# Create backend/api/routes.py
def handle_api_health(self):
    self._send_json(200, {"status": "healthy", "version": "2.0.0"})

def handle_api_data_latest(self):
    latest = query_latest()
    self._send_json(200, {"latest": latest})

# In server.py:do_GET()
if path == "/api/health":
    return self.handle_api_health()
elif path == "/api/data/latest":
    return self.handle_api_data_latest()
```

---

## 📊 MERGE READINESS CHECKLIST

- [ ] Fix pytest collection error (test_real_notification.py)
- [ ] Remove .claude/settings.local.json from changeset
- [ ] Add tests for business_model.py (at least 5 tests)
- [ ] Replace placeholder phone numbers
- [ ] Generate strong API keys in .env.example
- [ ] Run full test suite (148 tests passing)
- [ ] Verify no hardcoded secrets
- [ ] Docker build succeeds

**When all items are checked:**
```bash
git add .
git commit -m "fix: Address pre-merge checklist items

- Fix pytest collection error in test_real_notification.py
- Add comprehensive tests for business_model.py
- Replace placeholder values with env vars
- Generate strong API keys in .env.example
- Update .gitignore for local settings

All 148 tests passing ✅
Ready for merge to dev branch."

git push origin feature/dashboard
```

**Then create pull request:**
```bash
gh pr create \
  --base dev \
  --head feature/dashboard \
  --title "feat: SaaS Platform Upgrade - Multi-Tenant Architecture" \
  --body "See CODE_REVIEW_feature-dashboard.md for full analysis.

Changes:
- Multi-tenant subscription system (Bronze/Silver/Gold/Platinum)
- DRY configuration system (7 crop varieties)
- Rule engine with JSON configs
- Multi-channel notifications (6 channels)
- Growth stage tracking
- Business intelligence dashboard
- DevOps deployment automation

Test Coverage: 148 tests passing
Scalability: 1-100+ clients supported
Revenue Model: €49-€799/month per client"
```

---

**Estimated Time:** 2-4 hours
**Priority:** 🔴 HIGH (blocking merge to dev)
**Assignee:** @t0118430
**Reviewer:** Will need approval after fixes complete
