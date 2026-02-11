# Site Visits Backoffice - Guide

**Version**: 1.0.0
**Last Updated**: 2026-02-10
**Purpose**: Step-by-step guide to run and explore the Site Visits Backoffice

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Files Created](#files-created)
4. [Step 1: Seed Demo Data](#step-1-seed-demo-data)
5. [Step 2: Start the Server](#step-2-start-the-server)
6. [Step 3: Open the Backoffice](#step-3-open-the-backoffice)
7. [Step 4: Explore the Dashboard Tab](#step-4-explore-the-dashboard-tab)
8. [Step 5: Create a Field Report](#step-5-create-a-field-report)
9. [Step 6: Explore Visit History](#step-6-explore-visit-history)
10. [Step 7: Test the API Directly](#step-7-test-the-api-directly)
11. [API Reference](#api-reference)
12. [Existing APIs Consumed](#existing-apis-consumed)
13. [For C# Developers](#for-c-developers)

---

## Overview

The Site Visits Backoffice is a single-page web application for managing field inspections at hydroponic facilities. It demonstrates the **API consumer pattern**: the frontend populates itself by calling existing backend APIs at runtime, rather than hardcoding data.

Key features:
- **Dashboard** with KPIs, CSS-only charts, and live system status
- **Field Report Form** that fetches clients, crops, and sensor data from APIs
- **Visit History** with search (debounced), filters, sorting, expandable rows, CSV export, and pagination

---

## Architecture

```
Browser (site_visits.html)
    |
    |-- GET /api/site-visits/*          (new endpoints - visit CRUD + analytics)
    |-- GET /api/crops                  (existing - populates crop checkboxes)
    |-- GET /api/data/latest            (existing - live sensor readings)
    |-- GET /api/business/dashboard     (existing - client health, sensor status)
    |-- GET /api/calibrations/due       (existing - overdue calibrations)
    |
server.py (HTTP router)
    |
    |-- site_visits_manager.py  (SQLite CRUD + analytics)
    |-- client_manager.py       (existing clients table)
    |-- growth_stage_manager.py (existing crops)
    |-- database.py             (existing calibrations)
```

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/api/site_visits_manager.py` | Database layer: SQLite schema, CRUD, analytics queries |
| `backend/site_visits.html` | Single-page backoffice UI (HTML + CSS + JS) |
| `backend/tools/seed_site_visits.py` | Seed script: 5 demo clients + 35 demo visits |
| `backend/api/server.py` | Modified: added import + 10 route handlers |

---

## Step 1: Seed Demo Data

The seed script populates the database with 5 clients and 35 realistic site visits spread over the last 4 months, so the dashboard charts and tables are full.

```bash
cd backend/api
python ../tools/seed_site_visits.py
```

Expected output:
```
Database: .../backend/data/agritech.db

Seeding 5 demo clients...
  -> Inserted 5 clients
Seeding 35 demo site visits...
  -> Inserted 35 site visits across 5 clients

Done! Start the server and open http://localhost:3001/site-visits
```

> If you already have clients in the database, the script skips client seeding.
> If visits already exist, it asks before clearing and re-seeding.

---

## Step 2: Start the Server

```bash
cd backend/api
python server.py
```

You should see all endpoints listed in the terminal, including the **Site Visits Backoffice** section:

```
Site Visits Backoffice:
  GET    /site-visits              - Site visits backoffice UI
  GET    /api/site-visits          - List visits (paginated, filtered)
  GET    /api/site-visits/dashboard - Visit analytics
  ...
```

---

## Step 3: Open the Backoffice

Open your browser and navigate to:

```
http://localhost:3001/site-visits
```

You will see the Dashboard tab loaded with data.

---

## Step 4: Explore the Dashboard Tab

The dashboard loads automatically and shows:

**Row 1 - KPI Cards:**
- **Total Site Visits** - all-time count
- **Visits This Month** - with a +/- delta badge compared to last month
- **Pending Follow-ups** - highlighted in yellow/orange if > 0
- **Avg Site Rating** - star display (1-5)

**Row 2 - Live System Status** (fetched from existing APIs):
- **Active Crops** - count by growth stage (from `GET /api/crops`)
- **Sensor Health** - online/total, uptime %, overdue calibrations (from `GET /api/business/dashboard`)
- **Client Health** - average health score, clients needing attention (from `GET /api/business/dashboard`)

> If InfluxDB or other services are not running, these cards will show
> "Could not load..." gracefully. The visit stats still work because they
> come from SQLite.

**Row 3 - Charts** (pure CSS, no chart libraries):
- **Bar chart**: visits by month (last 6 months)
- **Donut chart**: visits by type (routine/emergency/follow-up/audit) using CSS `conic-gradient`
- **Rating distribution**: horizontal bars with star labels

**Row 4 - Data Tables:**
- **Top Visited Clients** - ranked by visit count with health score badges
- **Recent Activity Feed** - last 8 visits as cards with type badges, star ratings, issue counts

---

## Step 5: Create a Field Report

Click the **"New Field Report"** tab.

Watch the form auto-populate from 3 API calls in parallel:
1. `GET /api/site-visits/clients` populates the **Client** dropdown
2. `GET /api/crops` populates the **Crop Batches** checkboxes
3. `GET /api/data/latest` populates the **Live Sensor Readings** panel

Fill out the form:
1. **Visit Date** - defaults to today
2. **Inspector Name** - type a name (past inspectors appear as suggestions)
3. **Client** - select from dropdown (shows company name + service tier)
4. **Visit Type** - routine / emergency / follow-up / audit
5. **Crop Batches** - check the batches inspected
6. **Zones Inspected** - type a zone name and press Enter to add tags
7. **Observations** - free text
8. **Issues Found** - click "+ Add Issue" to add rows (description + severity + related-to)
9. **Actions Taken** - free text
10. **Follow-up Required** - toggle on to reveal date picker + notes
11. **Overall Rating** - click 1-5 stars
12. **Submit** - green toast confirms success

After submitting, switch to the **History** tab to see your new visit at the top.

---

## Step 6: Explore Visit History

Click the **"Visit History"** tab.

**Search**: Type in the search box. It uses **debounce** (300ms delay) so it waits until you stop typing before querying the API.

**Filters**: Use the dropdowns to filter by:
- Visit type (routine/emergency/follow-up/audit)
- Date range (from/to)
- Inspector name
- Follow-up status (all/pending/completed)

**Sort**: Click any column header to toggle ascending/descending sort.

**Expand**: Click any row to expand inline details:
- Full observations and actions taken
- Issues list with severity badges
- Zones and crop batches inspected
- Sensor readings snapshot captured at visit time
- Follow-up details

**Complete Follow-up**: Click the "Complete" button on visits with pending follow-ups.

**Delete**: Click the X button on any row (with confirmation dialog).

**CSV Export**: Click "Export CSV" to download all visits as a CSV file.

**Pagination**: Navigate pages at the bottom of the table.

---

## Step 7: Test the API Directly

Use curl or any HTTP client to test the REST endpoints:

```bash
# List visits (paginated)
curl http://localhost:3001/api/site-visits?page=1&per_page=5

# Dashboard analytics (KPIs + chart data)
curl http://localhost:3001/api/site-visits/dashboard

# Client list for dropdowns
curl http://localhost:3001/api/site-visits/clients

# Single visit detail
curl http://localhost:3001/api/site-visits/1

# Create a visit
curl -X POST http://localhost:3001/api/site-visits \
  -H "Content-Type: application/json" \
  -d '{
    "inspector_name": "Test Inspector",
    "visit_type": "routine",
    "client_id": 1,
    "observations": "Everything looks good",
    "overall_rating": 4
  }'

# Update a visit
curl -X PUT http://localhost:3001/api/site-visits/1 \
  -H "Content-Type: application/json" \
  -d '{"overall_rating": 5, "observations": "Updated notes"}'

# Complete a follow-up
curl -X POST http://localhost:3001/api/site-visits/1/complete-follow-up

# Delete a visit
curl -X DELETE http://localhost:3001/api/site-visits/3

# Export all visits (for CSV)
curl http://localhost:3001/api/site-visits/export
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/site-visits` | Serve the HTML backoffice page |
| `GET` | `/api/site-visits` | List visits (paginated, filtered) |
| `GET` | `/api/site-visits/dashboard` | Visit analytics: KPIs, charts, recent activity |
| `GET` | `/api/site-visits/clients` | Client list for form dropdowns |
| `GET` | `/api/site-visits/export` | All visits as flat JSON (for CSV) |
| `GET` | `/api/site-visits/{id}` | Single visit detail |
| `POST` | `/api/site-visits` | Create a new visit |
| `POST` | `/api/site-visits/{id}/complete-follow-up` | Mark follow-up as done |
| `PUT` | `/api/site-visits/{id}` | Update visit fields |
| `DELETE` | `/api/site-visits/{id}` | Delete a visit |

### Query Parameters for `GET /api/site-visits`

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `per_page` | int | Items per page (default: 20) |
| `visit_type` | string | Filter: routine, emergency, follow_up, audit |
| `inspector` | string | Filter by inspector name (partial match) |
| `date_from` | string | Filter: visits on or after this date (YYYY-MM-DD) |
| `date_to` | string | Filter: visits on or before this date (YYYY-MM-DD) |
| `follow_up` | string | Filter: "pending" or "completed" |
| `search` | string | Search across inspector name, observations, facility |
| `sort` | string | Sort column: visit_date, inspector_name, visit_type, overall_rating |
| `sort_dir` | string | Sort direction: asc or desc (default: desc) |

---

## Existing APIs Consumed

The backoffice is a **client of the existing API** - it calls these endpoints to populate the UI:

| Existing Endpoint | Used In | Data Pulled |
|---|---|---|
| `GET /api/crops` | Form: crop batch checkboxes, Dashboard: active crops card | Active crop batches with variety, zone, stage |
| `GET /api/data/latest` | Form: live sensor readings panel | Latest sensor readings (temp, humidity, pH, EC) |
| `GET /api/business/dashboard` | Dashboard: client health + sensor status cards | Client health scores, sensor online/offline |
| `GET /api/calibrations/due` | Dashboard: overdue calibrations badge | Sensors needing calibration |

This demonstrates the **API consumer pattern**: the frontend depends on the response shape (the API contract), not the implementation. If the backend switches from SQLite to PostgreSQL, the frontend keeps working unchanged.

---

## For C# Developers

If you are rebuilding this dashboard in C#, here is what you need to implement:

### Backend (ASP.NET / Minimal API)
1. **Database table**: `site_visits` with the schema described in `site_visits_manager.py`
2. **10 REST endpoints** matching the [API Reference](#api-reference) above
3. **Pagination**: LIMIT/OFFSET (or SKIP/TAKE in EF Core) with total count
4. **JSON columns**: `zones_inspected`, `crop_batches_checked`, `issues_found`, `sensor_readings_snapshot` are stored as JSON strings
5. **Filtering + sorting**: build WHERE clauses dynamically from query parameters (use parameterized queries to prevent SQL injection)

### Frontend (Blazor / Razor / plain JS)
1. **3 tabs**: Dashboard, New Report, History
2. **API consumer pattern**: on page load, fetch from multiple endpoints in parallel to populate dropdowns and context panels
3. **Charts**: use a C# charting library or CSS-only approach (conic-gradient for donut, width% for bars)
4. **Debounced search**: delay API calls until user stops typing (~300ms)
5. **CSV export**: generate client-side or add a server endpoint returning `text/csv`

### Key API contracts your C# app should call:
```
GET  /api/site-visits?page=1&per_page=15&sort=visit_date&sort_dir=desc
     -> { visits: [...], total: 35, page: 1, per_page: 15, total_pages: 3 }

GET  /api/site-visits/dashboard
     -> { kpis: {...}, charts: {...}, recent_activity: [...], top_clients: [...] }

POST /api/site-visits
     Body: { inspector_name, visit_type, client_id, observations, issues_found, ... }
     -> { status: "created", id: 36 }
```

Use the running Python server at `http://localhost:3001` as a **reference implementation** to compare your C# responses against.
