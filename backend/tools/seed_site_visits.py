#!/usr/bin/env python3
"""
Seed Site Visits - Populate demo clients and field inspection visits.

Creates 5 demo clients and 35 realistic site visits spread over the last
4 months so the dashboard charts and history table have data to display.

Usage:
  cd backend/api
  python ../tools/seed_site_visits.py

Behaviour:
  - If clients already exist in the DB, client seeding is skipped.
  - If site visits already exist, the script asks before clearing and re-seeding.
"""

import sys
import json
import random
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('seed-site-visits')

# Resolve DB path relative to backend/api (the expected working directory)
DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'agritech.db'

# ── Demo Clients ──────────────────────────────────────────────────────────

DEMO_CLIENTS = [
    {
        'company_name': 'GreenLeaf Farms',
        'contact_name': 'Sarah Johnson',
        'contact_phone': '+31 6 1234 5678',
        'contact_email': 'sarah@greenleaffarms.nl',
        'service_tier': 'gold',
        'location': 'Westland, Zuid-Holland',
        'monthly_fee': 149.0,
        'health_score': 92,
        'notes': 'Large-scale lettuce operation, 3 greenhouse blocks',
    },
    {
        'company_name': 'Urban Harvest BV',
        'contact_name': 'Mark de Vries',
        'contact_phone': '+31 6 9876 5432',
        'contact_email': 'mark@urbanharvest.nl',
        'service_tier': 'silver',
        'location': 'Amsterdam, Noord-Holland',
        'monthly_fee': 99.0,
        'health_score': 78,
        'notes': 'Indoor vertical farm, herbs and microgreens',
    },
    {
        'company_name': 'FreshFlow Hydroponics',
        'contact_name': 'Lisa van den Berg',
        'contact_phone': '+31 6 5555 1234',
        'contact_email': 'lisa@freshflow.nl',
        'service_tier': 'gold',
        'location': 'Bleiswijk, Zuid-Holland',
        'monthly_fee': 149.0,
        'health_score': 85,
        'notes': 'Tomato and pepper specialist, NFT systems',
    },
    {
        'company_name': 'Sprout & Co',
        'contact_name': 'Jan Bakker',
        'contact_phone': '+31 6 4444 7890',
        'contact_email': 'jan@sproutco.nl',
        'service_tier': 'bronze',
        'location': 'Utrecht, Utrecht',
        'monthly_fee': 49.0,
        'health_score': 65,
        'notes': 'Startup, single DWC system',
    },
    {
        'company_name': 'Royal Greens International',
        'contact_name': 'Emma Jansen',
        'contact_phone': '+31 6 3333 4567',
        'contact_email': 'emma@royalgreens.nl',
        'service_tier': 'gold',
        'location': 'Venlo, Limburg',
        'monthly_fee': 199.0,
        'health_score': 95,
        'notes': 'Export-grade production, ISO 22000 certified',
    },
]

# ── Visit Templates ───────────────────────────────────────────────────────

INSPECTORS = ['Anna de Groot', 'Pieter Smit', 'Sophie Mulder', 'Tom Visser']

VISIT_TYPES = ['routine', 'emergency', 'follow_up', 'audit']
VISIT_TYPE_WEIGHTS = [0.50, 0.10, 0.25, 0.15]

ZONE_POOL = ['Zone A', 'Zone B', 'Zone C', 'Zone D', 'Propagation', 'Nursery',
             'Main Hall', 'Packing Area', 'Cold Storage', 'Water Treatment']

CROP_BATCHES = ['Rosso Premium #12', 'Curly Green #08', 'Arugula Rocket #05',
                'Basil Genovese #11', 'Mint Spearmint #03', 'Cherry Tomato #07',
                'Rosso Premium #14', 'Curly Green #10']

OBSERVATION_TEMPLATES = [
    'All systems operating within normal parameters. Nutrient levels stable.',
    'Minor pH drift detected in Zone {zone} — recalibrated on site. Crop health good overall.',
    'Strong vegetative growth observed across all batches. EC slightly high, adjusted down.',
    'Root health excellent. New batch transplanted into NFT channels successfully.',
    'Temperature excursion overnight (HVAC fault). Plants show minor stress but recovering.',
    'Post-harvest clean completed. Systems sanitised and ready for next cycle.',
    'Pest scouting — no issues found. Sticky traps clean. Biological controls active.',
    'Client reported yellowing leaves in Zone {zone}. Diagnosed as iron deficiency — adjusted nutrient mix.',
    'Quarterly sensor calibration completed. All readings within ±2% tolerance.',
    'Emergency call-out: pump failure in main reservoir. Replaced impeller, system restored.',
    'Follow-up from last visit — pH stability confirmed after buffer adjustment.',
    'Audit inspection: documentation up to date, HACCP logs complete, minor labelling gap noted.',
    'Excellent crop quality. Client preparing for supermarket delivery this week.',
    'Water quality test results normal. TDS within range. No pathogen detected.',
    'LED lighting array in Zone {zone} showing reduced output — replacement scheduled.',
]

ACTION_TEMPLATES = [
    'Calibrated pH and EC sensors. Topped up nutrient reservoirs.',
    'Replaced faulty float valve. Tested overflow protection.',
    'Adjusted nutrient recipe: increased Fe-EDDHA to 15 ppm.',
    'Installed new CO2 sensor in Zone {zone}. Verified data flow to dashboard.',
    'Flushed irrigation lines. Applied H2O2 sterilisation cycle.',
    'Updated firmware on environmental controller to v3.2.',
    'Replaced UV steriliser lamp (3000h service interval).',
    'Trained new staff member on daily monitoring checklist.',
    'Submitted maintenance report to client. Next visit scheduled.',
    'No corrective actions needed — systems in good order.',
]

ISSUE_DESCRIPTIONS = [
    ('pH sensor drift exceeding ±0.3', 'medium', 'sensors'),
    ('Algae buildup in reservoir', 'low', 'water_quality'),
    ('HVAC not maintaining setpoint overnight', 'high', 'environment'),
    ('Root rot symptoms in two plants', 'medium', 'crop_health'),
    ('Nutrient pump making unusual noise', 'medium', 'equipment'),
    ('EC readings inconsistent between zones', 'low', 'sensors'),
    ('Condensation on LED fixtures', 'low', 'environment'),
    ('Missing HACCP log entries for 3 days', 'medium', 'compliance'),
    ('Emergency stop button obstructed', 'high', 'safety'),
    ('Outlet filter clogged — reduced flow rate', 'medium', 'equipment'),
]

FOLLOW_UP_NOTES = [
    'Check pH stability after buffer adjustment.',
    'Verify HVAC repair holds through next cold night.',
    'Confirm nutrient deficiency resolved — re-inspect leaves.',
    'Return to replace ordered spare part.',
    'Re-audit documentation after client updates.',
    'Monitor new batch transplant survival rate.',
]


def _random_date_in_last_n_days(n: int) -> str:
    """Return a random date string (YYYY-MM-DD) within the last n days."""
    offset = random.randint(0, n)
    dt = datetime.now() - timedelta(days=offset)
    return dt.strftime('%Y-%m-%d')


def _random_sensor_snapshot() -> dict:
    """Generate a fake sensor readings snapshot."""
    return {
        'temperature_c': round(random.uniform(18.0, 28.0), 1),
        'humidity_pct': round(random.uniform(45.0, 80.0), 1),
        'ph': round(random.uniform(5.5, 6.8), 2),
        'ec_ms': round(random.uniform(0.8, 2.8), 2),
        'co2_ppm': random.randint(400, 1200),
        'light_ppfd': random.randint(150, 600),
        'water_temp_c': round(random.uniform(18.0, 24.0), 1),
    }


def _generate_issues(count: int) -> list:
    """Pick random issues from the pool."""
    chosen = random.sample(ISSUE_DESCRIPTIONS, min(count, len(ISSUE_DESCRIPTIONS)))
    return [
        {'description': desc, 'severity': sev, 'related_to': rel}
        for desc, sev, rel in chosen
    ]


def _generate_visit(client_id: int, facility_name: str) -> dict:
    """Generate a single realistic demo visit."""
    visit_type = random.choices(VISIT_TYPES, weights=VISIT_TYPE_WEIGHTS, k=1)[0]
    zone_count = random.randint(1, 4)
    zones = random.sample(ZONE_POOL, zone_count)
    batch_count = random.randint(1, 4)
    batches = random.sample(CROP_BATCHES, batch_count)
    zone_label = random.choice(zones)

    observation = random.choice(OBSERVATION_TEMPLATES).format(zone=zone_label)
    action = random.choice(ACTION_TEMPLATES).format(zone=zone_label)

    # Issues: ~40% of visits have issues
    issue_count = random.choices([0, 1, 2, 3], weights=[0.60, 0.25, 0.10, 0.05], k=1)[0]
    issues = _generate_issues(issue_count) if issue_count > 0 else []

    # Follow-up: ~30% of visits require follow-up
    needs_followup = random.random() < 0.30
    followup_date = None
    followup_notes = ''
    followup_completed = False
    if needs_followup:
        followup_date = (datetime.now() + timedelta(days=random.randint(3, 21))).strftime('%Y-%m-%d')
        followup_notes = random.choice(FOLLOW_UP_NOTES)
        # Older follow-ups may already be completed
        followup_completed = random.random() < 0.40

    rating = random.choices([1, 2, 3, 4, 5], weights=[0.02, 0.08, 0.20, 0.45, 0.25], k=1)[0]

    return {
        'visit_date': _random_date_in_last_n_days(120),  # ~4 months
        'inspector_name': random.choice(INSPECTORS),
        'client_id': client_id,
        'facility_name': facility_name,
        'visit_type': visit_type,
        'zones_inspected': zones,
        'crop_batches_checked': batches,
        'sensor_readings_snapshot': _random_sensor_snapshot(),
        'observations': observation,
        'issues_found': issues,
        'actions_taken': action,
        'follow_up_required': needs_followup,
        'follow_up_date': followup_date,
        'follow_up_notes': followup_notes,
        'follow_up_completed': followup_completed,
        'overall_rating': rating,
    }


# ── Database Operations ──────────────────────────────────────────────────

def ensure_tables(conn: sqlite3.Connection):
    """Create tables if they don't exist (same schemas as client_manager + site_visits_manager)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            service_tier TEXT DEFAULT 'bronze',
            location TEXT,
            install_date TEXT DEFAULT (date('now')),
            monthly_fee REAL DEFAULT 49.0,
            is_active INTEGER DEFAULT 1,
            health_score INTEGER DEFAULT 100,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_date TEXT NOT NULL DEFAULT (date('now')),
            inspector_name TEXT NOT NULL,
            client_id INTEGER,
            facility_name TEXT,
            visit_type TEXT NOT NULL CHECK (visit_type IN ('routine','emergency','follow_up','audit')),
            zones_inspected TEXT,
            crop_batches_checked TEXT,
            sensor_readings_snapshot TEXT,
            observations TEXT,
            issues_found TEXT,
            actions_taken TEXT,
            follow_up_required INTEGER DEFAULT 0,
            follow_up_date TEXT,
            follow_up_notes TEXT,
            follow_up_completed INTEGER DEFAULT 0,
            overall_rating INTEGER DEFAULT 3 CHECK (overall_rating BETWEEN 1 AND 5),
            photo_notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def seed_clients(conn: sqlite3.Connection) -> list:
    """Insert demo clients. Returns list of (id, company_name) tuples.
    Skips if clients already exist."""
    existing = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    if existing > 0:
        logger.info(f"\n  Clients table already has {existing} rows — skipping client seeding.")
        rows = conn.execute("SELECT id, company_name FROM clients WHERE is_active = 1").fetchall()
        return rows

    logger.info("\nSeeding 5 demo clients...")
    for c in DEMO_CLIENTS:
        conn.execute("""
            INSERT INTO clients (company_name, contact_name, contact_phone, contact_email,
                                 service_tier, location, monthly_fee, health_score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c['company_name'], c['contact_name'], c['contact_phone'], c['contact_email'],
            c['service_tier'], c['location'], c['monthly_fee'], c['health_score'], c['notes'],
        ))
    conn.commit()
    logger.info(f"  -> Inserted {len(DEMO_CLIENTS)} clients")

    return conn.execute("SELECT id, company_name FROM clients WHERE is_active = 1").fetchall()


def seed_visits(conn: sqlite3.Connection, clients: list, count: int = 35):
    """Insert demo site visits spread across clients."""
    existing = conn.execute("SELECT COUNT(*) FROM site_visits").fetchone()[0]
    if existing > 0:
        answer = input(f"\n  site_visits table already has {existing} rows. Clear and re-seed? [y/N] ").strip().lower()
        if answer != 'y':
            logger.info("  Skipped — existing visits kept.")
            return 0
        conn.execute("DELETE FROM site_visits")
        conn.commit()
        logger.info(f"  Cleared {existing} existing visits.")

    logger.info(f"\nSeeding {count} demo site visits...")
    inserted = 0
    for _ in range(count):
        client_id, facility = random.choice(clients)
        visit = _generate_visit(client_id, facility)

        conn.execute("""
            INSERT INTO site_visits (
                visit_date, inspector_name, client_id, facility_name,
                visit_type, zones_inspected, crop_batches_checked,
                sensor_readings_snapshot, observations, issues_found,
                actions_taken, follow_up_required, follow_up_date,
                follow_up_notes, follow_up_completed, overall_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            visit['visit_date'],
            visit['inspector_name'],
            visit['client_id'],
            visit['facility_name'],
            visit['visit_type'],
            json.dumps(visit['zones_inspected']),
            json.dumps(visit['crop_batches_checked']),
            json.dumps(visit['sensor_readings_snapshot']),
            visit['observations'],
            json.dumps(visit['issues_found']),
            visit['actions_taken'],
            1 if visit['follow_up_required'] else 0,
            visit['follow_up_date'],
            visit['follow_up_notes'],
            1 if visit['follow_up_completed'] else 0,
            visit['overall_rating'],
        ))
        inserted += 1

    conn.commit()
    logger.info(f"  -> Inserted {inserted} site visits across {len(clients)} clients")
    return inserted


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 55)
    logger.info("  Seed Site Visits — Demo Data")
    logger.info("=" * 55)

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"\nDatabase: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        ensure_tables(conn)
        clients = seed_clients(conn)
        if not clients:
            logger.error("No clients available — cannot seed visits.")
            sys.exit(1)
        seed_visits(conn, clients, count=35)
    finally:
        conn.close()

    logger.info("\nDone! Start the server and open http://localhost:3001/site-visits")
    logger.info("=" * 55)


if __name__ == '__main__':
    main()
