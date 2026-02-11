#!/usr/bin/env python3
"""
Quick test script to send a notification with real sensor data from InfluxDB.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / 'api'))

from notifications.notification_service import notifier

# InfluxDB Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')

print("=" * 60)
print("Testing Notification with REAL Arduino Sensor Data")
print("=" * 60)

# Query latest data from InfluxDB
try:
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = influx_client.query_api()

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> last()
    '''

    print("\nQuerying InfluxDB for latest sensor readings...")
    tables = query_api.query(query)

    real_sensor_data = {}
    for table in tables:
        for record in table.records:
            real_sensor_data[record.get_field()] = record.get_value()
            if 'timestamp' not in real_sensor_data:
                real_sensor_data['timestamp'] = str(record.get_time())

    influx_client.close()

    if not real_sensor_data:
        print("\n[ERROR] No data found in InfluxDB!")
        print("Make sure your Arduino is running and sending data to the API.")
        sys.exit(1)

    print(f"\n[SUCCESS] Found real sensor data:")
    print(f"  Temperature: {real_sensor_data.get('temperature', 'N/A')}°C")
    print(f"  Humidity: {real_sensor_data.get('humidity', 'N/A')}%")
    if 'timestamp' in real_sensor_data:
        print(f"  Last updated: {real_sensor_data['timestamp']}")
    print("\nSending notification with REAL data...\n")

except Exception as e:
    print(f"\n[ERROR] Failed to query InfluxDB: {e}")
    print("Using fallback test data instead...")
    real_sensor_data = {
        "temperature": 24.5,
        "humidity": 58.3,
    }
    print(f"\nFallback Sensor Data:")
    print(f"  Temperature: {real_sensor_data['temperature']}°C")
    print(f"  Humidity: {real_sensor_data['humidity']}%")
    print("\nSending test notification...\n")

# Send the test alert
results = notifier.test_alert(sensor_data=real_sensor_data)

print("\n" + "=" * 60)
print("Results:")
print("=" * 60)
for result in results:
    status = "[SENT]" if result['sent'] else "[NOT SENT]"
    available = "available" if result['available'] else "unavailable"
    print(f"  {result['channel']:15} [{available:15}] {status}")

print("\n" + "=" * 60)
print("Check the console output above for the alert details!")
print("=" * 60)
print("\nNOTE: To test with REAL data from InfluxDB, make sure:")
print("  1. Your Arduino is running and sending data")
print("  2. Your API server is running (python api/server.py)")
print("  3. Then call: POST http://localhost:3001/api/notifications/test-real")
