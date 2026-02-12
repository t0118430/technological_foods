# Branch Protection Setup

**Date**: 2026-02-10
**Status**: Manual configuration required on GitHub

---

## Why

The new pipeline (`deploy.yml`) triggers on push to `master`. Without branch protection, anyone can push directly to `master` and trigger a deployment without review. Branch protection ensures all changes go through a PR with passing checks first.

---

## Setup Steps

### 1. Navigate to branch protection settings

1. Go to your repository on GitHub
2. Click **Settings** (top right tab)
3. Click **Branches** (left sidebar under "Code and automation")
4. Click **Add branch protection rule** (or edit existing `master` rule)

### 2. Configure the rule

**Branch name pattern**: `master`

Check the following boxes:

#### Require a pull request before merging
- [x] **Require a pull request before merging**
  - [x] Require approvals: **1** (minimum)
  - [ ] Dismiss stale pull request approvals when new commits are pushed (optional but recommended)
  - [ ] Require review from Code Owners (optional, skip if you're the only contributor)

#### Require status checks to pass before merging
- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Search for and add these required status checks:
    - `PR Check Summary` (the `check-summary` job from `pr-checks.yml`)

> Note: The status check names appear after the first PR run. You may need to open one PR first, then come back and configure the required checks.

#### Block direct pushes
- [x] **Do not allow bypassing the above settings**
  - This prevents even admins from pushing directly to `master`

#### Optional settings
- [ ] Require signed commits (recommended if team uses GPG keys)
- [ ] Require linear history (keeps git log clean, prevents merge commits)
- [ ] Include administrators (recommended — ensures rules apply to everyone)

### 3. Save

Click **Create** (or **Save changes** if editing).

---

## Verification

After setting up branch protection:

1. Try pushing directly to `master`:
   ```bash
   git checkout master
   echo "test" >> test.txt
   git add test.txt
   git commit -m "test direct push"
   git push origin master
   ```
   **Expected**: Push rejected with error about branch protection.

2. Create a PR instead:
   ```bash
   git checkout -b test/branch-protection
   echo "test" >> test.txt
   git add test.txt
   git commit -m "test PR flow"
   git push origin test/branch-protection
   ```
   Open a PR on GitHub. Checks should run. After passing and getting approval, merge should work.

---

## Required Status Checks Reference

These are the job names from `pr-checks.yml` that can be set as required:

| Status check name | What it gates |
|-------------------|---------------|
| `PR Check Summary` | Aggregates all checks — **this is the one to require** |
| `Detect Changes` | Path filtering (always passes) |
| `Deployment Preview` | PR comment (always passes) |
| `Lint & Validate Configs` | Backend linting (conditional) |
| `Unit Tests` | Backend unit tests (conditional) |
| `Integration Tests` | Backend integration tests (conditional) |
| `Docker Build Test` | Docker validation (conditional) |
| `Security Scan` | Vulnerability checks (conditional) |
| `Arduino Build Check` | Firmware compilation (conditional) |

**Recommended**: Only require `PR Check Summary` — it already aggregates all the conditional checks and fails appropriately.

---

## Troubleshooting

### "Required status check not found"

Status checks only appear in the GitHub dropdown after they've run at least once. Open a test PR first, let `pr-checks.yml` run, then configure the required checks.

### "Branch protection prevents workflow_dispatch"

`workflow_dispatch` on `deploy.yml` still works — it's a manual trigger on the workflow itself, not a push to the branch. This is the escape hatch for manual deployments.

### "Admin can still push directly"

Make sure **"Do not allow bypassing the above settings"** is checked. Without it, repository admins can bypass the rules.
