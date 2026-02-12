# CI/CD & DevOps Improvements Roadmap

**Date**: 2026-02-10
**Current state**: PR-gated pipeline with selective deployment implemented

---

## Priority Legend

| Priority | Meaning | Timeframe |
|----------|---------|-----------|
| P0 | Critical — do now | This week |
| P1 | High — do soon | Next 2 weeks |
| P2 | Medium — plan for | Next month |
| P3 | Low — nice to have | Backlog |

---

## P0 — Critical (This Week)

### Configure branch protection on GitHub
**Status**: Not yet done (manual step)
**Impact**: Without this, direct pushes to `master` still bypass PR checks

See [BRANCH_PROTECTION_SETUP.md](./BRANCH_PROTECTION_SETUP.md) for instructions.

### Validate pipeline end-to-end
**Status**: Not yet tested
**Impact**: Pipeline logic is in place but hasn't run in production

Test plan:
1. Create a test branch, change a backend file, open PR
2. Verify only backend checks run
3. Verify deployment preview comment appears
4. Merge, verify only backend deploys
5. Repeat with an arduino-only change

---

## P1 — High Priority (Next 2 Weeks)

### Fix integration tests to be blocking
**What**: Remove `|| true` / `continue-on-error` patterns from test steps in `deploy.yml`
**Why**: The deploy-backend job runs `pytest ... || true` as a "sanity check" — this means broken tests don't prevent deployment. In `pr-checks.yml` the tests are already blocking, but the deploy job's sanity check should either be blocking or removed entirely.
**Action**: Either make the sanity tests in `deploy.yml` blocking (remove `|| true`) or remove them since `pr-checks.yml` already validates before merge.

### Add `deploy/**` and `docker-compose*` to change detection
**What**: Changes to deploy scripts and docker-compose files should trigger Pi deployment
**Why**: If `deploy/health-check.sh` or `backend/docker-compose.yml` changes, the Pi needs the updated files
**Action**: Add these paths to the `dorny/paths-filter` backend filter in both workflows:
```yaml
backend:
  - 'backend/**'
  - 'deploy/**'
infra:
  - 'infra/**'
```

### Upgrade deprecated actions
**What**: Some workflows still reference `actions/upload-artifact@v3` and `actions/setup-python@v4`
**Why**: v3 of upload-artifact is deprecated, v4 is current. setup-python@v5 is latest.
**Action**: Audit all workflows, bump to latest stable versions.

### Add concurrency control
**What**: Prevent multiple deployments from running simultaneously
**Why**: If two PRs merge in quick succession, two deploy runs could conflict on the Pi
**Action**: Add concurrency groups to `deploy.yml`:
```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false  # don't cancel in-progress deploys
```

---

## P2 — Medium Priority (Next Month)

### Staging environment
**What**: Add a staging Pi (or Docker environment) for pre-production testing
**Why**: Currently there's only production — changes go directly to the live Pi
**How**:
- Add a `deploy-staging` job that deploys to a staging Pi before production
- Or use Docker Compose locally to simulate the Pi environment
- Gate production deploy on staging health check passing

### Smoke tests after deployment
**What**: Run a quick functional test against the live Pi after deployment
**Why**: Health check only validates services are running, not that the API behaves correctly
**How**:
- After `deploy-backend`, SSH to Pi and run a few curl commands
- Verify: POST sensor data, GET latest data, check alert triggers
- Fail and rollback if smoke tests fail

### Cache dependencies in CI
**What**: Cache pip packages and arduino-cli cores between workflow runs
**Why**: Each run currently re-downloads everything, adding 1-2 minutes
**How**:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('backend/api/requirements.txt') }}
```
Same for arduino-cli cores and libraries.

### Arduino deploy via Pi intermediary
**What**: Route Arduino OTA through the Pi instead of directly from GitHub Actions
**Why**: Arduino may not be reachable from the internet. Pi is on the same LAN.
**How**: In `deploy-arduino`, after building firmware:
```bash
scp build/arduino/*.bin pi@host:/tmp/
ssh pi@host "cd /path/arduino/ota-tools && python deploy_ota.py --firmware /tmp/firmware.bin"
```

### Per-environment secrets
**What**: Separate secrets for staging vs production
**Why**: Avoid accidentally deploying to production when testing
**How**: Use GitHub Environments feature:
- Create `staging` and `production` environments
- Move secrets into environments
- Reference in workflow: `environment: production`

---

## P3 — Backlog (Future)

### Blue-green deployment for backend
**What**: Deploy new version alongside old, switch traffic after health check
**Why**: Zero downtime deployments. Current approach has ~10-30s downtime during restart.
**How**:
- Run two API instances behind nginx on Pi
- Deploy to inactive instance
- Switch nginx upstream after health check
- Requires nginx config management on Pi

### Canary deployment for Arduino
**What**: If multiple Arduino devices, deploy to one first, monitor, then deploy to all
**Why**: Firmware bugs can brick devices — test on one before fleet rollout
**Prerequisite**: Multiple Arduino devices

### Automated rollback on metric degradation
**What**: Monitor error rates/latency after deploy, auto-rollback if degraded
**Why**: Health check only catches hard failures, not performance regressions
**How**:
- After deploy, query InfluxDB/Grafana for error rate
- Compare to pre-deploy baseline
- Trigger rollback if >5% error rate increase

### Pipeline performance dashboard
**What**: Track build times, success rates, deployment frequency
**Why**: DORA metrics — measure DevOps performance over time
**How**:
- GitHub Actions provides run duration data via API
- Send metrics to InfluxDB, visualize in Grafana
- Or use GitHub's built-in Actions insights

### Notifications with deployment diff
**What**: Include a summary of what changed in the ntfy notification
**Why**: "Backend deployed" is less useful than "Backend deployed: updated rule_engine.py, fixed pH threshold"
**How**: In the notify job, extract commit messages since last deploy and include in notification body.

### Matrix builds for multiple Arduino boards
**What**: Compile firmware for multiple board types in parallel
**Why**: Future-proofing for when the project supports different hardware
**How**: GitHub Actions matrix strategy with different FQBN values.

### Scheduled health monitoring
**What**: Run health checks on the Pi on a cron schedule, not just after deploys
**Why**: Detect issues that develop between deployments (disk full, service crash)
**How**: Add a scheduled workflow:
```yaml
on:
  schedule:
    - cron: '*/30 * * * *'  # every 30 minutes
```

### Infrastructure as Code for Pi setup
**What**: Automate Pi provisioning with Ansible or shell scripts checked into repo
**Why**: Currently Pi setup is manual. If the Pi dies, rebuild is manual.
**How**: Create `infra/ansible/` playbooks or enhance `deploy/setup-pi.sh` to be fully idempotent.

---

## Anti-Patterns to Avoid

### Don't add Kubernetes
The current scale (1 Pi, 1 Arduino, <200 sensors) does not justify Kubernetes. Docker Compose + systemd is the right tool. See [INTEGRATION_TESTS_AND_DEPLOYMENT_STRATEGY.md](../INTEGRATION_TESTS_AND_DEPLOYMENT_STRATEGY.md) for the full analysis.

### Don't over-abstract the pipeline
Keep workflows readable. One `deploy.yml` with clear conditional jobs is better than a chain of reusable workflows calling each other. Abstraction costs readability.

### Don't deploy docs changes
Documentation-only PRs should not trigger any deployment. The current path filters already handle this — only `backend/**`, `arduino/**`, `infra/**` trigger deploys.

### Don't test in production
Even though the Pi is "production", don't skip PR checks. The integration tests in `pr-checks.yml` use service containers (InfluxDB) to simulate the production environment. Fix tests instead of bypassing them.

---

## Measuring Success

Track these after implementing improvements:

| Metric | Current (estimate) | Target |
|--------|-------------------|--------|
| Deploy frequency | Ad-hoc pushes to master | 2-5 PRs merged/week |
| Lead time (commit to production) | Minutes (no gate) | <30 minutes (with PR review) |
| Change failure rate | Unknown | <10% |
| Mean time to recovery | Manual intervention | <5 minutes (auto-rollback) |
| Pipeline pass rate | Unknown | >90% |
| Build time (PR checks) | ~5 minutes | <5 minutes |
| Deploy time | ~5-8 minutes | <5 minutes (with caching) |
