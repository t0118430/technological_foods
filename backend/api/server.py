import os
import json
import logging
import asyncio
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from ac_controller import (
    controller as ac_controller,
    check_auto_control,
    get_auto_control_settings,
    set_auto_control_settings
)

# Load .env from backend directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('http-server')

# Environment variables
PORT = int(os.getenv('HTTP_PORT', '3001'))
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')

# InfluxDB client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)
query_api = influx_client.query_api()


def write_to_influx(data: Dict[str, Any], sensor_id: str = "arduino_1"):
    """Write sensor data to InfluxDB"""
    point = Point("sensor_reading")
    point = point.tag("sensor_id", sensor_id)
    point = point.tag("source", "http_api")

    for key, value in data.items():
        if key in ['timestamp', 'sensor_id']:
            continue
        if isinstance(value, bool):
            point = point.field(key, int(value))
        elif isinstance(value, (int, float)):
            point = point.field(key, float(value))
        else:
            point = point.field(key, str(value))

    write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    logger.info(f"Stored in InfluxDB: {data}")


def query_latest():
    """Query latest sensor readings from InfluxDB"""
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> last()
    '''
    tables = query_api.query(query)
    result = {}
    for table in tables:
        for record in table.records:
            result[record.get_field()] = record.get_value()
            result['timestamp'] = str(record.get_time())
    return result


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "AgriTech Hydroponics API"}).encode())

        elif self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "influxdb": INFLUXDB_URL,
                "version": "1.0.0"
            }).encode())

        elif self.path == "/api/data/latest":
            try:
                latest = query_latest()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"latest": latest}).encode())
            except Exception as e:
                logger.error(f"Query error: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/api/ac":
            state = ac_controller.get_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode())

        elif self.path == "/api/ac/auto":
            settings = get_auto_control_settings()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(settings).encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        if self.path == "/api/data":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode())
                sensor_id = data.pop('sensor_id', 'arduino_1')

                write_to_influx(data, sensor_id)

                # Check auto AC control based on temperature
                ac_action = None
                if "temperature" in data:
                    ac_action = check_auto_control(data["temperature"])

                logger.info(f"[Arduino] Received: {data}")

                response = {"status": "saved", "data": data}
                if ac_action:
                    response["ac_action"] = ac_action

                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())

            except Exception as e:
                logger.error(f"Error saving data: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/api/ac":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode())
                results = {}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if "power" in data:
                    success = loop.run_until_complete(ac_controller.set_power(data["power"]))
                    results["power"] = "ok" if success else "failed"

                if "temperature" in data:
                    success = loop.run_until_complete(ac_controller.set_temperature(data["temperature"]))
                    results["temperature"] = "ok" if success else "failed"

                if "mode" in data:
                    success = loop.run_until_complete(ac_controller.set_mode(data["mode"]))
                    results["mode"] = "ok" if success else "failed"

                loop.close()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "results": results,
                    "state": ac_controller.get_state()
                }).encode())

            except Exception as e:
                logger.error(f"AC control error: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/api/ac/auto":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode())
                settings = set_auto_control_settings(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "settings": settings
                }).encode())

            except Exception as e:
                logger.error(f"Auto control settings error: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logs


if __name__ == "__main__":
    logger.info(f"Connecting to InfluxDB at {INFLUXDB_URL}")

    # Initialize AC controller
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ac_initialized = loop.run_until_complete(ac_controller.initialize())
    loop.close()

    if ac_initialized:
        logger.info("Haier AC controller initialized")
    else:
        logger.warning("AC controller not initialized (check HON_EMAIL and HON_PASSWORD)")

    server = HTTPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"Server running at http://0.0.0.0:{PORT}")
    print("Endpoints:")
    print("  GET  /api/health      - Health check")
    print("  GET  /api/data/latest - Get latest reading from InfluxDB")
    print("  POST /api/data        - Save Arduino data to InfluxDB")
    print("  GET  /api/ac          - Get AC status")
    print("  POST /api/ac          - Control AC (power, temperature, mode)")
    print("  GET  /api/ac/auto     - Get auto control settings")
    print("  POST /api/ac/auto     - Set auto control settings")
    server.serve_forever()
