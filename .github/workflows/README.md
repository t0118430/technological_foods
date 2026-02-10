# AgriTech CI/CD Pipeline

## Overview

PR-gated, hardware-targeted CI/CD pipeline for the AgriTech Hydroponics Platform. All changes to `master` require a pull request with passing checks before merge. Deployments are selective — only changed components deploy to their respective hardware targets.

## Workflows

### 1. `pr-checks.yml` — PR Gate (required before merge)

**Trigger**: Pull request to `master`

Detects which directories changed and runs only the relevant checks:

| Job | Runs when | What it does |
|-----|-----------|-------------|
| `detect-changes` | Always | Uses `dorny/paths-filter` to detect `backend/**`, `arduino/**`, `infra/**` changes |
| `deployment-preview` | Always | Comments on the PR showing what will deploy where |
| `lint-and-validate` | `backend/**` changed | JSON config validation, Python syntax, OpenAPI spec |
| `unit-tests` | `backend/**` changed | pytest with coverage |
| `integration-tests` | `backend/**` changed | Tests with live InfluxDB service container |
| `docker-build` | `backend/**` changed | Validates docker-compose config |
| `security-scan` | `backend/**` changed | safety + bandit vulnerability checks |
| `arduino-build` | `arduino/**` changed | Compiles sketch to validate firmware builds |
| `check-summary` | Always | Aggregates results, fails if any relevant check failed |

### 2. `deploy.yml` — Deployment (after PR merge)

**Trigger**: Push to `master` (only happens via approved PR merge)

```
detect-changes
    |
    +-- deploy-backend  (if backend/** or infra/** changed)
    |       SSH backup -> selective rsync -> restart services -> health check -> rollback on failure
    |
    +-- deploy-arduino  (if arduino/** changed)
    |       Build firmware -> OTA deploy -> verify -> GitHub release
    |
    +-- notify  (always)
            Summary of what deployed and status
```

Key improvement: **rsync is now targeted** — only `backend/` and `infra/` are synced to the Pi, not the entire repo.

### 3. `sonarqube-analysis.yml` — Code Quality (unchanged)

**Trigger**: Push to `master` or `feature/**`, PRs to `master`

Runs SonarQube analysis with coverage, pylint, and bandit reports.

### 4. `test-hello-world.yml` — Pipeline Verification (unchanged)

**Trigger**: Push to `feature/ci-cd-pipeline` or `master`

Quick sanity check that GitHub Actions is working.

## Pipeline Flow

```
feature branch
    |
    v
Open PR to master
    |
    v
pr-checks.yml runs  ─────────────────────────>  Deployment preview
    |                                             comment on PR
    +-- backend checks (if backend changed)
    +-- arduino build (if arduino changed)
    +-- check-summary (must pass)
    |
    v
Reviewer approves PR
    |
    v
Merge to master
    |
    v
deploy.yml runs
    |
    +-- deploy-backend (selective rsync to Pi)
    +-- deploy-arduino (OTA to Arduino)
    +-- notify (ntfy summary)
```

## Deployment Preview

When a PR is opened, a comment is automatically posted:

```
## Deployment Preview
This PR will deploy to:
- [x] Raspberry Pi (backend)
- [ ] Raspberry Pi (infra) -- no changes
- [ ] Arduino (firmware) -- no changes
```

This comment updates on each push to the PR branch.

## GitHub Secrets Required

### Raspberry Pi
| Secret | Description | Example |
|--------|-------------|---------|
| `PI_SSH_KEY` | SSH private key | ed25519 key |
| `PI_HOST` | Pi hostname/IP | `192.168.1.10` |
| `PI_USER` | SSH username | `pi` |
| `PI_PROJECT_PATH` | Project path on Pi | `/home/pi/technological_foods` |

### Arduino
| Secret | Description | Example |
|--------|-------------|---------|
| `ARDUINO_IP` | Arduino IP address | `192.168.1.100` |
| `ARDUINO_OTA_PASSWORD` | OTA password | (optional) |

### Notifications
| Secret | Description | Example |
|--------|-------------|---------|
| `NTFY_TOPIC_URL` | ntfy topic URL | `https://ntfy.sh/techfoods` |

## Rollback

### Automatic
If the health check fails after backend deployment, the pipeline automatically restores from the pre-deploy backup and restarts services.

### Manual
```bash
ssh pi@<pi-ip>
cd /path/to/technological_foods
./deploy/restore.sh pre-deploy
sudo systemctl restart agritech-api.service
cd backend && docker-compose restart
```

## Local Testing with `act`

```bash
# Run PR checks
act pull_request -W .github/workflows/pr-checks.yml

# Run deploy (simulated)
act push -W .github/workflows/deploy.yml
```

## Related Documentation

- [CI/CD Current Pipeline](../../docs/devops/cicd/CURRENT_PIPELINE.md) — Detailed breakdown of what's implemented
- [CI/CD Improvements Roadmap](../../docs/devops/cicd/IMPROVEMENTS_ROADMAP.md) — Strategy for pipeline improvements
- [Branch Protection Setup](../../docs/devops/cicd/BRANCH_PROTECTION_SETUP.md) — How to configure GitHub branch rules
- [Deployment Strategy](./DEPLOYMENT_STRATEGY.md) — Two-tier hardware deployment architecture
- [DevOps Deployment Guide](../../docs/devops/DEVOPS_DEPLOYMENT_GUIDE.md) — Full Pi setup and operations guide

---

**Last Updated**: 2026-02-10
