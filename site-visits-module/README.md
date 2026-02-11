# Site Visits Module - Reference Implementation

Self-contained reference for rebuilding the Site Visits Backoffice in C# (or any language).

## What's in this folder

```
site-visits-module/
  README.md                    <-- You are here
  SITE_VISITS_GUIDE.md         <-- Step-by-step guide to run and test
  site_visits_manager.py       <-- Database layer (schema + CRUD + analytics)
  routes_server.py             <-- HTTP routes extracted from server.py (reference only)
  site_visits.html             <-- Frontend (HTML + CSS + JS, single file)
  seed_site_visits.py          <-- Seed script (5 clients + 35 demo visits)
  sample_responses/            <-- Example JSON responses from each endpoint
```

## Quick Start (run the Python version)

```bash
# 1. Seed demo data
cd backend/api
python ../tools/seed_site_visits.py

# 2. Start server
python server.py

# 3. Open browser
open http://localhost:3001/site-visits
```

See `SITE_VISITS_GUIDE.md` for the full walkthrough.

---

## Database Schema

Two tables. `clients` already exists in the system. `site_visits` is new.

### clients (existing)

```sql
CREATE TABLE clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name    TEXT NOT NULL,
    contact_name    TEXT,
    contact_phone   TEXT,
    contact_email   TEXT,
    service_tier    TEXT DEFAULT 'bronze',     -- bronze | silver | gold
    location        TEXT,
    install_date    TEXT DEFAULT (date('now')),
    monthly_fee     REAL DEFAULT 49.0,
    is_active       INTEGER DEFAULT 1,
    health_score    INTEGER DEFAULT 100,       -- 0-100
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

### site_visits (new)

```sql
CREATE TABLE site_visits (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_date               TEXT NOT NULL DEFAULT (date('now')),
    inspector_name           TEXT NOT NULL,
    client_id                INTEGER,                -- FK -> clients.id
    facility_name            TEXT,
    visit_type               TEXT NOT NULL,           -- routine | emergency | follow_up | audit
    zones_inspected          TEXT,                    -- JSON array: ["Zone A", "Zone B"]
    crop_batches_checked     TEXT,                    -- JSON array: [1, 3, 5]
    sensor_readings_snapshot TEXT,                    -- JSON object: {temperature: 22.5, ...}
    observations             TEXT,
    issues_found             TEXT,                    -- JSON array: [{description, severity, related_to}]
    actions_taken            TEXT,
    follow_up_required       INTEGER DEFAULT 0,
    follow_up_date           TEXT,
    follow_up_notes          TEXT,
    follow_up_completed      INTEGER DEFAULT 0,
    overall_rating           INTEGER DEFAULT 3,       -- 1-5
    photo_notes              TEXT,
    created_at               TEXT DEFAULT (datetime('now')),
    updated_at               TEXT DEFAULT (datetime('now'))
);
```

**JSON columns**: SQLite has no native array type, so `zones_inspected`, `crop_batches_checked`, `sensor_readings_snapshot`, and `issues_found` store JSON strings. In C# with SQL Server/PostgreSQL, consider using `nvarchar(max)` with JSON or proper JSONB columns.

---

## API Endpoints

| Method   | Path                                         | Description                        |
|----------|----------------------------------------------|------------------------------------|
| `GET`    | `/api/site-visits`                           | List visits (paginated + filtered) |
| `GET`    | `/api/site-visits/dashboard`                 | KPIs, charts, recent activity      |
| `GET`    | `/api/site-visits/clients`                   | Client dropdown list               |
| `GET`    | `/api/site-visits/export`                    | All visits (flat, for CSV)         |
| `GET`    | `/api/site-visits/{id}`                      | Single visit detail                |
| `POST`   | `/api/site-visits`                           | Create visit                       |
| `POST`   | `/api/site-visits/{id}/complete-follow-up`   | Mark follow-up done                |
| `PUT`    | `/api/site-visits/{id}`                      | Update visit (partial)             |
| `DELETE` | `/api/site-visits/{id}`                      | Delete visit                       |

---

## Response Shapes

### GET /api/site-visits?page=1&per_page=5

```json
{
  "visits": [
    {
      "id": 1,
      "visit_date": "2026-01-15",
      "inspector_name": "Anna de Groot",
      "client_id": 3,
      "client_name": "FreshFlow Hydroponics",
      "facility_name": "FreshFlow Hydroponics",
      "visit_type": "routine",
      "zones_inspected": ["Zone A", "Zone C", "Propagation"],
      "crop_batches_checked": ["Rosso Premium #12", "Basil Genovese #11"],
      "sensor_readings_snapshot": {
        "temperature_c": 23.4,
        "humidity_pct": 65.2,
        "ph": 5.92,
        "ec_ms": 1.85
      },
      "observations": "All systems operating within normal parameters.",
      "issues_found": [
        {"description": "pH sensor drift exceeding +/-0.3", "severity": "medium", "related_to": "sensors"}
      ],
      "actions_taken": "Calibrated pH and EC sensors.",
      "follow_up_required": true,
      "follow_up_date": "2026-02-01",
      "follow_up_notes": "Check pH stability after buffer adjustment.",
      "follow_up_completed": false,
      "overall_rating": 4,
      "photo_notes": "",
      "created_at": "2026-01-15 09:30:00",
      "updated_at": "2026-01-15 09:30:00"
    }
  ],
  "total": 35,
  "page": 1,
  "per_page": 5,
  "total_pages": 7
}
```

### GET /api/site-visits/dashboard

```json
{
  "kpis": {
    "total_visits": 35,
    "visits_this_month": 8,
    "visits_last_month": 6,
    "month_delta": 2,
    "pending_followups": 4,
    "avg_rating": 3.9
  },
  "charts": {
    "monthly": [
      {"month": "2025-10", "count": 5},
      {"month": "2025-11", "count": 7},
      {"month": "2025-12", "count": 6},
      {"month": "2026-01", "count": 9},
      {"month": "2026-02", "count": 8}
    ],
    "by_type": [
      {"type": "routine", "count": 18},
      {"type": "follow_up", "count": 9},
      {"type": "audit", "count": 5},
      {"type": "emergency", "count": 3}
    ],
    "ratings": [
      {"rating": 2, "count": 3},
      {"rating": 3, "count": 7},
      {"rating": 4, "count": 16},
      {"rating": 5, "count": 9}
    ]
  },
  "recent_activity": ["... (same shape as visit objects above, last 10)"],
  "top_clients": [
    {
      "id": 1,
      "company_name": "GreenLeaf Farms",
      "health_score": 92,
      "visit_count": 9,
      "last_visit": "2026-02-08"
    }
  ],
  "inspectors": ["Anna de Groot", "Pieter Smit", "Sophie Mulder", "Tom Visser"]
}
```

### GET /api/site-visits/clients

```json
{
  "clients": [
    {
      "id": 1,
      "company_name": "GreenLeaf Farms",
      "service_tier": "gold",
      "location": "Westland, Zuid-Holland",
      "health_score": 92
    }
  ]
}
```

### POST /api/site-visits

**Request body:**
```json
{
  "inspector_name": "Anna de Groot",
  "visit_type": "routine",
  "client_id": 1,
  "facility_name": "Greenhouse A",
  "zones_inspected": ["Zone A", "Zone B"],
  "crop_batches_checked": [1, 3],
  "sensor_readings_snapshot": {"temperature_c": 23.0, "humidity_pct": 62.0},
  "observations": "All good",
  "issues_found": [{"description": "Minor leak", "severity": "low", "related_to": "infrastructure"}],
  "actions_taken": "Tightened fitting",
  "follow_up_required": false,
  "overall_rating": 4
}
```

**Response:**
```json
{"status": "created", "id": 36}
```

### Query Parameters for GET /api/site-visits

| Parameter    | Type   | Example              | Description                          |
|-------------|--------|----------------------|--------------------------------------|
| `page`      | int    | `1`                  | Page number (default: 1)             |
| `per_page`  | int    | `15`                 | Items per page (default: 20)         |
| `visit_type`| string | `routine`            | Filter by type                       |
| `inspector` | string | `Anna`               | Partial match on inspector name      |
| `date_from` | string | `2026-01-01`         | Visits on or after                   |
| `date_to`   | string | `2026-01-31`         | Visits on or before                  |
| `follow_up` | string | `pending`/`completed`| Filter by follow-up status           |
| `search`    | string | `greenhouse`         | Search across name/observations/facility |
| `sort`      | string | `visit_date`         | Sort column                          |
| `sort_dir`  | string | `asc`/`desc`         | Sort direction (default: desc)       |

---

## C# Migration Hints

### Suggested Project Structure (ASP.NET)

```
SiteVisits/
  Controllers/
    SiteVisitsController.cs    <-- Maps to routes_server.py
  Models/
    SiteVisit.cs               <-- Entity
    Client.cs                  <-- Entity (from existing system)
    SiteVisitDto.cs            <-- Create/Update request DTO
    DashboardResponse.cs       <-- Dashboard response shape
  Services/
    SiteVisitsService.cs       <-- Maps to site_visits_manager.py
  Data/
    SiteVisitsDbContext.cs     <-- EF Core context
    Migrations/                <-- EF Core migrations
  wwwroot/
    site-visits.html           <-- Frontend (or Blazor equivalent)
```

### Key Mapping

| Python                             | C# Equivalent                          |
|------------------------------------|----------------------------------------|
| `site_visits_manager.py`          | `SiteVisitsService.cs`                |
| `routes_server.py`                | `SiteVisitsController.cs`             |
| `sqlite3.connect()`              | `DbContext` (EF Core)                 |
| `json.dumps(list)` in DB column   | `JsonSerializer.Serialize()` or JSONB |
| `LIMIT ? OFFSET ?`               | `.Skip(offset).Take(pageSize)`        |
| `conn.execute("SELECT...")`      | LINQ queries or raw SQL via EF Core   |
| `row_factory = sqlite3.Row`      | EF Core entity mapping                |
| `site_visits.html` (fetch API)    | Same HTML or Blazor components        |

### JSON Column Strategy

The Python version stores arrays as JSON strings in TEXT columns. In C#:

**Option A - JSON string (simple, like Python):**
```csharp
public class SiteVisit {
    public string ZonesInspected { get; set; } // JSON string
}
// Serialize/deserialize manually with JsonSerializer
```

**Option B - EF Core value converter (cleaner):**
```csharp
public class SiteVisit {
    public List<string> ZonesInspected { get; set; }
}
// In OnModelCreating:
builder.Property(e => e.ZonesInspected)
    .HasConversion(
        v => JsonSerializer.Serialize(v, (JsonSerializerOptions)null),
        v => JsonSerializer.Deserialize<List<string>>(v, (JsonSerializerOptions)null));
```

**Option C - PostgreSQL JSONB (best for production):**
```csharp
builder.Property(e => e.ZonesInspected).HasColumnType("jsonb");
```
