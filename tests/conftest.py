"""
Shared pytest fixtures for PostgreSQL integration tests.

Requires a running PostgreSQL instance (e.g. via Docker).
Connection parameters are read from environment variables with sensible defaults
matching the docker-compose.yml configuration.
"""

import os
import pytest

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Skip all tests in this directory if psycopg2 is not installed
pytestmark = pytest.mark.skipif(not HAS_PSYCOPG2, reason="psycopg2 not installed")

SITE_VISITS_DDL = """
CREATE TABLE IF NOT EXISTS business.site_visits (
    id SERIAL PRIMARY KEY,
    visit_date DATE NOT NULL DEFAULT CURRENT_DATE,
    inspector_name VARCHAR(255) NOT NULL,
    client_id INTEGER REFERENCES business.clients(id),
    facility_name VARCHAR(255),
    visit_type VARCHAR(20) NOT NULL CHECK (visit_type IN ('routine','emergency','follow_up','audit')),
    zones_inspected JSONB DEFAULT '[]',
    crop_batches_checked JSONB DEFAULT '[]',
    sensor_readings_snapshot JSONB DEFAULT '{}',
    observations TEXT,
    issues_found JSONB DEFAULT '[]',
    actions_taken TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    follow_up_notes TEXT,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    overall_rating INTEGER DEFAULT 3 CHECK (overall_rating BETWEEN 1 AND 5),
    photo_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

SITE_VISITS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_biz_site_visits_date ON business.site_visits(visit_date);",
    "CREATE INDEX IF NOT EXISTS idx_biz_site_visits_client ON business.site_visits(client_id);",
    "CREATE INDEX IF NOT EXISTS idx_biz_site_visits_type ON business.site_visits(visit_type);",
    "CREATE INDEX IF NOT EXISTS idx_biz_site_visits_followup ON business.site_visits(follow_up_required, follow_up_completed);",
]


def get_pg_connection():
    """Create a raw psycopg2 connection from env vars."""
    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', '5432')),
        dbname=os.getenv('PG_DATABASE', 'agritech'),
        user=os.getenv('PG_USER', 'agritech'),
        password=os.getenv('PG_PASSWORD', 'CHANGE_ME'),
    )


@pytest.fixture(scope="session")
def ensure_schema():
    """Ensure business schema and site_visits table exist. Runs once per session."""
    try:
        conn = get_pg_connection()
    except psycopg2.OperationalError:
        pytest.skip("PostgreSQL not available")

    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS core;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS business;")
        # Ensure the updated_at trigger function exists
        cur.execute("""
            CREATE OR REPLACE FUNCTION core.update_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        # Ensure clients table exists (site_visits FK target)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS business.clients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                company_name VARCHAR(255),
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(50),
                address TEXT,
                subscription_tier VARCHAR(50) DEFAULT 'bronze',
                subscription_start_date DATE NOT NULL DEFAULT CURRENT_DATE,
                subscription_end_date DATE,
                auto_renew BOOLEAN DEFAULT TRUE,
                status VARCHAR(20) DEFAULT 'active',
                total_revenue DECIMAL(12,2) DEFAULT 0,
                health_score INTEGER DEFAULT 100,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        # Create site_visits table
        cur.execute(SITE_VISITS_DDL)
        for idx_sql in SITE_VISITS_INDEXES:
            cur.execute(idx_sql)
        # Ensure trigger exists (ignore if already exists)
        cur.execute("""
            DO $$ BEGIN
                CREATE TRIGGER trg_site_visits_updated
                    BEFORE UPDATE ON business.site_visits
                    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at();
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """)
    conn.close()


@pytest.fixture(scope="function")
def pg_db(ensure_schema):
    """Yield a PostgresDatabase instance connected to the test DB.

    Cleans up site_visits after each test function.
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))
    from pg_database import PostgresDatabase

    db = PostgresDatabase()
    if not db.available:
        pytest.skip("PostgreSQL not available")

    yield db

    # Cleanup: remove all site_visits (but keep clients for other tests)
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM business.site_visits")

    db.close()


@pytest.fixture(scope="function")
def seed_clients(pg_db):
    """Insert 3 test clients and yield their IDs. Cleans up after."""
    import time
    ts = int(time.time() * 1000)
    client_ids = []

    with pg_db.get_connection() as conn:
        for i, (name, email) in enumerate([
            ("Test Client A", f"test_a_{ts}@example.com"),
            ("Test Client B", f"test_b_{ts}@example.com"),
            ("Test Client C", f"test_c_{ts}@example.com"),
        ]):
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO business.clients
                        (name, company_name, email, subscription_tier,
                         subscription_start_date, status, health_score)
                    VALUES (%s, %s, %s, 'silver', CURRENT_DATE, 'active', 80)
                    RETURNING id
                """, (name, f"Company {chr(65 + i)}", email))
                client_ids.append(cur.fetchone()[0])

    yield client_ids

    # Cleanup: delete visits first (FK), then clients
    with pg_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM business.site_visits WHERE client_id = ANY(%s)",
                (client_ids,)
            )
            cur.execute(
                "DELETE FROM business.clients WHERE id = ANY(%s)",
                (client_ids,)
            )
