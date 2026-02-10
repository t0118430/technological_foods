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

from urllib.parse import urlparse, parse_qs

from ac_controller import controller as ac_controller
from rule_engine import RuleEngine
from notification_service import notifier
from alert_escalation import escalation_manager
from growth_stage_manager import growth_manager
from database import db

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
API_KEY = os.getenv('API_KEY', '')

# InfluxDB client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)
query_api = influx_client.query_api()

# Rule engine (config server)
rule_engine = RuleEngine()


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


def _execute_ac_action(action: Dict[str, Any]):
    """Execute an AC command from a triggered rule."""
    if not ac_controller._initialized:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        command = action.get('command', '')
        if command == 'cool':
            loop.run_until_complete(ac_controller.set_power(True))
            target = action.get('target_temp', 24)
            loop.run_until_complete(ac_controller.set_temperature(target))
            loop.run_until_complete(ac_controller.set_mode('cool'))
            logger.info(f"Rule engine → AC ON (cool, {target}°C)")
        elif command == 'heat':
            loop.run_until_complete(ac_controller.set_power(True))
            target = action.get('target_temp', 24)
            loop.run_until_complete(ac_controller.set_temperature(target))
            loop.run_until_complete(ac_controller.set_mode('heat'))
            logger.info(f"Rule engine → AC ON (heat, {target}°C)")
        elif command == 'off':
            loop.run_until_complete(ac_controller.set_power(False))
            logger.info("Rule engine → AC OFF")
    finally:
        loop.close()


OPENAPI_PATH = Path(__file__).resolve().parent / 'openapi.json'

SWAGGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AgriTech Hydroponics API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/api/openapi.json',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: 'BaseLayout',
    });
  </script>
</body>
</html>"""


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode())

    def _parsed_path(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def _check_api_key(self):
        """Validate X-API-Key header. Returns True if valid, sends 401 if not."""
        if not API_KEY:
            return True  # No key configured — skip auth
        key = self.headers.get("X-API-Key", "")
        if key == API_KEY:
            return True
        self._send_json(401, {"error": "Unauthorized — invalid or missing API key"})
        return False

    def do_GET(self):
        path, query = self._parsed_path()

        if path in ("/", "/api/health", "/api/docs", "/api/openapi.json"):
            pass  # Public endpoints — no auth required
        elif not self._check_api_key():
            return

        if path == "/":
            self._send_json(200, {"message": "AgriTech Hydroponics API"})

        elif path == "/api/docs":
            self._send_html(200, SWAGGER_HTML)

        elif path == "/api/openapi.json":
            spec = OPENAPI_PATH.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(spec.encode())

        elif path == "/api/health":
            self._send_json(200, {
                "status": "healthy",
                "influxdb": INFLUXDB_URL,
                "version": "2.0.0"
            })

        elif path == "/api/data/latest":
            try:
                latest = query_latest()
                self._send_json(200, {"latest": latest})
            except Exception as e:
                logger.error(f"Query error: {e}")
                self._send_json(500, {"error": str(e)})

        elif path == "/api/ac":
            state = ac_controller.get_state()
            self._send_json(200, state)

        # ── Config Server: Rules ─────────────────────────
        elif path == "/api/rules":
            self._send_json(200, {"rules": rule_engine.get_rules()})

        elif path.startswith("/api/rules/"):
            rule_id = path.split("/api/rules/")[1]
            rule = rule_engine.get_rule(rule_id)
            if rule:
                self._send_json(200, rule)
            else:
                self._send_json(404, {"error": f"Rule '{rule_id}' not found"})

        # ── Notifications ─────────────────────────────────
        elif path == "/api/notifications":
            self._send_json(200, notifier.get_status())

        # ── Alert Escalation Status ───────────────────────
        elif path == "/api/escalation":
            self._send_json(200, escalation_manager.get_status())

        # ── Growth Stage Management ───────────────────────
        elif path == "/api/crops":
            crops = db.get_active_crops()
            self._send_json(200, {"crops": crops})

        elif path.startswith("/api/crops/"):
            crop_id = int(path.split("/api/crops/")[1].split("/")[0])

            if path.endswith("/conditions"):
                conditions = growth_manager.get_current_conditions(crop_id)
                if conditions:
                    self._send_json(200, conditions)
                else:
                    self._send_json(404, {"error": "Crop not found"})

            elif path.endswith("/rules"):
                rules = growth_manager.get_stage_specific_rules(crop_id)
                self._send_json(200, {"rules": rules})

            else:
                crop = db.get_crop(crop_id)
                if crop:
                    self._send_json(200, crop)
                else:
                    self._send_json(404, {"error": "Crop not found"})

        elif path == "/api/dashboard":
            dashboard = growth_manager.get_dashboard()
            self._send_json(200, dashboard)

        elif path == "/api/harvest/analytics":
            analytics = growth_manager.get_harvest_analytics()
            self._send_json(200, analytics)

        elif path == "/api/calibrations/due":
            due = db.get_due_calibrations()
            self._send_json(200, {"calibrations_due": due})

        # ── Config Server: Arduino Command Polling ────────
        elif path == "/api/commands":
            sensor_id = query.get("sensor_id", ["arduino_1"])[0]
            commands = rule_engine.get_pending_commands(sensor_id)
            self._send_json(200, {"commands": commands})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self._check_api_key():
            return
        path, _ = self._parsed_path()

        if path == "/api/data":
            try:
                data = self._read_body()
                sensor_id = data.pop('sensor_id', 'arduino_1')

                write_to_influx(data, sensor_id)

                # Check for resolved alerts first (values back to safe zone)
                resolved = escalation_manager.check_for_resolved_alerts(data)
                for resolution in resolved:
                    # Send "Issue Resolved" notification
                    notifier.notify(
                        rule_id=f"{resolution['rule_id']}_resolved",
                        severity='info',
                        message=f"✅ {resolution['sensor'].replace('_', ' ').title()} back to normal",
                        sensor_data=data,
                        recommended_action=f"Issue resolved after {resolution['duration_minutes']} minutes. System is now stable.",
                    )
                    logger.info(f"Alert resolved notification sent for {resolution['rule_id']}")

                # Evaluate rules (config server decides what to do)
                triggered = rule_engine.evaluate(data, sensor_id)

                # Execute AC actions from triggered rules
                ac_actions = [t for t in triggered if t['action'].get('type') == 'ac']
                for t in ac_actions:
                    _execute_ac_action(t['action'])

                # Execute notification actions from triggered rules WITH ESCALATION
                notify_actions = [t for t in triggered if t['action'].get('type') == 'notify']
                for t in notify_actions:
                    # Get sensor value for escalation tracking
                    sensor_key = t.get('sensor', 'unknown')
                    current_value = data.get(sensor_key, 0)

                    # Determine threshold and condition from original rule
                    rule_id_base = t['rule_id'].replace('_preventive', '')
                    rule = rule_engine.get_rule(rule_id_base)
                    if not rule:
                        continue

                    threshold = rule.get('threshold', 0)
                    condition = rule.get('condition', 'above')

                    # Get action strings
                    alert_type = t.get('alert_type', 'critical')
                    if alert_type == 'preventive':
                        preventive_action = rule.get('preventive_action', '')
                        recommended = preventive_action
                    else:
                        preventive_action = rule.get('preventive_action', '')
                        recommended = t['action'].get('recommended_action', '')

                    # Check escalation manager - should we send this alert?
                    escalation_info = escalation_manager.should_send_alert(
                        rule_id=t['rule_id'],
                        sensor=sensor_key,
                        current_value=current_value,
                        threshold=threshold,
                        condition=condition,
                        original_message=t['action'].get('message', t['rule_name']),
                        preventive_action=preventive_action,
                        recommended_action=recommended,
                    )

                    if not escalation_info:
                        # Alert suppressed (too soon or improving)
                        logger.debug(f"Alert {t['rule_id']} suppressed by escalation manager")
                        continue

                    # Send notification with escalation level
                    notifier.notify(
                        rule_id=t['rule_id'],
                        severity=escalation_info['severity'],
                        message=escalation_info['message'],
                        sensor_data=data,
                        recommended_action=escalation_info['suggested_action'],
                        escalation_info=escalation_info,
                    )

                logger.info(f"[Arduino] Received: {data} | Rules triggered: {len(triggered)}")

                self._send_json(201, {
                    "status": "saved",
                    "data": data,
                    "triggered_rules": [t['rule_id'] for t in triggered]
                })

            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error saving data: {e}")
                self._send_json(500, {"error": str(e)})

        elif path == "/api/ac":
            try:
                data = self._read_body()
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

                self._send_json(200, {
                    "status": "ok",
                    "results": results,
                    "state": ac_controller.get_state()
                })

            except Exception as e:
                logger.error(f"AC control error: {e}")
                self._send_json(500, {"error": str(e)})

        # ── Notifications: Test Alert ─────────────────────
        elif path == "/api/notifications/test":
            try:
                results = notifier.test_alert()
                self._send_json(200, {
                    "status": "test_sent",
                    "channels": results,
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Notifications: Test Alert with Real Data ──────
        elif path == "/api/notifications/test-real":
            try:
                # Get latest real data from InfluxDB
                latest = query_latest()

                if not latest:
                    self._send_json(404, {
                        "error": "No sensor data available. Arduino may not be sending data yet."
                    })
                    return

                # Send notification with real data
                results = notifier.test_alert(sensor_data=latest)
                self._send_json(200, {
                    "status": "test_sent_with_real_data",
                    "sensor_data": latest,
                    "channels": results,
                })
            except Exception as e:
                logger.error(f"Test alert error: {e}")
                self._send_json(500, {"error": str(e)})

        # ── Config Server: Create Rule ────────────────────
        elif path == "/api/rules":
            try:
                data = self._read_body()
                rule = rule_engine.create_rule(data)
                self._send_json(201, {"status": "created", "rule": rule})
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Growth Stage: Create Crop ─────────────────────
        elif path == "/api/crops":
            try:
                data = self._read_body()
                variety = data.get('variety')
                if not variety:
                    self._send_json(400, {"error": "variety required"})
                    return

                crop = growth_manager.create_crop_batch(
                    variety=variety,
                    plant_date=data.get('plant_date'),
                    zone=data.get('zone', 'main'),
                    notes=data.get('notes')
                )
                self._send_json(201, {"status": "created", "crop": crop})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Growth Stage: Advance Stage ───────────────────
        elif path.endswith("/advance"):
            crop_id = int(path.split("/api/crops/")[1].split("/")[0])
            try:
                data = self._read_body()
                new_stage = data.get('stage')
                reason = data.get('reason', 'Manual advancement')

                if not new_stage:
                    self._send_json(400, {"error": "stage required"})
                    return

                success = growth_manager.record_manual_stage_advance(crop_id, new_stage, reason)
                if success:
                    self._send_json(200, {"status": "advanced", "crop_id": crop_id, "stage": new_stage})
                else:
                    self._send_json(500, {"error": "Failed to advance stage"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Harvest Record ────────────────────────────────
        elif path.startswith("/api/crops/") and path.endswith("/harvest"):
            crop_id = int(path.split("/api/crops/")[1].split("/")[0])
            try:
                data = self._read_body()
                weight = data.get('weight_kg')
                quality = data.get('quality_grade', 'standard')

                if not weight:
                    self._send_json(400, {"error": "weight_kg required"})
                    return

                harvest_id = db.record_harvest(
                    crop_id,
                    weight,
                    quality,
                    data.get('market_value'),
                    data.get('notes')
                )
                self._send_json(201, {"status": "harvested", "harvest_id": harvest_id})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Calibration Record ────────────────────────────
        elif path == "/api/calibrations":
            try:
                data = self._read_body()
                sensor_type = data.get('sensor_type')

                if not sensor_type:
                    self._send_json(400, {"error": "sensor_type required"})
                    return

                calibration_id = db.record_calibration(
                    sensor_type,
                    data.get('next_due_days', 30),
                    data.get('performed_by'),
                    data.get('notes')
                )
                self._send_json(201, {"status": "recorded", "calibration_id": calibration_id})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_PUT(self):
        if not self._check_api_key():
            return
        path, _ = self._parsed_path()

        if path.startswith("/api/rules/"):
            rule_id = path.split("/api/rules/")[1]
            try:
                data = self._read_body()
                rule = rule_engine.update_rule(rule_id, data)
                if rule:
                    self._send_json(200, {"status": "updated", "rule": rule})
                else:
                    self._send_json(404, {"error": f"Rule '{rule_id}' not found"})
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        if not self._check_api_key():
            return
        path, _ = self._parsed_path()

        if path.startswith("/api/rules/"):
            rule_id = path.split("/api/rules/")[1]
            if rule_engine.delete_rule(rule_id):
                self._send_json(200, {"status": "deleted", "id": rule_id})
            else:
                self._send_json(404, {"error": f"Rule '{rule_id}' not found"})
        else:
            self._send_json(404, {"error": "Not found"})

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

    logger.info(f"Rule engine loaded {len(rule_engine.get_rules())} rules")

    server = HTTPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"Server running at http://0.0.0.0:{PORT}")
    print(f"Swagger UI:  http://localhost:{PORT}/api/docs")
    print("Endpoints:")
    print("  GET    /api/docs                - Swagger UI")
    print("  GET    /api/openapi.json        - OpenAPI spec")
    print("  GET    /api/health              - Health check")
    print("  GET    /api/data/latest         - Get latest reading from InfluxDB")
    print("  POST   /api/data                - Save Arduino data + evaluate rules")
    print("  GET    /api/ac                  - Get AC status")
    print("  POST   /api/ac                  - Control AC (power, temperature, mode)")
    print("  GET    /api/rules               - List all rules (config server)")
    print("  POST   /api/rules               - Create a rule")
    print("  PUT    /api/rules/{id}          - Update a rule")
    print("  DELETE /api/rules/{id}          - Delete a rule")
    print("  GET    /api/commands            - Arduino polls for commands")
    print("  GET    /api/notifications       - Notification status & history")
    print("  POST   /api/notifications/test  - Send test alert (default data)")
    print("  POST   /api/notifications/test-real - Send test alert (real sensor data)")
    print("  GET    /api/escalation          - Alert escalation status & active alerts")
    print("")
    print("Growth Stage Management:")
    print("  POST   /api/crops               - Create new crop batch")
    print("  GET    /api/crops               - List all active crops")
    print("  GET    /api/crops/{id}          - Get crop details & stage history")
    print("  GET    /api/crops/{id}/conditions - Get stage-specific optimal conditions")
    print("  GET    /api/crops/{id}/rules    - Get stage-specific monitoring rules")
    print("  POST   /api/crops/{id}/advance  - Manually advance to next stage")
    print("  POST   /api/crops/{id}/harvest  - Record harvest")
    print("  GET    /api/dashboard           - Comprehensive crop dashboard")
    print("  GET    /api/harvest/analytics   - Harvest performance metrics")
    print("")
    print("Sensor Calibration:")
    print("  POST   /api/calibrations        - Record sensor calibration")
    print("  GET    /api/calibrations/due    - Get sensors needing calibration")

    # Check for stage advancements on startup
    print("")
    print("Checking for crops ready to advance...")
    advanced = growth_manager.check_and_advance_stages()
    if advanced:
        print(f"  → Auto-advanced {len(advanced)} crops to next stage")
        for adv in advanced:
            print(f"     Crop {adv['crop_id']} ({adv['variety']}): {adv['from_stage']} → {adv['to_stage']}")
    else:
        print("  → No crops ready to advance")

    print("")
    server.serve_forever()
