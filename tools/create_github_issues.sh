#!/bin/bash
# Create GitHub Issues for P0: Code Quality & Test Coverage
# Run this script after installing GitHub CLI: https://cli.github.com/

set -e

echo "Creating P0 Critical Issues for feature/dashboard merge..."

# Issue 1: Fix pytest collection error
gh issue create \
  --title "🔴 P0: Fix pytest collection error (test_real_notification.py)" \
  --body "## Problem
\`test_real_notification.py\` uses \`sys.exit(1)\` which kills pytest collection when InfluxDB is unavailable.

## Current Error
\`\`\`bash
cd backend/api && python -m pytest --collect-only
# INTERNALERROR: SystemExit: 1
# no tests ran in 0.45s
\`\`\`

## Impact
- ❌ Blocks all test execution
- ❌ Breaks CI/CD pipeline
- ❌ Cannot verify code quality

## Solution Options

### Option A: Move to scripts directory (RECOMMENDED)
\`\`\`bash
cd backend
git mv test_real_notification.py scripts/manual_test_notification.py
\`\`\`

### Option B: Use pytest.skip
\`\`\`python
# Replace lines 54-57 in test_real_notification.py:
if not real_sensor_data:
    pytest.skip('No data in InfluxDB - Arduino not running')
\`\`\`

## Acceptance Criteria
- [ ] \`pytest --collect-only\` shows 148 tests collected
- [ ] No \`sys.exit()\` calls in test files
- [ ] CI/CD pipeline runs successfully
- [ ] Test execution time < 60 seconds

## Estimated Time
⏱️ 30 minutes

## Files Changed
- \`backend/test_real_notification.py\` (delete or modify)
- \`backend/scripts/manual_test_notification.py\` (create if using Option A)

## Verification
\`\`\`bash
cd backend/api
python -m pytest --collect-only
# Expected: collected 148 items
\`\`\`

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- Estimated: 30 minutes
- See: \`IMMEDIATE_ACTIONS.md\` Task 1" \
  --label "P0,bug,testing,blocking" \
  --assignee @me

echo "✅ Issue 1 created: pytest collection error"

# Issue 2: Remove local settings from commit
gh issue create \
  --title "🔴 P0: Remove .claude/settings.local.json from version control" \
  --body "## Problem
Local configuration file \`.claude/settings.local.json\` is in the changeset and should be gitignored.

## Current Status
\`\`\`bash
git status
# modified: .claude/settings.local.json
\`\`\`

## Security Risk
- ⚠️ Local settings may contain sensitive paths
- ⚠️ Pollutes git history with developer-specific configs
- ⚠️ Could leak local environment details

## Solution
\`\`\`bash
cd C:\\git\\technological_foods

# Remove from staging
git restore .claude/settings.local.json

# Add to .gitignore
echo '.claude/settings.local.json' >> .gitignore

# Commit the change
git add .gitignore
git commit -m 'chore: Prevent .claude/settings.local.json from being tracked'
\`\`\`

## Acceptance Criteria
- [ ] \`.claude/settings.local.json\` not in \`git status\`
- [ ] File added to \`.gitignore\`
- [ ] Future changes to this file won't be tracked
- [ ] Clean git history

## Estimated Time
⏱️ 5 minutes

## Files Changed
- \`.gitignore\` (add entry)

## Verification
\`\`\`bash
git status | grep settings.local.json
# Should return nothing
\`\`\`

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- Estimated: 5 minutes
- See: \`IMMEDIATE_ACTIONS.md\` Task 2" \
  --label "P0,chore,security,blocking" \
  --assignee @me

echo "✅ Issue 2 created: Remove local settings"

# Issue 3: Add business model tests
gh issue create \
  --title "🔴 P0: Add comprehensive tests for business_model.py" \
  --body "## Problem
Core revenue system (\`business_model.py\`) has **NO automated tests**. This is the most critical business logic (€3,600/month revenue calculations) with zero test coverage.

## Impact
- ❌ Revenue calculations not verified
- ❌ Subscription tier limits not tested
- ❌ Client health scoring untested
- ❌ Risk of billing errors in production

## Required Tests

### 1. Subscription Tier Limits
\`\`\`python
def test_bronze_tier_crop_limit():
    \"\"\"Bronze tier can't exceed 3 crops\"\"\"
    # Test that 4th crop raises ValueError

def test_silver_tier_data_retention():
    \"\"\"Silver tier retains 30 days of data\"\"\"

def test_platinum_unlimited_crops():
    \"\"\"Platinum tier has no crop limit\"\"\"
\`\`\`

### 2. Revenue Calculations
\`\`\`python
def test_monthly_revenue_calculation():
    \"\"\"MRR = sum of all active client monthly fees\"\"\"
    # Bronze (€49) + Silver (€199) + Gold (€499) = €747

def test_annual_revenue_projection():
    \"\"\"ARR = MRR × 12\"\"\"

def test_inactive_client_exclusion():
    \"\"\"Inactive clients don't count toward revenue\"\"\"
\`\`\`

### 3. Client Health Score
\`\`\`python
def test_sensor_drift_reduces_health():
    \"\"\"Sensor drift detected → -10 points\"\"\"

def test_calibration_overdue_reduces_health():
    \"\"\"Calibration overdue → -15 points\"\"\"

def test_multiple_issues_compound():
    \"\"\"Multiple issues reduce health cumulatively\"\"\"
\`\`\`

### 4. Upselling Triggers
\`\`\`python
def test_client_at_tier_limit_triggers_upsell():
    \"\"\"Bronze client with 3 crops → recommend Silver\"\"\"

def test_no_upsell_when_under_limit():
    \"\"\"Bronze client with 1 crop → no upsell\"\"\"
\`\`\`

## Implementation Steps
1. Create \`backend/api/test_business_model.py\`
2. Copy test template from \`IMMEDIATE_ACTIONS.md\`
3. Run: \`pytest test_business_model.py -v\`
4. Fix any failing tests (may reveal bugs in business_model.py)
5. Ensure 15+ tests passing

## Acceptance Criteria
- [ ] \`test_business_model.py\` created with 15+ tests
- [ ] All tests passing
- [ ] Code coverage >95% for business_model.py
- [ ] Tests cover: tiers, revenue, health, upselling

## Estimated Time
⏱️ 2 hours

## Files Changed
- \`backend/api/test_business_model.py\` (create)
- \`backend/api/business_model.py\` (fix bugs found by tests)

## Verification
\`\`\`bash
cd backend/api
python -m pytest test_business_model.py -v
# Expected: 15 passed in 2.34s
\`\`\`

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE (most critical)
- Estimated: 2 hours
- See: \`IMMEDIATE_ACTIONS.md\` Task 3
- Template: See \`IMMEDIATE_ACTIONS.md\` for full test code" \
  --label "P0,testing,business-logic,blocking" \
  --assignee @me

echo "✅ Issue 3 created: Business model tests"

# Issue 4: Replace placeholder phone numbers
gh issue create \
  --title "🔴 P0: Replace placeholder phone numbers (+351-XXX-XXXX)" \
  --body "## Problem
Production code contains placeholder phone numbers that won't work in production.

## Current Code
\`\`\`python
# backend/api/tier_notification_router.py:150
recommended_action = 'Call 24/7 support: +351-XXX-XXXX'
\`\`\`

## Impact
- ❌ Broken support contact information
- ❌ Customers can't reach emergency support
- ❌ Unprofessional placeholder in production

## Solution Options

### Option A: Use environment variables (RECOMMENDED)
\`\`\`python
# tier_notification_router.py
support_phone = os.getenv('SUPPORT_PHONE_GOLD', 'Contact your account manager')
recommended_action = f'Call 24/7 support: {support_phone}'
\`\`\`

Then add to \`backend/.env.example\`:
\`\`\`bash
# Emergency Contact Numbers (configure before production)
# SUPPORT_PHONE_SILVER=
# SUPPORT_PHONE_GOLD=
# SUPPORT_PHONE_PLATINUM=
\`\`\`

### Option B: Remove until service ready (SIMPLER)
\`\`\`python
recommended_action = 'Your dedicated account manager will contact you shortly.'
\`\`\`

## Acceptance Criteria
- [ ] No 'XXX-XXXX' in codebase
- [ ] Support contact info uses env vars or generic message
- [ ] \`.env.example\` documents required phone numbers
- [ ] Documentation explains how to configure

## Estimated Time
⏱️ 30 minutes

## Files Changed
- \`backend/api/tier_notification_router.py\`
- \`backend/.env.example\`

## Verification
\`\`\`bash
grep -r 'XXX-XXXX' backend/
# Should return nothing
\`\`\`

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- Estimated: 30 minutes
- See: \`IMMEDIATE_ACTIONS.md\` Task 4" \
  --label "P0,bug,production-ready,blocking" \
  --assignee @me

echo "✅ Issue 4 created: Replace placeholder phone numbers"

# Issue 5: Strengthen API key configuration
gh issue create \
  --title "🔴 P0: Strengthen API key configuration (remove weak defaults)" \
  --body "## Problem
\`backend/.env.example\` contains weak, easily guessable default passwords.

## Current Configuration
\`\`\`bash
INFLUXDB_PASSWORD=agritech2026          # ❌ Weak - year pattern
API_KEY=agritech-secret-key-2026        # ❌ Predictable
GRAFANA_PASSWORD=agritech2026           # ❌ Common password
\`\`\`

## Security Risk
- ⚠️ Developers may copy .env.example → production with weak keys
- ⚠️ Keys follow predictable pattern (agritech + year)
- ⚠️ If leaked, system easily compromised

## Solution
Replace with \`CHANGE_ME\` placeholders + instructions:

\`\`\`bash
# ==========================================
# SECURITY CONFIGURATION
# ==========================================
# 🔐 NEVER commit .env files to git
# 🔐 Generate unique random keys per environment
# 🔐 Rotate API keys every 90 days
#
# Generate strong keys:
#   API_KEY=\$(openssl rand -hex 32)
#   INFLUXDB_TOKEN=\$(openssl rand -base64 32)
#   INFLUXDB_PASSWORD=\$(openssl rand -base64 16)
#   GRAFANA_PASSWORD=\$(openssl rand -base64 16)
# ==========================================

INFLUXDB_PASSWORD=CHANGE_ME  # Generate: openssl rand -base64 16
API_KEY=CHANGE_ME            # Generate: openssl rand -hex 32
GRAFANA_PASSWORD=CHANGE_ME   # Generate: openssl rand -base64 16
\`\`\`

## Acceptance Criteria
- [ ] No weak passwords in \`.env.example\`
- [ ] All sensitive keys use \`CHANGE_ME\` placeholder
- [ ] Header comment explains key generation
- [ ] Commands provided for generating strong keys
- [ ] Warning about not committing .env files

## Estimated Time
⏱️ 10 minutes

## Files Changed
- \`backend/.env.example\`

## Verification
\`\`\`bash
grep 'agritech2026' backend/.env.example
# Should return nothing

grep 'CHANGE_ME' backend/.env.example
# Should find API_KEY, passwords, etc.
\`\`\`

## Related
- Epic: Code Quality & Test Coverage (P0)
- Priority: 🔴 BLOCKING MERGE
- Estimated: 10 minutes
- See: \`IMMEDIATE_ACTIONS.md\` Task 5" \
  --label "P0,security,configuration,blocking" \
  --assignee @me

echo "✅ Issue 5 created: Strengthen API keys"

# Create Epic/Milestone Issue
gh issue create \
  --title "🎯 EPIC: Code Quality & Test Coverage (P0 - BLOCKING MERGE)" \
  --body "## Epic Overview
**Goal:** Fix critical issues preventing merge of \`feature/dashboard\` → \`dev\`

**Business Value:** Enable deployment of SaaS platform features

**Priority:** 🔴 P0 - CRITICAL (Blocking merge)

**Total Estimated Time:** 8 hours

## Epic Status
- [ ] Issue 1: Fix pytest collection error (30 min)
- [ ] Issue 2: Remove local settings (5 min)
- [ ] Issue 3: Add business model tests (2 hours) **← Most Critical**
- [ ] Issue 4: Replace placeholder phone numbers (30 min)
- [ ] Issue 5: Strengthen API key configuration (10 min)

## Success Criteria
When all 5 issues are complete:
- ✅ pytest collects 148 tests (no sys.exit errors)
- ✅ test_business_model.py has 15+ passing tests
- ✅ No 'XXX-XXXX' placeholder values in code
- ✅ No weak passwords in .env.example
- ✅ .claude/settings.local.json not in git status
- ✅ All 148 tests passing
- ✅ Pull request created and ready for review

## Timeline
**Target:** Complete today (2026-02-09)

**Critical Path:** Issue 3 (business model tests) takes longest (2 hours)

**Recommended Order:**
1. Issue 2 (5 min) - Quick win
2. Issue 5 (10 min) - Quick win
3. Issue 1 (30 min) - Unblock testing
4. Issue 4 (30 min) - Clean up placeholders
5. Issue 3 (2 hours) - Most critical, do last with full focus

## Related Documents
- \`CODE_REVIEW_feature-dashboard.md\` - Full technical review
- \`IMMEDIATE_ACTIONS.md\` - Step-by-step instructions
- \`PRE_MERGE_CHECKLIST.md\` - Verification checklist
- \`PRODUCT_BACKLOG.md\` - Full backlog (10 epics, 40 stories)

## After This Epic
Once merged to dev:
- Next: Epic 2 - Production Security (HTTPS, API key rotation)
- Then: Epic 3 - Database Scalability (PostgreSQL migration)
- Then: Epic 5 - Multi-Location Deployment (Porto → Lisbon → Algarve)

## Impact
**Blocking:** Cannot merge 119 files with 25,581 insertions until these 5 issues are fixed

**Revenue Impact:** Delays launch of SaaS platform (€3,600/month potential revenue)

## Team Notes
All 5 issues have detailed step-by-step instructions in \`IMMEDIATE_ACTIONS.md\`. Copy test templates directly from that file." \
  --label "P0,epic,blocking" \
  --assignee @me

echo "✅ Epic issue created"
echo ""
echo "🎉 All 6 GitHub issues created successfully!"
echo ""
echo "View all issues: gh issue list --label P0"
echo "Or visit: https://github.com/t0118430/technological_foods/issues"
