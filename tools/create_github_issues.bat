@echo off
REM Create GitHub Issues for P0: Code Quality & Test Coverage
REM Run this script after installing GitHub CLI: https://cli.github.com/

echo Creating P0 Critical Issues for feature/dashboard merge...
echo.

REM Check if gh CLI is installed
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: GitHub CLI not found!
    echo.
    echo Please install GitHub CLI first:
    echo   1. Download from: https://cli.github.com/
    echo   2. Or run: winget install --id GitHub.cli
    echo   3. Then run: gh auth login
    echo.
    pause
    exit /b 1
)

echo Creating Issue 1: Fix pytest collection error...
gh issue create --title "🔴 P0: Fix pytest collection error (test_real_notification.py)" --body "## Problem%n`test_real_notification.py` uses `sys.exit(1)` which kills pytest collection.%n%nSee GITHUB_ISSUES_GUIDE.md for full details." --label "P0,bug,testing,blocking" --assignee @me
echo ✅ Issue 1 created
echo.

echo Creating Issue 2: Remove local settings...
gh issue create --title "🔴 P0: Remove .claude/settings.local.json from version control" --body "## Problem%n.claude/settings.local.json should be gitignored.%n%nSee GITHUB_ISSUES_GUIDE.md for full details." --label "P0,chore,security,blocking" --assignee @me
echo ✅ Issue 2 created
echo.

echo Creating Issue 3: Add business model tests...
gh issue create --title "🔴 P0: Add comprehensive tests for business_model.py" --body "## Problem%nCore revenue system has NO automated tests.%n%nSee GITHUB_ISSUES_GUIDE.md and IMMEDIATE_ACTIONS.md for full test template." --label "P0,testing,business-logic,blocking" --assignee @me
echo ✅ Issue 3 created
echo.

echo Creating Issue 4: Replace placeholder phone numbers...
gh issue create --title "🔴 P0: Replace placeholder phone numbers (+351-XXX-XXXX)" --body "## Problem%nProduction code has placeholder phone numbers.%n%nSee GITHUB_ISSUES_GUIDE.md for full details." --label "P0,bug,production-ready,blocking" --assignee @me
echo ✅ Issue 4 created
echo.

echo Creating Issue 5: Strengthen API keys...
gh issue create --title "🔴 P0: Strengthen API key configuration (remove weak defaults)" --body "## Problem%n.env.example has weak default passwords.%n%nSee GITHUB_ISSUES_GUIDE.md for full details." --label "P0,security,configuration,blocking" --assignee @me
echo ✅ Issue 5 created
echo.

echo Creating Epic Issue...
gh issue create --title "🎯 EPIC: Code Quality & Test Coverage (P0 - BLOCKING MERGE)" --body "## Epic Overview%nFix 5 critical issues blocking merge to dev.%n%nTotal Estimated Time: 8 hours%n%nSee GITHUB_ISSUES_GUIDE.md for full details." --label "P0,epic,blocking" --assignee @me
echo ✅ Epic issue created
echo.

echo 🎉 All 6 GitHub issues created successfully!
echo.
echo View all issues: gh issue list --label P0
echo Or visit: https://github.com/t0118430/technological_foods/issues
echo.
pause
