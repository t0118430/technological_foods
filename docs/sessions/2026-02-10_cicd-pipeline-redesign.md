# Session: CI/CD Pipeline Redesign — PR-Gated, Hardware-Targeted Deployments

**Date**: 2026-02-10
**Branch**: `fix/pipeline/notificatidashboard`

---

## What Was Done

### 1. Replaced 3 workflow files with 2 unified ones

**Deleted:**
- `.github/workflows/deploy-server-pi.yml` — deployed entire repo via rsync on push to master
- `.github/workflows/deploy-arduino-ota.yml` — deployed arduino on push to master
- `.github/workflows/test-backend.yml` — ran backend tests on push/PR

**Created:**
- `.github/workflows/deploy.yml` — unified deployment pipeline triggered on push to master
- `.github/workflows/pr-checks.yml` — PR gate with conditional checks and deployment preview

**Unchanged:**
- `sonarqube-analysis.yml`
- `test-hello-world.yml`

### 2. Key improvements in the new pipeline

- **PR gate**: All code must go through a PR before reaching `master`
- **Change detection**: `dorny/paths-filter@v3` detects which directories changed (`backend/**`, `arduino/**`, `infra/**`)
- **Selective deployment**: Only changed components deploy to their target hardware
- **Targeted rsync**: Backend deploy now syncs only `backend/` and `infra/` (not the entire repo)
- **Deployment preview**: PR comment showing exactly what will deploy where
- **Conditional checks**: Backend tests only run when backend changes, Arduino compile only when arduino changes
- **Summary job**: `check-summary` aggregates all conditional checks — single job for branch protection to require

### 3. Created CI/CD documentation

| File | Content |
|------|---------|
| `docs/devops/cicd/CURRENT_PIPELINE.md` | Full breakdown of what's implemented — job graphs, change detection, selective rsync, secrets reference, verification checklist |
| `docs/devops/cicd/BRANCH_PROTECTION_SETUP.md` | Step-by-step GitHub branch protection configuration guide |
| `docs/devops/cicd/IMPROVEMENTS_ROADMAP.md` | Prioritized roadmap (P0-P3) with 15+ improvements and DORA metrics targets |

### 4. Updated existing workflow documentation

| File | Changes |
|------|---------|
| `.github/workflows/README.md` | Rewritten to reflect new pipeline structure, cross-linked to new docs |
| `.github/workflows/DEPLOYMENT_STRATEGY.md` | Rewritten with PR gate, selective rsync, deployment scenarios |

---

## Pipeline Architecture (after)

```
feature branch
    |
    v
PR to master → pr-checks.yml
    |
    +-- detect-changes (dorny/paths-filter)
    +-- deployment-preview (PR comment)
    +-- backend checks (conditional: lint, unit, integration, docker, security)
    +-- arduino build (conditional: compile check)
    +-- check-summary (aggregates, gates merge)
    |
    v
Merge → deploy.yml
    |
    +-- detect-changes
    +-- deploy-backend (if backend/infra changed) → selective rsync to Pi
    +-- deploy-arduino (if arduino changed) → OTA to Arduino
    +-- notify (summary via ntfy)
```

---

## Still TODO (manual steps)

1. **Configure branch protection on GitHub** — require `PR Check Summary` status check, require 1 approval, block direct pushes (see `BRANCH_PROTECTION_SETUP.md`)
2. **Run end-to-end validation** — open a test PR to verify the pipeline works
3. **Review P1 improvements** in `IMPROVEMENTS_ROADMAP.md` — blocking integration tests, change detection gaps, action version upgrades

---

## Files Changed in This Session

### Created
- `.github/workflows/deploy.yml`
- `.github/workflows/pr-checks.yml`
- `docs/devops/cicd/CURRENT_PIPELINE.md`
- `docs/devops/cicd/BRANCH_PROTECTION_SETUP.md`
- `docs/devops/cicd/IMPROVEMENTS_ROADMAP.md`

### Modified
- `.github/workflows/README.md`
- `.github/workflows/DEPLOYMENT_STRATEGY.md`

### Deleted (via git rm)
- `.github/workflows/deploy-server-pi.yml`
- `.github/workflows/deploy-arduino-ota.yml`
- `.github/workflows/test-backend.yml`
