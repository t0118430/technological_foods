#!/usr/bin/env python3
"""
InfluxDB → PostgreSQL ETL Runner.

Bridges InfluxDB downsampled buckets (hydroponics_hourly, hydroponics_daily)
to PostgreSQL BI tables (bi.hourly_sensor_agg, bi.daily_sensor_agg).

Usage:
  python run_etl.py hourly              # Process latest hourly aggregates
  python run_etl.py daily               # Process latest daily aggregates
  python run_etl.py full                # Hourly + daily + cleanup
  python run_etl.py backfill --days 30  # Backfill historical data
  python run_etl.py cleanup             # Purge old hourly data (>90 days)
  python run_etl.py status              # Show ETL status & watermarks

Options:
  --dry-run    Simulate without writing to PostgreSQL
  --days N     Number of days for backfill (default: 30)
  --hours N    Lookback hours for hourly processing (default: 3)

Requires:
  pip install psycopg2-binary influxdb-client
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add backend/api to path so we can import the ETL processor
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'api'))

# Load .env
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('run-etl')


def cmd_hourly(args):
    """Process latest hourly aggregates."""
    from etl import etl_processor
    result = etl_processor.process_hourly(lookback_hours=args.hours, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    return 0 if 'error' not in result else 1


def cmd_daily(args):
    """Process latest daily aggregates."""
    from etl import etl_processor
    result = etl_processor.process_daily(lookback_days=args.days, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    return 0 if 'error' not in result else 1


def cmd_full(args):
    """Run hourly + daily + cleanup."""
    from etl import etl_processor
    result = etl_processor.run_full_cycle(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    errors = [k for k, v in result.items() if isinstance(v, dict) and 'error' in v]
    return 0 if not errors else 1


def cmd_backfill(args):
    """Backfill historical data."""
    from etl import etl_processor
    logger.info(f"Backfilling {args.days} days of historical data...")
    result = etl_processor.backfill(days=args.days, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_cleanup(args):
    """Purge old hourly data."""
    from etl import etl_processor
    result = etl_processor.cleanup_old_hourly(retention_days=args.retention_days)
    print(json.dumps(result, indent=2, default=str))
    return 0 if 'error' not in result else 1


def cmd_status(args):
    """Show ETL status and watermarks."""
    from etl import etl_processor
    status = etl_processor.get_status()
    print(json.dumps(status, indent=2, default=str))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='InfluxDB -> PostgreSQL ETL Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_etl.py hourly              Process latest hourly aggregates
  python run_etl.py daily               Process latest daily aggregates
  python run_etl.py full                Hourly + daily + cleanup
  python run_etl.py backfill --days 30  Backfill 30 days of history
  python run_etl.py cleanup             Purge old hourly data (>90 days)
  python run_etl.py status              Show ETL status & watermarks
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='ETL command to run')

    # hourly
    p_hourly = subparsers.add_parser('hourly', help='Process latest hourly aggregates')
    p_hourly.add_argument('--dry-run', action='store_true', help='Simulate without writing')
    p_hourly.add_argument('--hours', type=int, default=3, help='Lookback hours (default: 3)')

    # daily
    p_daily = subparsers.add_parser('daily', help='Process latest daily aggregates')
    p_daily.add_argument('--dry-run', action='store_true', help='Simulate without writing')
    p_daily.add_argument('--days', type=int, default=2, help='Lookback days (default: 2)')

    # full
    p_full = subparsers.add_parser('full', help='Hourly + daily + cleanup')
    p_full.add_argument('--dry-run', action='store_true', help='Simulate without writing')

    # backfill
    p_backfill = subparsers.add_parser('backfill', help='Backfill historical data')
    p_backfill.add_argument('--days', type=int, default=30, help='Number of days to backfill (default: 30)')
    p_backfill.add_argument('--dry-run', action='store_true', help='Simulate without writing')

    # cleanup
    p_cleanup = subparsers.add_parser('cleanup', help='Purge old hourly data')
    p_cleanup.add_argument('--retention-days', type=int, default=90,
                           help='Delete data older than N days (default: 90)')

    # status
    subparsers.add_parser('status', help='Show ETL status & watermarks')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    logger.info("=" * 60)
    logger.info("InfluxDB -> PostgreSQL ETL Runner")
    logger.info(f"Command: {args.command}")
    if hasattr(args, 'dry_run') and args.dry_run:
        logger.info("Mode: DRY RUN (no data will be written)")
    logger.info("=" * 60)

    commands = {
        'hourly': cmd_hourly,
        'daily': cmd_daily,
        'full': cmd_full,
        'backfill': cmd_backfill,
        'cleanup': cmd_cleanup,
        'status': cmd_status,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
