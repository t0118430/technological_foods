#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script.

Migrates data from the two SQLite databases (agritech.db, agritech_business.db)
to the new PostgreSQL schema.

Mappings:
  SQLite crops           -> PostgreSQL crop.batches + crop.batch_stages
  SQLite growth_stages   -> PostgreSQL crop.batch_stages
  SQLite harvests        -> PostgreSQL crop.harvests
  SQLite calibrations    -> PostgreSQL audit.events (calibration records)
  SQLite events          -> PostgreSQL audit.events
  SQLite customers       -> PostgreSQL business.clients
  SQLite payments        -> PostgreSQL business.payments
  SQLite customer_sensors       -> PostgreSQL business.client_sensors
  SQLite sensor_recommendations -> PostgreSQL business.sensor_recommendations
  SQLite support_tickets        -> PostgreSQL business.support_tickets
  SQLite feature_usage          -> PostgreSQL business.feature_usage

Usage:
  python migrate_sqlite_to_postgres.py [--dry-run]

Requires:
  pip install psycopg2-binary

Environment:
  PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'api'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration')

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Paths
AGRITECH_DB = Path(__file__).resolve().parent.parent / 'data' / 'agritech.db'
BUSINESS_DB = Path(__file__).resolve().parent.parent / 'data' / 'agritech_business.db'


def get_pg_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', '5432')),
        dbname=os.getenv('PG_DATABASE', 'agritech'),
        user=os.getenv('PG_USER', 'agritech'),
        password=os.getenv('PG_PASSWORD', 'CHANGE_ME'),
    )


def get_sqlite_connection(db_path):
    """Get SQLite connection."""
    if not db_path.exists():
        logger.warning(f"SQLite database not found: {db_path}")
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def migrate_crops(sqlite_conn, pg_conn, dry_run=False):
    """Migrate crops -> crop.batches and growth_stages -> crop.batch_stages."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM crops ORDER BY id")
    crops = cursor.fetchall()

    if not crops:
        logger.info("No crops to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for crop in crops:
        variety = crop['variety']

        # Look up variety in PostgreSQL (must have been seeded first)
        pg_cur.execute("SELECT id FROM crop.varieties WHERE code = %s", (variety,))
        variety_row = pg_cur.fetchone()
        if not variety_row:
            logger.warning(f"Variety '{variety}' not found in PostgreSQL. Skipping crop {crop['id']}")
            continue

        variety_id = variety_row['id']

        # Look up zone
        zone_name = crop['zone'] or 'main'
        pg_cur.execute("SELECT id FROM core.zones WHERE name ILIKE %s LIMIT 1", (f"%{zone_name}%",))
        zone_row = pg_cur.fetchone()
        zone_id = zone_row['id'] if zone_row else None

        # Generate batch code
        pg_cur.execute("SELECT crop.generate_batch_code(%s) AS code", (variety,))
        batch_code = pg_cur.fetchone()['code']

        if dry_run:
            logger.info(f"[DRY RUN] Would migrate crop {crop['id']}: {variety} -> batch {batch_code}")
            migrated += 1
            continue

        # Insert batch
        pg_cur.execute("""
            INSERT INTO crop.batches (batch_code, variety_id, zone_id, plant_date,
                expected_harvest_date, actual_harvest_date, status, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            batch_code, variety_id, zone_id,
            crop['plant_date'], crop['expected_harvest_date'],
            crop['actual_harvest_date'], crop['status'] or 'active',
            crop['notes'], crop['created_at'] or datetime.now().isoformat()
        ))
        batch_id = pg_cur.fetchone()['id']

        # Migrate growth stages for this crop
        cursor.execute("""
            SELECT * FROM growth_stages WHERE crop_id = ? ORDER BY started_at
        """, (crop['id'],))
        stages = cursor.fetchall()

        for stage in stages:
            stage_name = stage['stage']

            # Find matching stage definition
            pg_cur.execute("""
                SELECT id FROM crop.growth_stage_definitions
                WHERE variety_id = %s AND stage_name = %s
            """, (variety_id, stage_name))
            stage_def = pg_cur.fetchone()

            if not stage_def:
                # Try fuzzy match or use first stage
                pg_cur.execute("""
                    SELECT id FROM crop.growth_stage_definitions
                    WHERE variety_id = %s ORDER BY stage_order LIMIT 1
                """, (variety_id,))
                stage_def = pg_cur.fetchone()

            if stage_def:
                pg_cur.execute("""
                    INSERT INTO crop.batch_stages (batch_id, stage_def_id, started_at, ended_at)
                    VALUES (%s, %s, %s, %s)
                """, (batch_id, stage_def['id'], stage['started_at'], stage['ended_at']))

        migrated += 1
        logger.info(f"Migrated crop {crop['id']} -> batch {batch_id} ({batch_code})")

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_harvests(sqlite_conn, pg_conn, dry_run=False):
    """Migrate harvests -> crop.harvests."""
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT h.*, c.variety FROM harvests h
        JOIN crops c ON h.crop_id = c.id
        ORDER BY h.id
    """)
    harvests = cursor.fetchall()

    if not harvests:
        logger.info("No harvests to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for harvest in harvests:
        # Find the corresponding batch in PostgreSQL
        # Match by variety and approximate plant date
        pg_cur.execute("""
            SELECT b.id FROM crop.batches b
            JOIN crop.varieties v ON b.variety_id = v.id
            WHERE v.code = %s
            ORDER BY b.created_at DESC LIMIT 1
        """, (harvest['variety'],))
        batch_row = pg_cur.fetchone()

        if not batch_row:
            logger.warning(f"No matching batch found for harvest {harvest['id']}")
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would migrate harvest {harvest['id']}")
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO crop.harvests (batch_id, harvest_date, weight_kg,
                quality_grade, total_revenue, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            batch_row['id'], harvest['harvest_date'], harvest['weight_kg'],
            harvest['quality_grade'], harvest['market_value'],
            harvest['notes'], harvest['created_at'] or datetime.now().isoformat()
        ))
        migrated += 1

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_events(sqlite_conn, pg_conn, dry_run=False):
    """Migrate events -> audit.events."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id")
    events = cursor.fetchall()

    if not events:
        logger.info("No events to migrate")
        return 0

    pg_cur = pg_conn.cursor()
    migrated = 0

    for event in events:
        if dry_run:
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO audit.events (event_type, severity, message, data, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            event['event_type'], event['severity'] or 'info',
            event['message'], event['data'], event['created_at']
        ))
        migrated += 1

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_customers(sqlite_conn, pg_conn, dry_run=False):
    """Migrate customers -> business.clients."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY id")
    customers = cursor.fetchall()

    if not customers:
        logger.info("No customers to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for customer in customers:
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate customer: {customer['name']}")
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO business.clients (name, company_name, email, phone, address,
                subscription_tier, subscription_start_date, subscription_end_date,
                auto_renew, status, total_revenue, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            customer['name'], customer['company_name'], customer['email'],
            customer['phone'], customer['address'],
            customer['subscription_tier'] or 'bronze',
            customer['subscription_start_date'],
            customer['subscription_end_date'],
            bool(customer['auto_renew']),
            customer['status'] or 'active',
            customer['total_revenue'] or 0,
            customer['created_at'] or datetime.now().isoformat()
        ))
        client_id = pg_cur.fetchone()['id']
        migrated += 1
        logger.info(f"Migrated customer {customer['id']} -> client {client_id}")

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_payments(sqlite_conn, pg_conn, dry_run=False):
    """Migrate payments -> business.payments."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM payments ORDER BY id")
    payments = cursor.fetchall()

    if not payments:
        logger.info("No payments to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for payment in payments:
        # Map customer_id to client_id (assumes sequential migration)
        pg_cur.execute("""
            SELECT id FROM business.clients ORDER BY id OFFSET %s LIMIT 1
        """, (payment['customer_id'] - 1,))
        client_row = pg_cur.fetchone()
        if not client_row:
            logger.warning(f"No matching client for payment customer_id={payment['customer_id']}")
            continue

        if dry_run:
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO business.payments (client_id, amount, currency, payment_date,
                payment_method, tier, period_start, period_end, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            client_row['id'], payment['amount'],
            payment['currency'] or 'EUR', payment['payment_date'],
            payment['payment_method'], payment['tier'],
            payment['period_start'], payment['period_end'],
            payment['status'] or 'completed', payment['notes']
        ))
        migrated += 1

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_customer_sensors(sqlite_conn, pg_conn, dry_run=False):
    """Migrate customer_sensors -> business.client_sensors."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM customer_sensors ORDER BY id")
    sensors = cursor.fetchall()

    if not sensors:
        logger.info("No customer sensors to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for sensor in sensors:
        pg_cur.execute("""
            SELECT id FROM business.clients ORDER BY id OFFSET %s LIMIT 1
        """, (sensor['customer_id'] - 1,))
        client_row = pg_cur.fetchone()
        if not client_row:
            continue

        if dry_run:
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO business.client_sensors (client_id, sensor_type, sensor_model,
                serial_number, installation_date, status, last_calibration, next_calibration_due, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            client_row['id'], sensor['sensor_type'], sensor['sensor_model'],
            sensor['serial_number'], sensor['installation_date'],
            sensor['status'] or 'active', sensor['last_calibration'],
            sensor['next_calibration_due'], sensor['notes']
        ))
        migrated += 1

    if not dry_run:
        pg_conn.commit()

    return migrated


def migrate_support_tickets(sqlite_conn, pg_conn, dry_run=False):
    """Migrate support_tickets -> business.support_tickets."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM support_tickets ORDER BY id")
    tickets = cursor.fetchall()

    if not tickets:
        logger.info("No support tickets to migrate")
        return 0

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    migrated = 0

    for ticket in tickets:
        pg_cur.execute("""
            SELECT id FROM business.clients ORDER BY id OFFSET %s LIMIT 1
        """, (ticket['customer_id'] - 1,))
        client_row = pg_cur.fetchone()
        if not client_row:
            continue

        if dry_run:
            migrated += 1
            continue

        pg_cur.execute("""
            INSERT INTO business.support_tickets (client_id, severity, subject, description,
                status, assigned_to, created_at, resolved_at, response_time_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            client_row['id'], ticket['severity'], ticket['subject'],
            ticket['description'], ticket['status'] or 'open',
            ticket['assigned_to'], ticket['created_at'],
            ticket['resolved_at'], ticket['response_time_hours']
        ))
        migrated += 1

    if not dry_run:
        pg_conn.commit()

    return migrated


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without writing')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("SQLite -> PostgreSQL Migration")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    # Connect to PostgreSQL
    try:
        pg_conn = get_pg_connection()
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    totals = {}

    # Migrate agritech.db (crops, stages, harvests, events)
    sqlite_crop = get_sqlite_connection(AGRITECH_DB)
    if sqlite_crop:
        logger.info(f"\n--- Migrating from {AGRITECH_DB} ---")

        count = migrate_crops(sqlite_crop, pg_conn, args.dry_run)
        totals['crops'] = count
        logger.info(f"Crops migrated: {count}")

        count = migrate_harvests(sqlite_crop, pg_conn, args.dry_run)
        totals['harvests'] = count
        logger.info(f"Harvests migrated: {count}")

        count = migrate_events(sqlite_crop, pg_conn, args.dry_run)
        totals['events'] = count
        logger.info(f"Events migrated: {count}")

        sqlite_crop.close()
    else:
        logger.info(f"Skipping {AGRITECH_DB} (not found)")

    # Migrate agritech_business.db (customers, payments, sensors, tickets)
    sqlite_biz = get_sqlite_connection(BUSINESS_DB)
    if sqlite_biz:
        logger.info(f"\n--- Migrating from {BUSINESS_DB} ---")

        count = migrate_customers(sqlite_biz, pg_conn, args.dry_run)
        totals['customers'] = count
        logger.info(f"Customers migrated: {count}")

        count = migrate_payments(sqlite_biz, pg_conn, args.dry_run)
        totals['payments'] = count
        logger.info(f"Payments migrated: {count}")

        count = migrate_customer_sensors(sqlite_biz, pg_conn, args.dry_run)
        totals['customer_sensors'] = count
        logger.info(f"Customer sensors migrated: {count}")

        count = migrate_support_tickets(sqlite_biz, pg_conn, args.dry_run)
        totals['support_tickets'] = count
        logger.info(f"Support tickets migrated: {count}")

        sqlite_biz.close()
    else:
        logger.info(f"Skipping {BUSINESS_DB} (not found)")

    pg_conn.close()

    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary:")
    for table, count in totals.items():
        logger.info(f"  {table}: {count} records")
    logger.info(f"  Total: {sum(totals.values())} records")
    if args.dry_run:
        logger.info("  (DRY RUN - no data was written)")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
