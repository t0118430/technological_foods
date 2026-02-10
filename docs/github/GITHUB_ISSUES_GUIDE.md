# 🎯 GitHub Issues Creation Guide

## Quick Summary
You have **3 options** to create the P0 critical issues:

1. **Automated (Recommended):** Use GitHub CLI script
2. **Manual:** Copy-paste from markdown templates
3. **Web UI:** Create directly on GitHub.com

---

## ✅ Option 1: Automated with GitHub CLI (RECOMMENDED)

### Step 1: Install GitHub CLI
```bash
# Windows (using winget)
winget install --id GitHub.cli

# Or download from: https://cli.github.com/
```

### Step 2: Authenticate
```bash
gh auth login
# Follow prompts to authenticate with GitHub
```

### Step 3: Run the script
```bash
cd C:\git\technological_foods
bash create_github_issues.sh
```

**Result:** Creates 6 issues automatically:
- 5 individual P0 tasks
- 1 epic tracking issue

---

## ✅ Option 2: Manual Copy-Paste (No CLI needed)

### Issue 1: Fix pytest collection error

**Title:**
```
🔴 P0: Fix pytest collection error (test_real_notification.py)
```

**Labels:** `P0`, `bug`, `testing`, `blocking`

**Body:** Copy from [`issues/issue-1-pytest-fix.md`](#issue-1-content) below

---

### Issue 2: Remove local settings

**Title:**
```
🔴 P0: Remove .claude/settings.local.json from version control
```

**Labels:** `P0`, `chore`, `security`, `blocking`

**Body:** Copy from [`issues/issue-2-local-settings.md`](#issue-2-content) below

---

### Issue 3: Add business model tests

**Title:**
```
🔴 P0: Add comprehensive tests for business_model.py
```

**Labels:** `P0`, `testing`, `business-logic`, `blocking`

**Body:** Copy from [`issues/issue-3-business-tests.md`](#issue-3-content) below

---

### Issue 4: Replace placeholder phone numbers

**Title:**
```
🔴 P0: Replace placeholder phone numbers (+351-XXX-XXXX)
```

**Labels:** `P0`, `bug`, `production-ready`, `blocking`

**Body:** Copy from [`issues/issue-4-placeholders.md`](#issue-4-content) below

---

### Issue 5: Strengthen API key configuration

**Title:**
```
🔴 P0: Strengthen API key configuration (remove weak defaults)
```

**Labels:** `P0`, `security`, `configuration`, `blocking`

**Body:** Copy from [`issues/issue-5-api-keys.md`](#issue-5-content) below

---

### Epic Issue: Code Quality & Test Coverage

**Title:**
```
🎯 EPIC: Code Quality & Test Coverage (P0 - BLOCKING MERGE)
```

**Labels:** `P0`, `epic`, `blocking`

**Body:** Copy from [`issues/epic-p0-code-quality.md`](#epic-content) below

---

## ✅ Option 3: Web UI (GitHub.com)

### Steps:
1. Go to https://github.com/t0118430/technological_foods/issues
2. Click "New issue"
3. Copy title and body from sections above
4. Add labels manually
5. Assign to yourself
6. Click "Submit new issue"

Repeat for all 6 issues.

---

# 📝 Issue Content Templates

## <a name="issue-1-content"></a>Issue 1: Fix pytest collection error

```markdown
## Problem
`test_real_notification.py` uses `sys.exit(1)` which kills pytest collection when InfluxDB is unavailable.

## Current Error
```bash
cd backend/api && python -m pytest --collect-only
# INTERNALERROR: SystemExit: 1
# no tests ran in 0.45s
```

## Impact
- ❌ Blocks all test execution
- ❌ Breaks CI/CD pipeline
- ❌ Cannot verify code quality

## Solution Options

### Option A: Move to scripts directory (RECOMMENDED)
```bash
cd backend
git mv test_real_notification.py scripts/manual_test_notification.py
```

### Option B: Use pytest.skip
```python
# Replace lines 54-57 in test_real_notification.py:
if not real_sensor_data:
    pytest.skip('No data in InfluxDB - Arduino not running')
```

## Acceptance Criteria
- [ ] `pytest --collect-only` shows 148 tests collected
- [ ] No `sys.exit()` calls in test files
- [ ] CI/CD pipeline runs successfully
- [ ] Test execution time < 60 seconds

## Estimated Time
⏱️ 30 minutes

## Files Changed
- `backend/test_real_notification.py` (delete or modify)
- `backend/scripts/manual_test_notification.py` (create if using Option A)

## Verification
```bash
cd backend/api
python -m pytest --collect-only
# Expected: collected 148 items
```

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- See: `IMMEDIATE_ACTIONS.md` Task 1
```

---

## <a name="issue-2-content"></a>Issue 2: Remove local settings

```markdown
## Problem
Local configuration file `.claude/settings.local.json` is in the changeset and should be gitignored.

## Current Status
```bash
git status
# modified: .claude/settings.local.json
```

## Security Risk
- ⚠️ Local settings may contain sensitive paths
- ⚠️ Pollutes git history with developer-specific configs
- ⚠️ Could leak local environment details

## Solution
```bash
cd C:\git\technological_foods

# Remove from staging
git restore .claude/settings.local.json

# Add to .gitignore
echo '.claude/settings.local.json' >> .gitignore

# Commit the change
git add .gitignore
git commit -m 'chore: Prevent .claude/settings.local.json from being tracked'
```

## Acceptance Criteria
- [ ] `.claude/settings.local.json` not in `git status`
- [ ] File added to `.gitignore`
- [ ] Future changes to this file won't be tracked
- [ ] Clean git history

## Estimated Time
⏱️ 5 minutes

## Files Changed
- `.gitignore` (add entry)

## Verification
```bash
git status | grep settings.local.json
# Should return nothing
```

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- See: `IMMEDIATE_ACTIONS.md` Task 2
```

---

## <a name="issue-3-content"></a>Issue 3: Add business model tests

```markdown
## Problem
Core revenue system (`business_model.py`) has **NO automated tests**. This is the most critical business logic (€3,600/month revenue calculations) with zero test coverage.

## Impact
- ❌ Revenue calculations not verified
- ❌ Subscription tier limits not tested
- ❌ Client health scoring untested
- ❌ Risk of billing errors in production

## Required Tests

### 1. Subscription Tier Limits
- `test_bronze_tier_crop_limit()` - Verify 3 crop maximum
- `test_silver_tier_data_retention()` - Verify 30 day retention
- `test_platinum_unlimited_crops()` - Verify no crop limit

### 2. Revenue Calculations
- `test_monthly_revenue_calculation()` - MRR = sum of active clients
- `test_annual_revenue_projection()` - ARR = MRR × 12
- `test_inactive_client_exclusion()` - Inactive clients excluded

### 3. Client Health Score
- `test_sensor_drift_reduces_health()` - Drift = -10 points
- `test_calibration_overdue_reduces_health()` - Overdue = -15 points
- `test_multiple_issues_compound()` - Issues stack

### 4. Upselling Triggers
- `test_client_at_tier_limit_triggers_upsell()` - Recommend upgrade
- `test_no_upsell_when_under_limit()` - No upsell when under limit

## Implementation
See full test code template in `IMMEDIATE_ACTIONS.md` Task 3.

## Acceptance Criteria
- [ ] `test_business_model.py` created with 15+ tests
- [ ] All tests passing
- [ ] Code coverage >95% for business_model.py
- [ ] Tests cover: tiers, revenue, health, upselling

## Estimated Time
⏱️ 2 hours

## Files Changed
- `backend/api/test_business_model.py` (create)
- `backend/api/business_model.py` (fix bugs found by tests)

## Verification
```bash
cd backend/api
python -m pytest test_business_model.py -v
# Expected: 15 passed in 2.34s
```

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE (most critical)
- See: `IMMEDIATE_ACTIONS.md` Task 3 for full test template
```

---

## <a name="issue-4-content"></a>Issue 4: Replace placeholder phone numbers

```markdown
## Problem
Production code contains placeholder phone numbers that won't work in production.

## Current Code
```python
# backend/api/tier_notification_router.py:150
recommended_action = 'Call 24/7 support: +351-XXX-XXXX'
```

## Impact
- ❌ Broken support contact information
- ❌ Customers can't reach emergency support
- ❌ Unprofessional placeholder in production

## Solution Options

### Option A: Use environment variables (RECOMMENDED)
```python
# tier_notification_router.py
support_phone = os.getenv('SUPPORT_PHONE_GOLD', 'Contact your account manager')
recommended_action = f'Call 24/7 support: {support_phone}'
```

### Option B: Remove until service ready
```python
recommended_action = 'Your dedicated account manager will contact you shortly.'
```

## Acceptance Criteria
- [ ] No 'XXX-XXXX' in codebase
- [ ] Support contact info uses env vars or generic message
- [ ] `.env.example` documents required phone numbers

## Estimated Time
⏱️ 30 minutes

## Verification
```bash
grep -r 'XXX-XXXX' backend/
# Should return nothing
```

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- See: `IMMEDIATE_ACTIONS.md` Task 4
```

---

## <a name="issue-5-content"></a>Issue 5: Strengthen API keys

```markdown
## Problem
`backend/.env.example` contains weak, easily guessable default passwords.

## Current Configuration
```bash
INFLUXDB_PASSWORD=agritech2026          # ❌ Weak
API_KEY=agritech-secret-key-2026        # ❌ Predictable
GRAFANA_PASSWORD=agritech2026           # ❌ Common
```

## Solution
```bash
# Add security header to .env.example:
# ==========================================
# SECURITY CONFIGURATION
# 🔐 Generate unique random keys per environment
# 🔐 Commands:
#   API_KEY=$(openssl rand -hex 32)
#   INFLUXDB_PASSWORD=$(openssl rand -base64 16)
# ==========================================

INFLUXDB_PASSWORD=CHANGE_ME
API_KEY=CHANGE_ME
GRAFANA_PASSWORD=CHANGE_ME
```

## Acceptance Criteria
- [ ] No weak passwords in `.env.example`
- [ ] All keys use `CHANGE_ME` placeholder
- [ ] Header explains key generation

## Estimated Time
⏱️ 10 minutes

## Verification
```bash
grep 'agritech2026' backend/.env.example
# Should return nothing
```

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- See: `IMMEDIATE_ACTIONS.md` Task 5
```

---

## <a name="epic-content"></a>Epic: Code Quality & Test Coverage

```markdown
## Epic Overview
**Goal:** Fix critical issues preventing merge of `feature/dashboard` → `dev`

**Priority:** 🔴 P0 - CRITICAL (Blocking merge)

**Total Estimated Time:** 8 hours

## Epic Status
- [ ] #[X] Fix pytest collection error (30 min)
- [ ] #[X] Remove local settings (5 min)
- [ ] #[X] Add business model tests (2 hours) **← Most Critical**
- [ ] #[X] Replace placeholder phone numbers (30 min)
- [ ] #[X] Strengthen API key configuration (10 min)

## Success Criteria
When all 5 issues are complete:
- ✅ pytest collects 148 tests
- ✅ test_business_model.py has 15+ passing tests
- ✅ No 'XXX-XXXX' placeholders
- ✅ No weak passwords in .env.example
- ✅ Clean git status
- ✅ Pull request ready

## Timeline
**Target:** Complete today (2026-02-09)

**Critical Path:** Issue #[X] (business model tests) takes longest (2 hours)

## Related Documents
- `CODE_REVIEW_feature-dashboard.md` - Full technical review
- `IMMEDIATE_ACTIONS.md` - Step-by-step instructions
- `PRODUCT_BACKLOG.md` - Full backlog

## Impact
**Blocking:** Cannot merge 119 files (25,581 insertions) until complete

**Revenue Impact:** Delays SaaS platform launch (€3,600/month potential)
```

---

## 📊 Issue Labels to Create

If labels don't exist, create them on GitHub:

| Label | Color | Description |
|-------|-------|-------------|
| `P0` | `#d73a4a` (red) | Critical - Blocking merge |
| `P1` | `#ff9800` (orange) | High priority - Pre-production |
| `P2` | `#ffd700` (yellow) | Medium priority - Launch ready |
| `P3` | `#00ff00` (green) | Low priority - Future |
| `blocking` | `#b60205` (dark red) | Blocks other work |
| `epic` | `#0e8a16` (green) | Epic tracking issue |
| `testing` | `#1d76db` (blue) | Test coverage |
| `security` | `#d93f0b` (orange) | Security issue |
| `business-logic` | `#5319e7` (purple) | Core business logic |

---

## ✅ Next Steps

1. Choose an option above (automated, manual, or web UI)
2. Create all 6 issues
3. Start working on issues in this order:
   - Issue 2 (5 min) - Quick win
   - Issue 5 (10 min) - Quick win
   - Issue 1 (30 min) - Unblock testing
   - Issue 4 (30 min) - Clean up
   - **Issue 3 (2 hours) - Most critical**

4. Track progress in the epic issue
5. When all complete, merge to dev! 🚀

---

**Questions?** See `IMMEDIATE_ACTIONS.md` for detailed step-by-step instructions.
