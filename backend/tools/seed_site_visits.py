"""
Seed script: populates the database with demo site visits + clients
so the Site Visits Backoffice dashboard looks full when demoing.

Usage:
    cd backend/api
    python ../tools/seed_site_visits.py
"""

import sqlite3
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'agritech.db'

# ── Demo Clients ───────────────────────────────────────────────────
CLIENTS = [
    ("Horta Verde Lda", "Miguel Santos", "+351 912 345 678", "miguel@hortaverde.pt", "gold", "Lisbon", 499.0),
    ("BioGrow Porto", "Ana Ferreira", "+351 923 456 789", "ana@biogrow.pt", "silver", "Porto", 199.0),
    ("FreshLeaf Algarve", "Carlos Mendes", "+351 934 567 890", "carlos@freshleaf.pt", "bronze", "Faro", 49.0),
    ("AquaFarm Coimbra", "Sofia Costa", "+351 945 678 901", "sofia@aquafarm.pt", "silver", "Coimbra", 199.0),
    ("GreenTech Braga", "Pedro Oliveira", "+351 956 789 012", "pedro@greentech.pt", "gold", "Braga", 499.0),
]

INSPECTORS = ["Ana Ferreira", "Marco Silva", "Rita Lopes", "Joao Pereira", "Carla Nunes"]

FACILITIES = [
    "Greenhouse A", "Greenhouse B", "Vertical Farm Unit 1",
    "Vertical Farm Unit 2", "Nursery Wing", "Main Production Hall",
    "Seedling Room", "Packing Area",
]

ZONES = ["Zone A", "Zone B", "Zone C", "Zone D", "NFT Row 1", "NFT Row 2", "DWC Tanks", "Seedling Trays"]

OBSERVATIONS_POOL = [
    "All systems running normally. Nutrient levels within optimal range.",
    "Minor pest activity detected near intake vents. Recommended IPM treatment.",
    "Excellent growth rates observed on basil batches. pH stable at 5.8.",
    "Some yellowing on lower leaves of lettuce batch. Possible nitrogen deficiency.",
    "Temperature spikes noted around 14:00. AC response time acceptable.",
    "Humidity sensors in Zone B reading 3% higher than portable reference meter.",
    "Root zone healthy across all DWC tanks. Dissolved oxygen at 7.2 mg/L.",
    "Light distribution uneven in NFT Row 2. Recommend adjusting LED height.",
    "Germination rate for arugula batch at 94%, above the 85% target.",
    "Drain-to-waste ratio slightly high at 28%. Adjust irrigation schedule.",
    "New crop transplanted successfully. All seedlings showing vigorous growth.",
    "Client reports intermittent pH probe readings. Probe cleaned and recalibrated on-site.",
]

ISSUES_POOL = [
    {"description": "pH sensor drift detected - reading 0.3 above reference", "severity": "medium", "related_to": "sensor"},
    {"description": "Temperature exceeded 30C for 45 minutes", "severity": "high", "related_to": "infrastructure"},
    {"description": "Aphids found on basil plants near ventilation intake", "severity": "medium", "related_to": "crop"},
    {"description": "EC probe not responding intermittently", "severity": "high", "related_to": "sensor"},
    {"description": "Minor water leak at NFT channel junction", "severity": "low", "related_to": "infrastructure"},
    {"description": "Algae buildup in reservoir tank", "severity": "low", "related_to": "infrastructure"},
    {"description": "Nutrient burn visible on tomato leaf tips", "severity": "medium", "related_to": "crop"},
    {"description": "Backup pump failed during test cycle", "severity": "critical", "related_to": "infrastructure"},
    {"description": "Light timer malfunction - LEDs stayed on overnight", "severity": "high", "related_to": "infrastructure"},
    {"description": "Root rot starting on 2 lettuce plants in DWC", "severity": "medium", "related_to": "crop"},
]

ACTIONS_POOL = [
    "Recalibrated pH and EC probes. Verified against reference solution.",
    "Applied neem oil treatment to affected plants. Installed sticky traps.",
    "Adjusted AC setpoints and verified response times. System functioning correctly.",
    "Replaced faulty sensor cable. Readings now stable.",
    "Tightened junction fitting. No further leaks observed after 30 min monitoring.",
    "Cleaned reservoir and replaced nutrient solution. Added H2O2 treatment.",
    "Adjusted nutrient concentration. Flushed system with fresh solution.",
    "Ordered replacement pump. Temporary fix applied with bypass valve.",
    "Reset timer controller. Verified correct light schedule programmed.",
    "Removed affected plants. Increased dissolved oxygen with air stones.",
    "Performed routine calibration on all sensors. All within spec.",
    "Trained client staff on daily monitoring procedures.",
]

FOLLOWUP_NOTES = [
    "Recheck pH probe accuracy after 7 days of operation",
    "Verify pest treatment effectiveness - look for new activity",
    "Confirm replacement pump has been installed and tested",
    "Re-measure nutrient levels after adjustment period",
    "Check if temperature spikes have been resolved with new AC settings",
    "Verify sensor replacement is reading correctly",
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print(f"Database: {DB_PATH}")
    print()

    # ── 1. Seed clients if table is empty ──────────────────────────
    existing_clients = conn.execute("SELECT COUNT(*) as c FROM clients").fetchone()['c']
    if existing_clients == 0:
        print("Seeding 5 demo clients...")
        for name, contact, phone, email, tier, location, fee in CLIENTS:
            health = random.randint(65, 100)
            conn.execute("""
                INSERT INTO clients (company_name, contact_name, contact_phone, contact_email,
                                     service_tier, location, monthly_fee, health_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, contact, phone, email, tier, location, fee, health))
        conn.commit()
        print(f"  -> Inserted 5 clients")
    else:
        print(f"Clients table already has {existing_clients} records, skipping.")

    # Get client IDs for visits
    client_ids = [r['id'] for r in conn.execute("SELECT id FROM clients WHERE is_active = 1").fetchall()]
    if not client_ids:
        print("ERROR: No clients found. Cannot seed visits.")
        conn.close()
        return

    # ── 2. Ensure site_visits table exists ─────────────────────────
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

    # Check if already seeded
    existing_visits = conn.execute("SELECT COUNT(*) as c FROM site_visits").fetchone()['c']
    if existing_visits > 0:
        print(f"Site visits table already has {existing_visits} records.")
        resp = input("Clear and re-seed? (y/N): ").strip().lower()
        if resp != 'y':
            print("Skipping visit seeding.")
            conn.close()
            return
        conn.execute("DELETE FROM site_visits")
        conn.commit()
        print("  -> Cleared existing visits.")

    # ── 3. Generate 35 demo visits over the last 4 months ──────────
    print("Seeding 35 demo site visits...")
    now = datetime.now()
    visit_types = ['routine', 'routine', 'routine', 'emergency', 'follow_up', 'audit']  # weighted toward routine

    for i in range(35):
        days_ago = random.randint(0, 120)
        visit_date = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        created_at = (now - timedelta(days=days_ago, hours=random.randint(0, 12))).strftime('%Y-%m-%d %H:%M:%S')

        inspector = random.choice(INSPECTORS)
        client_id = random.choice(client_ids)
        facility = random.choice(FACILITIES)
        visit_type = random.choice(visit_types)

        zones = random.sample(ZONES, k=random.randint(1, 4))
        crop_ids = random.sample(range(1, 7), k=random.randint(0, 3))

        # Fake sensor snapshot (realistic values)
        snapshot = {
            "temperature": round(random.uniform(19.0, 28.0), 1),
            "humidity": round(random.uniform(55.0, 78.0), 1),
            "pH": round(random.uniform(5.4, 6.6), 1),
            "ec": round(random.uniform(1.0, 2.4), 1),
        }

        observations = random.choice(OBSERVATIONS_POOL)
        actions = random.choice(ACTIONS_POOL)

        # Some visits have issues (60%)
        issues = []
        if random.random() < 0.6:
            issue_count = random.randint(1, 3)
            issues = random.sample(ISSUES_POOL, k=min(issue_count, len(ISSUES_POOL)))

        # Rating: mostly 3-5, occasionally lower
        rating = random.choices([1, 2, 3, 4, 5], weights=[2, 5, 20, 40, 33])[0]

        # Follow-up: ~30% of visits
        follow_up = random.random() < 0.30
        follow_up_completed = 0
        follow_up_date = None
        follow_up_notes = ""
        if follow_up:
            follow_up_date = (now - timedelta(days=days_ago) + timedelta(days=random.randint(7, 21))).strftime('%Y-%m-%d')
            follow_up_notes = random.choice(FOLLOWUP_NOTES)
            # If the follow-up date is in the past, 70% chance it's completed
            if follow_up_date < now.strftime('%Y-%m-%d') and random.random() < 0.7:
                follow_up_completed = 1

        conn.execute("""
            INSERT INTO site_visits (
                visit_date, inspector_name, client_id, facility_name,
                visit_type, zones_inspected, crop_batches_checked,
                sensor_readings_snapshot, observations, issues_found,
                actions_taken, follow_up_required, follow_up_date,
                follow_up_notes, follow_up_completed, overall_rating,
                photo_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            visit_date, inspector, client_id, facility,
            visit_type, json.dumps(zones), json.dumps(crop_ids),
            json.dumps(snapshot), observations, json.dumps(issues),
            actions, 1 if follow_up else 0, follow_up_date,
            follow_up_notes, follow_up_completed, rating,
            f"IMG_{1000 + i}: {facility} overview" if random.random() < 0.4 else "",
            created_at, created_at,
        ))

    conn.commit()
    conn.close()

    print(f"  -> Inserted 35 site visits across {len(client_ids)} clients")
    print()
    print("Done! Start the server and open http://localhost:3001/site-visits")


if __name__ == "__main__":
    seed()
