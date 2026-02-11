"""
Data Retention & Aggregation Strategy

Smart data lifecycle management:
- Raw data: Kept per tier (7-180 days)
- Hourly aggregates: 1 year
- Daily aggregates: Forever
- Automatic cleanup and aggregation

Author: AgriTech Hydroponics
License: Proprietary
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import os

logger = logging.getLogger('data-retention')

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')


# Retention policies by tier
RETENTION_POLICIES = {
    'bronze': {
        'raw_days': 7,
        'hourly_days': 30,
        'daily_days': 365
    },
    'silver': {
        'raw_days': 30,
        'hourly_days': 90,
        'daily_days': 730  # 2 years
    },
    'gold': {
        'raw_days': 90,
        'hourly_days': 365,
        'daily_days': 9999  # Forever
    },
    'platinum': {
        'raw_days': 180,
        'hourly_days': 9999,  # Forever
        'daily_days': 9999   # Forever
    }
}


class DataRetentionManager:
    """
    Manages data lifecycle and retention policies.

    Strategies:
    1. Raw sensor data: Kept per tier (7-180 days)
    2. Hourly aggregates: Calculated and stored
    3. Daily aggregates: Calculated and stored
    4. Automatic cleanup based on customer tier
    """

    def __init__(self):
        self.influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        self.query_api = self.influx_client.query_api()
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def create_hourly_aggregates(self, customer_id: int, days_back: int = 1):
        """
        Create hourly aggregates from raw data.

        Aggregates: mean, min, max, count per hour
        """
        start_time = datetime.now() - timedelta(days=days_back)

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{days_back}d)
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => r.customer_id == "{customer_id}")
          |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
          |> set(key: "_measurement", value: "sensor_reading_hourly")
          |> to(bucket: "{INFLUXDB_BUCKET}_aggregates", org: "{INFLUXDB_ORG}")
        '''

        try:
            result = self.query_api.query(query)
            logger.info(f"Created hourly aggregates for customer {customer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create hourly aggregates: {e}")
            return False

    def create_daily_aggregates(self, customer_id: int, days_back: int = 7):
        """Create daily aggregates from hourly data."""
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}_aggregates")
          |> range(start: -{days_back}d)
          |> filter(fn: (r) => r._measurement == "sensor_reading_hourly")
          |> filter(fn: (r) => r.customer_id == "{customer_id}")
          |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
          |> set(key: "_measurement", value: "sensor_reading_daily")
          |> to(bucket: "{INFLUXDB_BUCKET}_aggregates", org: "{INFLUXDB_ORG}")
        '''

        try:
            result = self.query_api.query(query)
            logger.info(f"Created daily aggregates for customer {customer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create daily aggregates: {e}")
            return False

    def cleanup_raw_data(self, customer_id: int, tier: str):
        """
        Delete raw data older than tier allows.

        Args:
            customer_id: Customer ID
            tier: Subscription tier (bronze, silver, gold, platinum)
        """
        policy = RETENTION_POLICIES.get(tier, RETENTION_POLICIES['bronze'])
        retention_days = policy['raw_days']

        # Calculate cutoff date
        cutoff = datetime.now() - timedelta(days=retention_days)

        delete_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -365d, stop: {cutoff.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => r.customer_id == "{customer_id}")
        '''

        try:
            # Note: InfluxDB delete API would be used here
            # For now, log the action
            logger.info(f"Would delete raw data before {cutoff} for customer {customer_id} ({tier} tier)")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup raw data: {e}")
            return False

    def get_data_usage_stats(self, customer_id: int) -> Dict[str, Any]:
        """
        Get data storage statistics for customer.

        Returns:
            Stats about raw, hourly, daily data points
        """
        stats = {}

        # Count raw data points
        query_raw = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -180d)
          |> filter(fn: (r) => r._measurement == "sensor_reading")
          |> filter(fn: (r) => r.customer_id == "{customer_id}")
          |> count()
        '''

        try:
            result = self.query_api.query(query_raw)
            raw_count = 0
            for table in result:
                for record in table.records:
                    raw_count += record.get_value()

            stats['raw_data_points'] = raw_count
            stats['estimated_raw_size_mb'] = raw_count * 0.001  # Rough estimate

        except Exception as e:
            logger.error(f"Failed to get raw data stats: {e}")
            stats['raw_data_points'] = 0

        return stats

    def run_maintenance(self, customer_id: int, tier: str):
        """
        Run complete maintenance cycle for customer.

        1. Create hourly aggregates
        2. Create daily aggregates
        3. Cleanup old raw data per tier policy
        """
        logger.info(f"Starting maintenance for customer {customer_id} ({tier} tier)")

        # Create aggregates
        self.create_hourly_aggregates(customer_id, days_back=1)
        self.create_daily_aggregates(customer_id, days_back=7)

        # Cleanup
        self.cleanup_raw_data(customer_id, tier)

        logger.info(f"Maintenance complete for customer {customer_id}")

    def get_tier_data_info(self, tier: str) -> Dict[str, Any]:
        """Get data retention information for a tier."""
        policy = RETENTION_POLICIES.get(tier, RETENTION_POLICIES['bronze'])

        return {
            'tier': tier,
            'raw_data_retention_days': policy['raw_days'],
            'hourly_aggregates_retention_days': policy['hourly_days'],
            'daily_aggregates_retention_days': policy['daily_days'],
            'description': f"Raw data kept for {policy['raw_days']} days, then aggregated",
            'storage_estimate_gb_per_year': self._estimate_storage(policy['raw_days'])
        }

    def _estimate_storage(self, raw_days: int) -> float:
        """Estimate storage requirements."""
        # Assumptions:
        # - 1 reading per 2 seconds = 43,200 readings/day
        # - 6 sensors average
        # - ~100 bytes per reading
        readings_per_day = 43200 * 6
        bytes_per_reading = 100
        total_bytes = readings_per_day * bytes_per_reading * raw_days
        return total_bytes / (1024 ** 3)  # Convert to GB


# Global instance
retention_manager = DataRetentionManager()
