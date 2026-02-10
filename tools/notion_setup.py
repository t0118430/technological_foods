"""
TechFoods Notion Workspace Builder
Creates the full project management workspace with Epics, Backlog, Sprints, and documentation.
"""
import requests
import json
import time
import sys

TOKEN = 'ntn_Z68536087907z6rxIVRCHFOcULs8slyt8XDzUe1dJiE2z7'
PARENT_PAGE_ID = '30319881-c556-803c-90e6-ef18eaf80c19'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}
API = 'https://api.notion.com/v1'

def api_call(method, endpoint, data=None, retries=3):
    """Make API call with rate limiting and retries."""
    for attempt in range(retries):
        time.sleep(0.35)  # Rate limit: ~3 req/s
        if method == 'POST':
            r = requests.post(f'{API}/{endpoint}', headers=HEADERS, json=data)
        elif method == 'PATCH':
            r = requests.patch(f'{API}/{endpoint}', headers=HEADERS, json=data)
        else:
            r = requests.get(f'{API}/{endpoint}', headers=HEADERS)

        if r.status_code == 429:
            wait = int(r.headers.get('Retry-After', 2))
            print(f'  Rate limited, waiting {wait}s...')
            time.sleep(wait)
            continue
        if r.status_code >= 400:
            print(f'  ERROR {r.status_code}: {r.json().get("message", "")}')
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return None
        return r.json()
    return None

def create_page(parent_id, title, children=None, icon=None):
    """Create a page under a parent."""
    data = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": [{"text": {"content": title}}]
        }
    }
    if icon:
        data["icon"] = {"type": "emoji", "emoji": icon}
    if children:
        data["children"] = children[:100]  # Notion limit: 100 blocks per request
    result = api_call('POST', 'pages', data)
    if result:
        print(f'  Created page: {title}')
        return result['id']
    return None

def append_blocks(page_id, blocks):
    """Append blocks to a page (max 100 at a time)."""
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        api_call('PATCH', f'blocks/{page_id}/children', {"children": chunk})

def heading(level, text):
    h = f'heading_{level}'
    return {"type": h, h: {"rich_text": [{"text": {"content": text}}]}}

def paragraph(text):
    if not text:
        return {"type": "paragraph", "paragraph": {"rich_text": []}}
    return {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]}}

def bulleted(text):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": text[:2000]}}]}}

def todo_item(text, checked=False):
    return {"type": "to_do", "to_do": {"rich_text": [{"text": {"content": text[:2000]}}], "checked": checked}}

def divider():
    return {"type": "divider", "divider": {}}

def callout(text, icon="💡"):
    return {"type": "callout", "callout": {"rich_text": [{"text": {"content": text[:2000]}}], "icon": {"type": "emoji", "emoji": icon}}}

def create_database(parent_id, title, properties, icon=None):
    """Create a database under a parent page."""
    data = {
        "parent": {"page_id": parent_id},
        "title": [{"text": {"content": title}}],
        "properties": properties
    }
    if icon:
        data["icon"] = {"type": "emoji", "emoji": icon}
    result = api_call('POST', 'databases', data)
    if result:
        print(f'  Created database: {title}')
        return result['id']
    return None

def add_db_item(database_id, properties):
    """Add an item to a database."""
    data = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    return api_call('POST', 'pages', data)

def title_prop(text):
    return {"title": [{"text": {"content": text[:2000]}}]}

def rich_text_prop(text):
    return {"rich_text": [{"text": {"content": text[:2000]}}]}

def select_prop(name):
    return {"select": {"name": name}}

def number_prop(val):
    return {"number": val}

def checkbox_prop(val):
    return {"checkbox": val}


# ============================================================
# MAIN BUILD
# ============================================================

def main():
    print("=" * 60)
    print("TechFoods Notion Workspace Builder")
    print("=" * 60)

    parent = PARENT_PAGE_ID

    # --------------------------------------------------------
    # 1. Add overview content to root TechFoods page
    # --------------------------------------------------------
    print("\n[1/7] Adding overview to TechFoods page...")
    overview_blocks = [
        callout("AgriTech IoT Hydroponics SaaS Platform - Project Management Hub", "🌱"),
        paragraph(""),
        heading(2, "Project Overview"),
        paragraph("Technological Foods is an IoT hydroponics monitoring & automation platform. Arduino sensors collect data (temp, humidity, pH, EC), send to a Python API on Raspberry Pi, stored in InfluxDB, visualized in Grafana, with multi-channel alerts via ntfy."),
        paragraph(""),
        heading(3, "Tech Stack"),
        bulleted("Hardware: Arduino R4 WiFi, Raspberry Pi 4, DHT20 sensors, pH/EC probes"),
        bulleted("Backend: Python API, InfluxDB, SQLite (migrating to PostgreSQL)"),
        bulleted("Infrastructure: Docker Compose, GitHub Actions CI/CD, systemd services"),
        bulleted("Monitoring: Grafana dashboards, ntfy push notifications, SonarQube"),
        bulleted("Business: Multi-tenant SaaS (Bronze/Silver/Gold/Platinum tiers)"),
        paragraph(""),
        heading(3, "Key Metrics"),
        bulleted("65+ documentation files, 7 PDFs analyzed"),
        bulleted("200+ tasks identified across 8 epics"),
        bulleted("248 estimated hours of development work"),
        bulleted("6 sprints planned (Sprint 0 through Sprint 5+)"),
        bulleted("Revenue target: EUR 43,200/year (24 clients at EUR 150/mo avg)"),
        paragraph(""),
        divider(),
    ]
    append_blocks(parent, overview_blocks)

    # --------------------------------------------------------
    # 2. Create Epics Database
    # --------------------------------------------------------
    print("\n[2/7] Creating Epics database...")
    epics_db_id = create_database(parent, "Epics", {
        "Epic": {"title": {}},
        "Priority": {"select": {"options": [
            {"name": "P0 - Critical", "color": "red"},
            {"name": "P1 - High", "color": "orange"},
            {"name": "P2 - Medium", "color": "yellow"},
            {"name": "P3 - Low", "color": "green"},
        ]}},
        "Status": {"select": {"options": [
            {"name": "Not Started", "color": "default"},
            {"name": "In Progress", "color": "blue"},
            {"name": "Done", "color": "green"},
        ]}},
        "Estimated Hours": {"number": {"format": "number"}},
        "Sprint": {"select": {"options": [
            {"name": "Sprint 0 - Today", "color": "red"},
            {"name": "Sprint 1 - Week 1-2", "color": "orange"},
            {"name": "Sprint 2 - Week 3-4", "color": "yellow"},
            {"name": "Sprint 3 - Week 5-6", "color": "green"},
            {"name": "Sprint 4 - Week 7-8", "color": "blue"},
            {"name": "Sprint 5+ - Future", "color": "purple"},
        ]}},
        "Description": {"rich_text": {}},
    }, icon="🎯")

    epics = [
        ("Epic 1: Code Quality & Test Coverage", "P0 - Critical", "Sprint 0 - Today", 8,
         "Fix pytest errors, add business model tests, remove hardcoded secrets, strengthen API keys. BLOCKING MERGE."),
        ("Epic 2: Production Security", "P1 - High", "Sprint 1 - Week 1-2", 20,
         "HTTPS with Caddy, API key rotation, security headers, Twilio WhatsApp integration."),
        ("Epic 3: Database Scalability", "P1 - High", "Sprint 2 - Week 3-4", 20,
         "PostgreSQL migration from SQLite, connection pooling, abstraction layer, zero-downtime migration."),
        ("Epic 4: Business Intelligence Dashboard", "P2 - Medium", "Sprint 4 - Week 7-8", 24,
         "Revenue visualization, client health dashboard, upsell recommendation engine."),
        ("Epic 5: Multi-Location Deployment", "P2 - Medium", "Sprint 3 - Week 5-6", 32,
         "WireGuard VPN (Porto/Lisbon/Algarve), data sync queue, site health monitoring."),
        ("Epic 6: Customer Portal", "P3 - Low", "Sprint 5+ - Future", 40,
         "Client auth, React/Vue dashboard, Stripe billing, tier management."),
        ("Epic 7: Advanced Notifications", "P3 - Low", "Sprint 5+ - Future", 24,
         "Slack/Discord channels, message templates, webhook config."),
        ("Epic 8: AI/ML Predictive Alerts", "P3 - Low", "Sprint 5+ - Future", 60,
         "Sensor drift prediction with LSTM/Prophet, training data collection, API integration."),
    ]

    epic_names = {}
    for name, priority, sprint, hours, desc in epics:
        result = add_db_item(epics_db_id, {
            "Epic": title_prop(name),
            "Priority": select_prop(priority),
            "Sprint": select_prop(sprint),
            "Status": select_prop("Not Started"),
            "Estimated Hours": number_prop(hours),
            "Description": rich_text_prop(desc),
        })
        if result:
            epic_names[name] = result['id']
            print(f'    + {name}')

    # --------------------------------------------------------
    # 3. Create Product Backlog Database (Kanban)
    # --------------------------------------------------------
    print("\n[3/7] Creating Product Backlog database...")
    backlog_db_id = create_database(parent, "Product Backlog", {
        "Task": {"title": {}},
        "Status": {"select": {"options": [
            {"name": "Backlog", "color": "default"},
            {"name": "To Do", "color": "gray"},
            {"name": "In Progress", "color": "blue"},
            {"name": "In Review", "color": "purple"},
            {"name": "Done", "color": "green"},
            {"name": "Blocked", "color": "red"},
        ]}},
        "Priority": {"select": {"options": [
            {"name": "P0 - Critical", "color": "red"},
            {"name": "P1 - High", "color": "orange"},
            {"name": "P2 - Medium", "color": "yellow"},
            {"name": "P3 - Low", "color": "green"},
        ]}},
        "Epic": {"select": {"options": [
            {"name": "Code Quality", "color": "red"},
            {"name": "Security", "color": "orange"},
            {"name": "Database", "color": "yellow"},
            {"name": "BI Dashboard", "color": "green"},
            {"name": "Multi-Location", "color": "blue"},
            {"name": "Customer Portal", "color": "purple"},
            {"name": "Notifications", "color": "pink"},
            {"name": "AI/ML", "color": "brown"},
            {"name": "Business/Strategy", "color": "gray"},
            {"name": "DevOps", "color": "default"},
        ]}},
        "Sprint": {"select": {"options": [
            {"name": "Sprint 0", "color": "red"},
            {"name": "Sprint 1", "color": "orange"},
            {"name": "Sprint 2", "color": "yellow"},
            {"name": "Sprint 3", "color": "green"},
            {"name": "Sprint 4", "color": "blue"},
            {"name": "Sprint 5+", "color": "purple"},
        ]}},
        "Story Points": {"number": {"format": "number"}},
        "Estimate": {"rich_text": {}},
        "Assignee": {"select": {"options": [
            {"name": "DevOps", "color": "blue"},
            {"name": "Backend Dev", "color": "green"},
            {"name": "Frontend Dev", "color": "purple"},
            {"name": "QA", "color": "orange"},
            {"name": "Data Scientist", "color": "yellow"},
            {"name": "Team Lead", "color": "red"},
        ]}},
    }, icon="📋")

    # --------------------------------------------------------
    # 4. Populate Product Backlog with ALL tasks
    # --------------------------------------------------------
    print("\n[4/7] Populating backlog tasks...")

    tasks = [
        # === SPRINT 0: P0 Critical (Blocking Merge) ===
        ("TASK-001: Fix hardcoded credentials in .env.example", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 1, "5 min", "DevOps"),
        ("TASK-002: Generate production API keys (32+ char)", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 1, "10 min", "DevOps"),
        ("TASK-003: Add .gitignore rules (.claude/settings, .env)", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 1, "2 min", "DevOps"),
        ("TASK-101: Fix test_real_notification.py sys.exit()", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 2, "30 min", "Backend Dev"),
        ("TASK-104: Create test_business_model.py (15+ tests)", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 3, "2 hours", "Backend Dev"),
        ("TASK-105: Create test_client_manager.py (10+ tests)", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 2, "1 hour", "Backend Dev"),
        ("TASK-108: Replace placeholder phone numbers with env vars", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 1, "30 min", "Backend Dev"),
        ("TASK-109: Update .env.example with CHANGE_ME + strong key instructions", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 1, "10 min", "DevOps"),
        ("TASK-004: Create root README.md", "To Do", "P0 - Critical", "Code Quality", "Sprint 0", 2, "30 min", "DevOps"),
        ("TASK-007: Merge feature/dashboard into dev", "Backlog", "P0 - Critical", "Code Quality", "Sprint 0", 1, "15 min", "DevOps"),
        ("TASK-008: Tag release v2.0.0-beta", "Backlog", "P0 - Critical", "Code Quality", "Sprint 0", 1, "5 min", "DevOps"),

        # === SPRINT 1: Dev Environment & Security ===
        ("TASK-009: Deploy to dev Raspberry Pi", "Backlog", "P1 - High", "DevOps", "Sprint 1", 3, "1 hour", "DevOps"),
        ("TASK-010: Configure InfluxDB (org/bucket/token)", "Backlog", "P1 - High", "DevOps", "Sprint 1", 1, "30 min", "DevOps"),
        ("TASK-011: Set up ntfy notifications", "Backlog", "P1 - High", "DevOps", "Sprint 1", 1, "15 min", "DevOps"),
        ("TASK-014: Test Arduino connection", "Backlog", "P1 - High", "DevOps", "Sprint 1", 2, "30 min", "DevOps"),
        ("TASK-015: Create Grafana dashboard", "Backlog", "P1 - High", "DevOps", "Sprint 1", 3, "2 hours", "DevOps"),
        ("TASK-201: Install Caddy reverse proxy for HTTPS", "Backlog", "P1 - High", "Security", "Sprint 1", 5, "4 hours", "DevOps"),
        ("TASK-202: Enforce HTTPS on all API endpoints", "Backlog", "P1 - High", "Security", "Sprint 1", 2, "2 hours", "Backend Dev"),
        ("TASK-203: Add security headers (HSTS, CSP, X-Frame)", "Backlog", "P1 - High", "Security", "Sprint 1", 1, "1 hour", "Backend Dev"),
        ("TASK-205: Create API key rotation endpoint", "Backlog", "P1 - High", "Security", "Sprint 1", 5, "4 hours", "Backend Dev"),
        ("TASK-208: Complete Twilio WhatsApp integration", "Backlog", "P1 - High", "Security", "Sprint 1", 5, "4 hours", "Backend Dev"),
        ("TASK-028: Set up automated backups (daily USB)", "Backlog", "P1 - High", "DevOps", "Sprint 1", 2, "1 hour", "DevOps"),

        # === SPRINT 2: Database & Scalability ===
        ("TASK-301: Create DB abstraction layer (SQLite + PostgreSQL)", "Backlog", "P1 - High", "Database", "Sprint 2", 8, "8 hours", "Backend Dev"),
        ("TASK-302: Write SQLite-to-PostgreSQL migration script", "Backlog", "P1 - High", "Database", "Sprint 2", 5, "4 hours", "Backend Dev"),
        ("TASK-303: Performance benchmarking (10-500 clients)", "Backlog", "P1 - High", "Database", "Sprint 2", 5, "4 hours", "Backend Dev"),
        ("TASK-304: Document zero-downtime migration", "Backlog", "P1 - High", "Database", "Sprint 2", 3, "4 hours", "Backend Dev"),
        ("Migrate to FastAPI from BaseHTTPRequestHandler", "Backlog", "P1 - High", "Database", "Sprint 2", 8, "1 day", "Backend Dev"),
        ("Implement rate limiting (SlowAPI + Redis)", "Backlog", "P1 - High", "Database", "Sprint 2", 5, "2 hours", "Backend Dev"),
        ("Setup Celery + Redis task queue", "Backlog", "P1 - High", "Database", "Sprint 2", 8, "3 hours", "Backend Dev"),
        ("Migrate notifications to background tasks (Celery)", "Backlog", "P1 - High", "Notifications", "Sprint 2", 8, "3 hours", "Backend Dev"),
        ("Add 14 database indexes (time, composite, FK)", "Backlog", "P2 - Medium", "Database", "Sprint 2", 3, "1 hour", "Backend Dev"),
        ("Fix N+1 queries in growth_stage_manager.py", "Backlog", "P2 - Medium", "Database", "Sprint 2", 5, "4 hours", "Backend Dev"),

        # === SPRINT 3: Multi-Location ===
        ("TASK-501: Configure WireGuard VPN on Porto Pi", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 8, "8 hours", "DevOps"),
        ("TASK-502: Create VPN client scripts for remote Pis", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 5, "4 hours", "DevOps"),
        ("TASK-504: Implement data sync queue (offline resilience)", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 8, "8 hours", "Backend Dev"),
        ("TASK-507: Implement heartbeat system (60s pings)", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 5, "4 hours", "Backend Dev"),
        ("TASK-508: Add site health dashboard (map view)", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 3, "2 hours", "Frontend Dev"),
        ("TASK-019: Set up WireGuard VPN on Porto Pi", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 3, "2 hours", "DevOps"),
        ("TASK-020: Configure VPN client on Lisbon Pi", "Backlog", "P2 - Medium", "Multi-Location", "Sprint 3", 2, "1 hour", "DevOps"),

        # === SPRINT 4: BI Dashboard ===
        ("TASK-401: Revenue calculation endpoints", "Backlog", "P2 - Medium", "BI Dashboard", "Sprint 4", 5, "4 hours", "Backend Dev"),
        ("TASK-402: Revenue visualization (Charts.js)", "Backlog", "P2 - Medium", "BI Dashboard", "Sprint 4", 5, "4 hours", "Frontend Dev"),
        ("TASK-404: Client health dashboard view", "Backlog", "P2 - Medium", "BI Dashboard", "Sprint 4", 8, "6 hours", "Frontend Dev"),
        ("TASK-407: Upsell recommendation engine", "Backlog", "P2 - Medium", "BI Dashboard", "Sprint 4", 5, "4 hours", "Backend Dev"),
        ("TASK-024: Train predictive maintenance ML model", "Backlog", "P2 - Medium", "AI/ML", "Sprint 4", 8, "8 hours", "Data Scientist"),

        # === SPRINT 5+: Future ===
        ("TASK-601: Client authentication system", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 8, "8 hours", "Backend Dev"),
        ("TASK-602: Build client dashboard UI (React/Vue)", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 8, "8 hours", "Frontend Dev"),
        ("TASK-604: Integrate Stripe payment gateway", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 8, "8 hours", "Backend Dev"),
        ("TASK-701: Create Slack notification channel", "Backlog", "P3 - Low", "Notifications", "Sprint 5+", 5, "4 hours", "Backend Dev"),
        ("TASK-801: Collect training data from 100+ sensors", "Backlog", "P3 - Low", "AI/ML", "Sprint 5+", 13, "16 hours", "Data Scientist"),
        ("TASK-802: Train drift prediction model (LSTM/Prophet)", "Backlog", "P3 - Low", "AI/ML", "Sprint 5+", 13, "16 hours", "Data Scientist"),
        ("TASK-025: Optimize dashboard for mobile (CSS)", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 5, "4 hours", "Frontend Dev"),
        ("TASK-027: Create Progressive Web App (PWA)", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 5, "4 hours", "Frontend Dev"),
        ("Implement WebSocket for real-time dashboard", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 5, "4 hours", "Backend Dev"),
        ("Add Grafana embedding in business dashboard", "Backlog", "P3 - Low", "BI Dashboard", "Sprint 5+", 3, "2 hours", "DevOps"),
        ("Create admin UI for rule management", "Backlog", "P3 - Low", "Customer Portal", "Sprint 5+", 5, "4 hours", "Frontend Dev"),
        ("TASK-030: Set up SonarQube on Raspberry Pi", "Backlog", "P2 - Medium", "DevOps", "Sprint 1", 3, "2 hours", "DevOps"),

        # === Business & Strategy Tasks ===
        ("Form Cooperative CRL in Braganca (10 farmers)", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 5+", 8, "Month 1", "Team Lead"),
        ("Water Partnership with Aguas do Nordeste", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 5+", 5, "Month 1", "Team Lead"),
        ("Apply for EU FEADER funding (EUR 105,000)", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 5+", 8, "Month 1", "Team Lead"),
        ("Secure 2ha land (municipal lease)", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 5+", 5, "Month 1", "Team Lead"),
        ("Deploy AgriTech platform to pilot farm", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 5+", 8, "Month 3", "DevOps"),
        ("Build $600 prototype for remote community", "Backlog", "P3 - Low", "Business/Strategy", "Sprint 5+", 5, "Month 1", "DevOps"),
        ("Submit $10,000 grant proposal", "Backlog", "P3 - Low", "Business/Strategy", "Sprint 5+", 5, "Month 2", "Team Lead"),
        ("Onboard first 3 paying SaaS clients", "Backlog", "P1 - High", "Business/Strategy", "Sprint 3", 8, "Month 2-3", "Team Lead"),
        ("Hardware: Order Arduino Opta + SIM800L", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 1", 2, "1 week", "DevOps"),
        ("Hardware: Buy 2nd DHT20 for dual sensor", "Backlog", "P2 - Medium", "Business/Strategy", "Sprint 1", 1, "1 week", "DevOps"),
    ]

    count = 0
    for task_name, status, priority, epic, sprint, sp, estimate, assignee in tasks:
        result = add_db_item(backlog_db_id, {
            "Task": title_prop(task_name),
            "Status": select_prop(status),
            "Priority": select_prop(priority),
            "Epic": select_prop(epic),
            "Sprint": select_prop(sprint),
            "Story Points": number_prop(sp),
            "Estimate": rich_text_prop(estimate),
            "Assignee": select_prop(assignee),
        })
        count += 1
        if count % 10 == 0:
            print(f'    Added {count}/{len(tasks)} tasks...')
    print(f'    Added {count}/{len(tasks)} tasks total.')

    # --------------------------------------------------------
    # 5. Create Sprint Planning Page
    # --------------------------------------------------------
    print("\n[5/7] Creating Sprint Planning page...")
    sprint_page = create_page(parent, "Sprint Planning", icon="🏃")
    if sprint_page:
        sprint_blocks = [
            callout("6 sprints planned covering immediate fixes through future vision", "📅"),
            paragraph(""),
            heading(2, "Sprint 0 - Today (P0 Critical, ~3 hours)"),
            paragraph("Goal: Fix all merge blockers, merge feature/dashboard to dev"),
            todo_item("Fix pytest collection error (test_real_notification.py)", False),
            todo_item("Remove .claude/settings.local.json from git", False),
            todo_item("Add business model tests (15+ tests)", False),
            todo_item("Replace placeholder phone numbers", False),
            todo_item("Strengthen API key configuration", False),
            todo_item("Create root README.md", False),
            todo_item("Run full test suite (148 tests)", False),
            todo_item("Merge feature/dashboard to dev", False),
            todo_item("Tag release v2.0.0-beta", False),
            paragraph(""),
            heading(2, "Sprint 1 - Week 1-2 (Dev Environment + Security, ~12 hours)"),
            paragraph("Goal: Deploy to dev Pi, add HTTPS, complete Twilio integration"),
            todo_item("Deploy to dev Raspberry Pi", False),
            todo_item("Configure InfluxDB and Grafana dashboards", False),
            todo_item("Install Caddy for HTTPS (auto-SSL)", False),
            todo_item("Create API key rotation endpoint", False),
            todo_item("Complete Twilio WhatsApp integration", False),
            todo_item("Set up automated backups", False),
            todo_item("Set up SonarQube on Pi", False),
            paragraph(""),
            heading(2, "Sprint 2 - Week 3-4 (Database & Scalability, ~20 hours)"),
            paragraph("Goal: Migrate to FastAPI + PostgreSQL, add Celery background tasks"),
            todo_item("Migrate from BaseHTTPRequestHandler to FastAPI", False),
            todo_item("Implement PostgreSQL with connection pooling", False),
            todo_item("Write SQLite-to-PostgreSQL migration script", False),
            todo_item("Setup Celery + Redis task queue", False),
            todo_item("Add rate limiting (SlowAPI)", False),
            todo_item("Performance benchmarking", False),
            paragraph(""),
            heading(2, "Sprint 3 - Week 5-6 (Multi-Location, ~32 hours)"),
            paragraph("Goal: VPN network between Porto/Lisbon, data sync, onboard first clients"),
            todo_item("Configure WireGuard VPN (Porto server)", False),
            todo_item("Create VPN client for Lisbon Pi", False),
            todo_item("Implement data sync queue", False),
            todo_item("Add site health monitoring", False),
            todo_item("Onboard first 3 paying clients", False),
            paragraph(""),
            heading(2, "Sprint 4 - Week 7-8 (BI Dashboard, ~24 hours)"),
            paragraph("Goal: Revenue dashboard, client health scores, upsell engine"),
            todo_item("Revenue calculation endpoints + Charts.js visualization", False),
            todo_item("Client health dashboard view", False),
            todo_item("Upsell recommendation engine", False),
            todo_item("Train predictive maintenance ML model", False),
            paragraph(""),
            heading(2, "Sprint 5+ - Future (Portal, AI/ML, ~124 hours)"),
            paragraph("Goal: Customer portal, Stripe billing, Slack notifications, AI predictions"),
            todo_item("Client authentication + React/Vue dashboard", False),
            todo_item("Stripe payment gateway", False),
            todo_item("Slack/Discord notification channels", False),
            todo_item("Progressive Web App (PWA)", False),
            todo_item("LSTM/Prophet drift prediction model", False),
        ]
        append_blocks(sprint_page, sprint_blocks)

    # --------------------------------------------------------
    # 6. Create Strategy & Vision Page
    # --------------------------------------------------------
    print("\n[6/7] Creating Strategy & Vision page...")
    strategy_page = create_page(parent, "Strategy & Vision", icon="🚀")
    if strategy_page:
        strategy_blocks = [
            heading(2, "Business Model"),
            paragraph("Multi-tenant SaaS with 4 tiers:"),
            bulleted("Bronze: EUR 49/mo - Critical alerts only, 7-day retention, 1 zone/3 crops"),
            bulleted("Silver: EUR 199/mo - Preventive alerts, 30-day retention, growth tracking, 3 zones"),
            bulleted("Gold: EUR 499/mo - Full escalation, 90-day retention, WhatsApp/ntfy, 10 zones"),
            bulleted("Platinum: EUR 799/mo - Unlimited, 180-day retention, phone calls, dedicated manager"),
            paragraph(""),
            heading(2, "Revenue Projections"),
            bulleted("Year 1: 24 clients at EUR 150/mo avg = EUR 43,200/year"),
            bulleted("Year 3: 150 clients = EUR 681,000/year ARR"),
            bulleted("Cooperative model: EUR 371,100/year per 50-member hub"),
            bulleted("2030 Vision: 20 hubs, EUR 20M/year, 2,000 farmers"),
            paragraph(""),
            heading(2, "Pilot Project - Braganca"),
            paragraph("6-month pilot with 10 farmers, EUR 150,000 budget (70% EU funding). Form cooperative, partner with Aguas do Nordeste for recycled water, build 1,000m2 greenhouse, deploy 15 Arduino sensor nodes."),
            paragraph(""),
            heading(2, "Remote Community Vision"),
            paragraph("$600 solar-powered, offline-first hydroponic systems for remote communities globally. 3-phase roadmap: 3 pilot communities ($10,000) -> 30 communities ($150,000) -> 100+ ecosystem. 5-year impact: 500 communities, 50,000 people."),
            paragraph(""),
            heading(2, "Hardware Decision"),
            paragraph("Arduino Opta (EUR 737, 3-year cost EUR 917) RECOMMENDED over Siemens LOGO! 8 (EUR 1,880, 3-year cost EUR 2,060). Arduino wins 9/15 criteria. Siemens only for enterprise clients at scale (Phase 4+)."),
            paragraph(""),
            heading(2, "Scalability Assessment"),
            callout("Current system handles 5-10 sensors, 10-20 clients. NOT production-ready for scale. 3-week refactoring needed ($25,000 investment) to reach 200+ sensors, 100+ clients. Projected ROI: 9,000% over 5 years.", "⚠️"),
            paragraph(""),
            heading(2, "Key Documents"),
            bulleted("docs/strategy/EXECUTIVE_SUMMARY.md - Scalability business case"),
            bulleted("docs/strategy/VISION_SUSTAINABLE_REMOTE_COMMUNITIES.md - 2030 vision"),
            bulleted("docs/planning/ACTION_PLAN_PILOT_PROJECT.md - Braganca 6-month plan"),
            bulleted("docs/planning/PRODUCT_BACKLOG.md - Full 248h backlog"),
            bulleted("docs/strategy/GRANT_PROPOSAL_TEMPLATE.md - $10K grant template"),
        ]
        append_blocks(strategy_page, strategy_blocks)

    # --------------------------------------------------------
    # 7. Create Architecture & Technical Page
    # --------------------------------------------------------
    print("\n[7/7] Creating Architecture & Technical page...")
    arch_page = create_page(parent, "Architecture & Technical", icon="🏗️")
    if arch_page:
        arch_blocks = [
            heading(2, "System Architecture"),
            paragraph("Arduino R4 WiFi -> HTTP POST -> Python API (port 3001) -> InfluxDB + SQLite -> Grafana (port 3000) + ntfy notifications. Docker Compose runs InfluxDB, Grafana, Node-RED on Raspberry Pi 4."),
            paragraph(""),
            heading(2, "Current State (Phase 1 - DONE)"),
            bulleted("Sensor monitoring: temp, humidity, pH, EC via DHT20/analog"),
            bulleted("Rule engine: 13 default rules with warning_margin support"),
            bulleted("Alert system: 3-tier (preventive/critical/urgent) with escalation"),
            bulleted("Growth stages: seedling -> vegetative -> maturity (auto-advance)"),
            bulleted("Notifications: ntfy multi-channel (console, push, WhatsApp-ready)"),
            bulleted("Business: Client management, health scores, tier-based routing"),
            bulleted("CI/CD: 4 GitHub Actions workflows (test, deploy-server, deploy-arduino, hello)"),
            bulleted("Dual sensor redundancy: automatic drift detection"),
            bulleted("109 unit tests passing"),
            paragraph(""),
            heading(2, "Target Architecture (Phase 2 - PLANNED)"),
            bulleted("FastAPI (async) replacing BaseHTTPRequestHandler"),
            bulleted("PostgreSQL + SQLAlchemy replacing SQLite"),
            bulleted("Celery + Redis for background task processing"),
            bulleted("NGINX reverse proxy with HTTPS (Caddy)"),
            bulleted("Prometheus + Grafana for application monitoring"),
            bulleted("8 microservices: Sensor, Weather, Crop, Analytics, Client, Notification, Billing, Data Marketplace"),
            paragraph(""),
            heading(2, "Scalability Issues (from Audit)"),
            callout("9 issues identified: sync I/O, no connection pooling, no rate limiting, blocking notifications, missing indexes, N+1 queries, no caching, memory leaks, non-functional data retention.", "🔴"),
            paragraph(""),
            heading(2, "Infrastructure Decision: Docker Compose (NOT Kubernetes)"),
            paragraph("Kubernetes is NOT needed at current scale (10-200 sensors). Docker Compose: $120/month vs Kubernetes: $388/month. Consider K8s only at 1000+ sensors (18-24 months)."),
            paragraph(""),
            heading(2, "Deployment"),
            bulleted("Server: SSH/rsync to Raspberry Pi on master push"),
            bulleted("Arduino: OTA firmware over WiFi on master push"),
            bulleted("Two environments: Dev (ports 3001/8086/3000) and Prod (3002/8087/3001)"),
            bulleted("Systemd services: docker, api, backup (2AM daily), monitor (5min health)"),
            paragraph(""),
            heading(2, "Key Technical Documents"),
            bulleted("docs/architecture/database_design_documentation.md - PostgreSQL schema"),
            bulleted("docs/architecture/domain_model_documentation.md - DDD domain model"),
            bulleted("docs/architecture/MICROSERVICES_ARCHITECTURE.md - 8-service plan"),
            bulleted("docs/planning/SCALABILITY_AUDIT_REPORT.md - Production readiness audit"),
            bulleted("docs/planning/SCALABILITY_BACKLOG.md - 3-week refactoring plan"),
            bulleted("docs/architecture/DOCKER_COMPOSE_VS_KUBERNETES.md - Infrastructure decision"),
        ]
        append_blocks(arch_page, arch_blocks)

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("WORKSPACE BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nCreated under: TechFoods page")
    print(f"  - Epics database: {len(epics)} epics")
    print(f"  - Product Backlog database: {count} tasks")
    print(f"  - Sprint Planning page (6 sprints)")
    print(f"  - Strategy & Vision page")
    print(f"  - Architecture & Technical page")
    print(f"\nOpen Notion to see your workspace!")


if __name__ == '__main__':
    main()
