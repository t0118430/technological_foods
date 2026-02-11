# CI/CD Pipeline — What's Implemented

**Date**: 2026-02-10
**Status**: Implemented, pending branch protection configuration

---

## Summary

The CI/CD pipeline was redesigned to enforce PR-gated, hardware-targeted deployments. Three separate workflow files (`deploy-server-pi.yml`, `deploy-arduino-ota.yml`, `test-backend.yml`) were consolidated into two purpose-driven workflows.

## Before vs After

### Before (problems)

| Workflow | Trigger | Issues |
|----------|---------|--------|
| `deploy-server-pi.yml` | Push to master | No PR gate. rsync'd **entire repo** to Pi. |
| `deploy-arduino-ota.yml` | Push to master | No PR gate. No separation from backend. |
| `test-backend.yml` | Push/PR | Good but no arduino validation. No deployment preview. |

### After (current)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `pr-checks.yml` | PR to master | Gate: runs relevant checks based on what changed, posts deployment preview |
| `deploy.yml` | Push to master | Deploy: detects changes, deploys only affected targets selectively |

Unchanged:
- `sonarqube-analysis.yml` — Code quality on push/PR
- `test-hello-world.yml` — Pipeline verification

---

## Workflow: `pr-checks.yml`

**File**: `.github/workflows/pr-checks.yml`
**Trigger**: `pull_request` to `master`

### Job graph

```
detect-changes
    |
    +-- deployment-preview    (always — comments on PR)
    |
    +-- lint-and-validate     (if backend/** changed)
    |       |
    |       +-- unit-tests
    |       |       |
    |       |       +-- integration-tests
    |       |
    |       +-- docker-build
    |       |
    |       +-- security-scan
    |
    +-- arduino-build         (if arduino/** changed)
    |
    +-- check-summary         (always — aggregates, fails if anything failed)
```

### Change detection

Uses `dorny/paths-filter@v3` with three filters:
- `backend` — matches `backend/**`
- `arduino` — matches `arduino/**`
- `infra` — matches `infra/**`

### Deployment preview

On every PR, posts/updates a comment like:

```markdown
## Deployment Preview
This PR will deploy to:
- [x] **Raspberry Pi** (backend)
- [ ] **Raspberry Pi** (infra) -- no changes
- [ ] **Arduino** (firmware) -- no changes
```

Uses `actions/github-script@v7` to create or update the comment (avoids duplicate comments on re-push).

### Backend checks (conditional)

Only run when `backend/**` files changed. Carried over from the old `test-backend.yml`:

| Job | What it does |
|-----|-------------|
| lint-and-validate | JSON config validation, Python syntax, OpenAPI spec |
| unit-tests | pytest with coverage, parallel execution via pytest-xdist |
| integration-tests | Live InfluxDB service container, starts API server, runs test_integration.py |
| docker-build | Validates docker-compose configuration |
| security-scan | `safety` vulnerability check + `bandit` static analysis |

### Arduino build check (conditional)

Only runs when `arduino/**` files changed. Compiles the sketch with `arduino-cli` using `--warnings all` to catch issues before merge.

### Check summary

Runs always. Evaluates which checks were expected and whether they passed. Fails the workflow if any relevant check failed — this is the job branch protection should require.

---

## Workflow: `deploy.yml`

**File**: `.github/workflows/deploy.yml`
**Trigger**: `push` to `master` + `workflow_dispatch`

### Job graph

```
detect-changes
    |
    +-- deploy-backend   (if backend == true || infra == true)
    |
    +-- deploy-arduino   (if arduino == true)
    |
    +-- notify           (always — deployment summary)
```

### deploy-backend

Steps:
1. Checkout + Python setup
2. **Quick sanity tests** — py_compile, JSON validation, pytest (non-blocking)
3. Validate docker-compose
4. **SSH setup** — writes PI_SSH_KEY, adds host to known_hosts
5. **Create backup** — runs `./deploy/backup.sh pre-deploy` on Pi
6. **Selective rsync** — syncs only `backend/` and/or `infra/` (not entire repo)
7. **Restart services** — docker-compose pull/up, systemctl restart
8. **Health check** — runs `./deploy/health-check.sh` on Pi
9. **Rollback on failure** — restores from backup, restarts services
10. **ntfy notification** — success or failure

Key fix — selective rsync:
```bash
# Before (bad): rsync -avz . pi@host:/path/
# After (good):
rsync -avz backend/ pi@host:/path/backend/
rsync -avz infra/ pi@host:/path/infra/
```

### deploy-arduino

Steps:
1. Setup arduino-cli + core + libraries
2. **Build firmware** with `--warnings all`
3. Calculate SHA256 checksum
4. Upload artifact (retained 30 days)
5. **OTA deploy** via `deploy_ota.py`
6. **Verify** — wait 10s, check health endpoint
7. **GitHub release** — creates tag `arduino-v{version}` with firmware binary
8. **ntfy notification**

### notify

Runs always. Builds a summary of what was deployed and the status of each job. Sends a single ntfy notification with the full picture.

---

## Secrets Required

| Secret | Used by | Description |
|--------|---------|-------------|
| `PI_SSH_KEY` | deploy-backend | SSH private key for Pi access |
| `PI_HOST` | deploy-backend | Pi hostname or IP |
| `PI_USER` | deploy-backend | SSH username |
| `PI_PROJECT_PATH` | deploy-backend | Project directory on Pi |
| `ARDUINO_IP` | deploy-arduino | Arduino IP address |
| `ARDUINO_OTA_PASSWORD` | deploy-arduino | OTA password |
| `NTFY_TOPIC_URL` | deploy-backend, deploy-arduino, notify | ntfy endpoint |
| `GITHUB_TOKEN` | deploy-arduino | Auto-provided, for GitHub releases |

---

## What Still Needs Manual Setup

### Branch protection rules

Must be configured on GitHub (Settings > Branches > Add rule for `master`):

- See [BRANCH_PROTECTION_SETUP.md](./BRANCH_PROTECTION_SETUP.md) for step-by-step instructions

### Verification checklist

- [ ] Create test branch, change a backend file, open PR — only backend checks run
- [ ] Change an Arduino file in same PR — Arduino build check also runs
- [ ] PR comment shows deployment targets
- [ ] Merge PR — only backend deploys to Pi, Arduino deploys OTA
- [ ] Health check passes — ntfy success notification
- [ ] Direct push to master — blocked by branch protection
