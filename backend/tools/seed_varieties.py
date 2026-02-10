#!/usr/bin/env python3
"""
Seed Varieties & Growth Stage Definitions into PostgreSQL.

Parses existing JSON configs from backend/config/variety_*.json and inserts
into crop.varieties + crop.growth_stage_definitions with expanded stages
(germination, seedling, transplant, vegetative, flowering, fruiting, maturity, harvest_ready).

Usage:
  python seed_varieties.py [--dry-run]

Requires:
  pip install psycopg2-binary
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('seed-varieties')

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'


def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', '5432')),
        dbname=os.getenv('PG_DATABASE', 'agritech'),
        user=os.getenv('PG_USER', 'agritech'),
        password=os.getenv('PG_PASSWORD', 'CHANGE_ME'),
    )


# Variety definitions with expanded growth stages
# Each variety maps to: code, name, category, scientific_name, difficulty,
# market_position, typical_cycle_days, yield_kg_per_sqm, and stages
VARIETIES = [
    {
        'code': 'rosso_premium',
        'name': 'Rosso Premium',
        'category': 'lettuce',
        'scientific_name': "Lactuca sativa 'Rosso'",
        'difficulty': 'medium',
        'market_position': 'premium',
        'typical_cycle_days': 50,
        'yield_kg_per_sqm': 4.0,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 3,
             'temp': (18, 22), 'humidity': (70, 80), 'ph': None, 'ec': None, 'light_hours': 0},
            {'order': 2, 'name': 'seedling', 'min_days': 3, 'max_days': 14,
             'temp': (20, 24), 'humidity': (50, 65), 'ph': (5.8, 6.3), 'ec': (0.8, 1.2), 'light_hours': 16},
            {'order': 3, 'name': 'transplant', 'min_days': 14, 'max_days': 16,
             'temp': (20, 24), 'humidity': (50, 65), 'ph': (5.8, 6.3), 'ec': (1.0, 1.4), 'light_hours': 14},
            {'order': 4, 'name': 'vegetative', 'min_days': 16, 'max_days': 35,
             'temp': (20, 24), 'humidity': (50, 65), 'ph': (5.8, 6.3), 'ec': (1.4, 1.8), 'light_hours': 14},
            {'order': 5, 'name': 'maturity', 'min_days': 35, 'max_days': 50,
             'temp': (20, 24), 'humidity': (50, 65), 'ph': (5.8, 6.3), 'ec': (1.6, 2.0), 'light_hours': 12},
            {'order': 6, 'name': 'harvest_ready', 'min_days': 50, 'max_days': 55,
             'temp': (20, 24), 'humidity': (50, 65), 'ph': (5.8, 6.3), 'ec': (1.6, 2.0), 'light_hours': 12},
        ]
    },
    {
        'code': 'curly_green',
        'name': 'Curly Green',
        'category': 'lettuce',
        'scientific_name': "Lactuca sativa 'Lollo Bionda'",
        'difficulty': 'easy',
        'market_position': 'standard',
        'typical_cycle_days': 45,
        'yield_kg_per_sqm': 5.0,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 3,
             'temp': (18, 22), 'humidity': (70, 80), 'ph': None, 'ec': None, 'light_hours': 0},
            {'order': 2, 'name': 'seedling', 'min_days': 3, 'max_days': 12,
             'temp': (18, 22), 'humidity': (55, 70), 'ph': (6.0, 6.5), 'ec': (0.6, 1.0), 'light_hours': 16},
            {'order': 3, 'name': 'transplant', 'min_days': 12, 'max_days': 14,
             'temp': (18, 22), 'humidity': (55, 70), 'ph': (6.0, 6.5), 'ec': (0.8, 1.2), 'light_hours': 14},
            {'order': 4, 'name': 'vegetative', 'min_days': 14, 'max_days': 30,
             'temp': (18, 22), 'humidity': (55, 70), 'ph': (6.0, 6.5), 'ec': (1.2, 1.6), 'light_hours': 14},
            {'order': 5, 'name': 'maturity', 'min_days': 30, 'max_days': 45,
             'temp': (18, 22), 'humidity': (55, 70), 'ph': (6.0, 6.5), 'ec': (1.4, 1.8), 'light_hours': 12},
            {'order': 6, 'name': 'harvest_ready', 'min_days': 45, 'max_days': 50,
             'temp': (18, 22), 'humidity': (55, 70), 'ph': (6.0, 6.5), 'ec': (1.4, 1.8), 'light_hours': 12},
        ]
    },
    {
        'code': 'arugula_rocket',
        'name': 'Arugula (Rocket)',
        'category': 'lettuce',
        'scientific_name': 'Eruca vesicaria sativa',
        'difficulty': 'easy',
        'market_position': 'premium',
        'typical_cycle_days': 30,
        'yield_kg_per_sqm': 3.0,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 3,
             'temp': (18, 24), 'humidity': (65, 80), 'ph': None, 'ec': None, 'light_hours': 0},
            {'order': 2, 'name': 'seedling', 'min_days': 3, 'max_days': 7,
             'temp': (15, 25), 'humidity': (50, 70), 'ph': (6.0, 6.5), 'ec': (0.8, 1.2), 'light_hours': 14},
            {'order': 3, 'name': 'vegetative', 'min_days': 7, 'max_days': 20,
             'temp': (15, 25), 'humidity': (50, 70), 'ph': (6.0, 6.8), 'ec': (1.2, 1.6), 'light_hours': 14},
            {'order': 4, 'name': 'maturity', 'min_days': 20, 'max_days': 30,
             'temp': (15, 25), 'humidity': (50, 70), 'ph': (6.2, 7.0), 'ec': (1.4, 1.8), 'light_hours': 12},
            {'order': 5, 'name': 'harvest_ready', 'min_days': 30, 'max_days': 35,
             'temp': (15, 25), 'humidity': (50, 70), 'ph': (6.2, 7.0), 'ec': (1.4, 1.8), 'light_hours': 12},
        ]
    },
    {
        'code': 'basil_genovese',
        'name': 'Genovese Basil',
        'category': 'herb',
        'scientific_name': "Ocimum basilicum 'Genovese'",
        'difficulty': 'medium',
        'market_position': 'premium',
        'typical_cycle_days': 35,
        'yield_kg_per_sqm': 3.5,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 5,
             'temp': (20, 28), 'humidity': (65, 80), 'ph': None, 'ec': None, 'light_hours': 0},
            {'order': 2, 'name': 'seedling', 'min_days': 5, 'max_days': 10,
             'temp': (20, 28), 'humidity': (50, 70), 'ph': (5.5, 6.0), 'ec': (0.8, 1.2), 'light_hours': 16},
            {'order': 3, 'name': 'transplant', 'min_days': 10, 'max_days': 12,
             'temp': (20, 28), 'humidity': (50, 70), 'ph': (5.8, 6.2), 'ec': (1.0, 1.4), 'light_hours': 14},
            {'order': 4, 'name': 'vegetative', 'min_days': 12, 'max_days': 25,
             'temp': (20, 28), 'humidity': (50, 70), 'ph': (5.8, 6.2), 'ec': (1.2, 1.6), 'light_hours': 14},
            {'order': 5, 'name': 'maturity', 'min_days': 25, 'max_days': 35,
             'temp': (20, 28), 'humidity': (50, 70), 'ph': (6.0, 6.4), 'ec': (1.4, 1.8), 'light_hours': 14},
            {'order': 6, 'name': 'harvest_ready', 'min_days': 35, 'max_days': 40,
             'temp': (20, 28), 'humidity': (50, 70), 'ph': (6.0, 6.4), 'ec': (1.4, 1.8), 'light_hours': 14},
        ]
    },
    {
        'code': 'mint_spearmint',
        'name': 'Spearmint',
        'category': 'herb',
        'scientific_name': 'Mentha spicata',
        'difficulty': 'easy',
        'market_position': 'premium',
        'typical_cycle_days': 30,
        'yield_kg_per_sqm': 3.0,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 10,
             'temp': (18, 25), 'humidity': (65, 80), 'ph': None, 'ec': None, 'light_hours': 0,
             'notes': 'Cutting propagation preferred'},
            {'order': 2, 'name': 'seedling', 'min_days': 10, 'max_days': 15,
             'temp': (18, 28), 'humidity': (55, 80), 'ph': (6.0, 7.0), 'ec': (1.0, 1.4), 'light_hours': 14},
            {'order': 3, 'name': 'vegetative', 'min_days': 15, 'max_days': 25,
             'temp': (18, 28), 'humidity': (55, 80), 'ph': (6.0, 7.0), 'ec': (1.2, 1.6), 'light_hours': 14},
            {'order': 4, 'name': 'maturity', 'min_days': 25, 'max_days': 30,
             'temp': (18, 28), 'humidity': (55, 80), 'ph': (6.2, 7.0), 'ec': (1.4, 1.8), 'light_hours': 14},
            {'order': 5, 'name': 'harvest_ready', 'min_days': 30, 'max_days': 35,
             'temp': (18, 28), 'humidity': (55, 80), 'ph': (6.2, 7.0), 'ec': (1.4, 1.8), 'light_hours': 14,
             'notes': 'Continuous harvest - cut above node for regrowth'},
        ]
    },
    {
        'code': 'tomato_cherry',
        'name': 'Cherry Tomato',
        'category': 'fruit',
        'scientific_name': 'Solanum lycopersicum var. cerasiforme',
        'difficulty': 'hard',
        'market_position': 'premium',
        'typical_cycle_days': 80,
        'yield_kg_per_sqm': 8.0,
        'stages': [
            {'order': 1, 'name': 'germination', 'min_days': 0, 'max_days': 7,
             'temp': (20, 25), 'humidity': (70, 80), 'ph': None, 'ec': None, 'light_hours': 16},
            {'order': 2, 'name': 'seedling', 'min_days': 7, 'max_days': 14,
             'temp': (20, 26), 'humidity': (60, 70), 'ph': (5.8, 6.3), 'ec': (1.2, 1.6), 'light_hours': 14},
            {'order': 3, 'name': 'transplant', 'min_days': 14, 'max_days': 16,
             'temp': (22, 28), 'humidity': (60, 70), 'ph': (6.0, 6.5), 'ec': (1.6, 2.0), 'light_hours': 14},
            {'order': 4, 'name': 'vegetative', 'min_days': 16, 'max_days': 35,
             'temp': (22, 28), 'humidity': (60, 70), 'ph': (6.0, 6.5), 'ec': (1.8, 2.2), 'light_hours': 14},
            {'order': 5, 'name': 'flowering', 'min_days': 35, 'max_days': 49,
             'temp': (22, 28), 'humidity': (50, 65), 'ph': (6.0, 6.5), 'ec': (2.0, 2.5), 'light_hours': 14,
             'notes': 'Hand pollination may be needed in greenhouse'},
            {'order': 6, 'name': 'fruiting', 'min_days': 49, 'max_days': 70,
             'temp': (24, 30), 'humidity': (50, 60), 'ph': (6.2, 6.8), 'ec': (2.2, 2.8), 'light_hours': 14,
             'notes': 'High EC = sweeter tomatoes'},
            {'order': 7, 'name': 'maturity', 'min_days': 70, 'max_days': 80,
             'temp': (24, 30), 'humidity': (50, 60), 'ph': (6.2, 6.8), 'ec': (2.2, 2.8), 'light_hours': 14},
            {'order': 8, 'name': 'harvest_ready', 'min_days': 80, 'max_days': 90,
             'temp': (24, 30), 'humidity': (50, 60), 'ph': (6.2, 6.8), 'ec': (2.2, 2.8), 'light_hours': 14,
             'notes': 'Harvest fully red on vine for maximum sweetness'},
        ]
    },
]


def load_variety_config(code):
    """Load the full JSON config for a variety."""
    config_file = CONFIG_DIR / f'variety_{code}.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def seed_varieties(pg_conn, dry_run=False):
    """Seed varieties and growth stage definitions."""
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    seeded = 0

    for variety in VARIETIES:
        # Load full JSON config
        config_json = load_variety_config(variety['code'])

        if dry_run:
            logger.info(f"[DRY RUN] Would seed variety: {variety['code']} ({variety['name']}) "
                        f"with {len(variety['stages'])} stages")
            seeded += 1
            continue

        # Upsert variety
        cur.execute("""
            INSERT INTO crop.varieties (code, name, category, scientific_name,
                difficulty, market_position, typical_cycle_days, yield_kg_per_sqm, config_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                scientific_name = EXCLUDED.scientific_name,
                difficulty = EXCLUDED.difficulty,
                market_position = EXCLUDED.market_position,
                typical_cycle_days = EXCLUDED.typical_cycle_days,
                yield_kg_per_sqm = EXCLUDED.yield_kg_per_sqm,
                config_json = EXCLUDED.config_json
            RETURNING id
        """, (
            variety['code'], variety['name'], variety['category'],
            variety['scientific_name'], variety['difficulty'],
            variety['market_position'], variety['typical_cycle_days'],
            variety['yield_kg_per_sqm'],
            json.dumps(config_json) if config_json else None
        ))
        variety_id = cur.fetchone()['id']

        # Delete existing stage definitions for this variety (for idempotent re-runs)
        cur.execute("""
            DELETE FROM crop.growth_stage_definitions WHERE variety_id = %s
        """, (variety_id,))

        # Insert stage definitions
        for stage in variety['stages']:
            ph_min = stage['ph'][0] if stage['ph'] else None
            ph_max = stage['ph'][1] if stage['ph'] else None
            ec_min = stage['ec'][0] if stage['ec'] else None
            ec_max = stage['ec'][1] if stage['ec'] else None
            temp_min = stage['temp'][0] if stage['temp'] else None
            temp_max = stage['temp'][1] if stage['temp'] else None
            hum_min = stage['humidity'][0] if stage['humidity'] else None
            hum_max = stage['humidity'][1] if stage['humidity'] else None

            cur.execute("""
                INSERT INTO crop.growth_stage_definitions (
                    variety_id, stage_order, stage_name,
                    min_days, max_days,
                    optimal_temp_min, optimal_temp_max,
                    optimal_humidity_min, optimal_humidity_max,
                    optimal_ph_min, optimal_ph_max,
                    optimal_ec_min, optimal_ec_max,
                    light_hours, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                variety_id, stage['order'], stage['name'],
                stage['min_days'], stage['max_days'],
                temp_min, temp_max, hum_min, hum_max,
                ph_min, ph_max, ec_min, ec_max,
                stage.get('light_hours'), stage.get('notes')
            ))

        seeded += 1
        logger.info(f"Seeded variety: {variety['code']} ({variety['name']}) "
                     f"with {len(variety['stages'])} stages")

    if not dry_run:
        pg_conn.commit()

    return seeded


def main():
    parser = argparse.ArgumentParser(description='Seed varieties into PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without writing')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Seed Varieties & Growth Stage Definitions")
    logger.info(f"Config directory: {CONFIG_DIR}")
    logger.info(f"Varieties to seed: {len(VARIETIES)}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    try:
        pg_conn = get_pg_connection()
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    count = seed_varieties(pg_conn, args.dry_run)

    pg_conn.close()

    logger.info("\n" + "=" * 60)
    logger.info(f"Seeded {count} varieties with expanded growth stages:")
    for v in VARIETIES:
        stages_str = " -> ".join(s['name'] for s in v['stages'])
        logger.info(f"  {v['code']}: {stages_str}")
    if args.dry_run:
        logger.info("  (DRY RUN - no data was written)")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
