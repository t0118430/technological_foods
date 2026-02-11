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
from business_dashboard import dashboard as business_dashboard
from drift_detection_service import drift_detector
from multi_channel_notifier import multi_notifier, AlertLevel, ChannelType
from client_manager import client_manager
from sensor_analytics import sensor_analytics
from weather_service import weather_service
from market_data_service import market_data_service
from crop_intelligence import crop_intelligence
from data_export import data_export_service

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

        # ── Business Intelligence Dashboard (Complete) ────
        elif path == "/api/business/dashboard":
            try:
                data = business_dashboard.get_complete_dashboard()
                self._send_json(200, data)
            except Exception as e:
                logger.error(f"Business dashboard error: {e}")
                self._send_json(500, {"error": str(e)})

        elif path == "/business":
            # Serve HTML business dashboard
            try:
                dashboard_path = Path(__file__).resolve().parent.parent / "dashboard.html"
                if dashboard_path.exists():
                    html_content = dashboard_path.read_text(encoding="utf-8")
                    self._send_html(200, html_content)
                else:
                    self._send_html(404, "<h1>Dashboard not found</h1><p>dashboard.html is missing</p>")
            except Exception as e:
                logger.error(f"Dashboard HTML error: {e}")
                self._send_html(500, f"<h1>Error</h1><p>{str(e)}</p>")

        elif path == "/api/calibrations/due":
            due = db.get_due_calibrations()
            self._send_json(200, {"calibrations_due": due})

        # ── Drift Detection Status ────────────────────────
        elif path == "/api/sensors/drift/status":
            status = drift_detector.get_status()
            self._send_json(200, status)

        elif path.startswith("/api/sensors/drift/"):
            sensor_id = path.split("/api/sensors/drift/")[1]
            trend = drift_detector.get_drift_trend(sensor_id)
            self._send_json(200, {
                "sensor_id": sensor_id,
                "trend": trend
            })

        # ── Config Server: Arduino Command Polling ────────
        elif path == "/api/commands":
            sensor_id = query.get("sensor_id", ["arduino_1"])[0]
            commands = rule_engine.get_pending_commands(sensor_id)
            self._send_json(200, {"commands": commands})

        # ── Sensor Analytics (Phase 1) ──────────────────────
        elif path == "/api/analytics/summary":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                summary = sensor_analytics.get_sensor_summary(sensor_id)
                self._send_json(200, summary)
            except Exception as e:
                logger.error(f"Analytics summary error: {e}")
                self._send_json(500, {"error": str(e)})

        elif path == "/api/analytics/vpd":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                latest = query_latest()
                temp = latest.get('temperature')
                humidity = latest.get('humidity')
                if temp is not None and humidity is not None:
                    vpd = sensor_analytics.calculate_vpd(float(temp), float(humidity))
                    self._send_json(200, vpd)
                else:
                    self._send_json(404, {"error": "No temperature/humidity data available"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/analytics/dli":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                dli = sensor_analytics.calculate_dli(sensor_id)
                self._send_json(200, dli)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/analytics/trends":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                window = int(query.get("window", ["60"])[0])
                trends = sensor_analytics.detect_trends(sensor_id, window)
                self._send_json(200, {"sensor_id": sensor_id, "trends": trends})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/analytics/anomalies":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                latest = query_latest()
                anomalies = sensor_analytics.detect_anomalies(latest, sensor_id)
                self._send_json(200, {"sensor_id": sensor_id, "anomalies": anomalies})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/analytics/history":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                field = query.get("field", ["temperature"])[0]
                start = query.get("start", ["-7d"])[0]
                end = query.get("end", ["now()"])[0]
                aggregation = query.get("aggregation", ["1h"])[0]
                result = sensor_analytics.query_historical_analytics(
                    sensor_id, field, start, end, aggregation
                )
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Weather Service (Phase 2) ───────────────────────
        elif path == "/api/weather/current":
            try:
                result = weather_service.get_current_weather()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/weather/forecast":
            try:
                days = int(query.get("days", ["3"])[0])
                result = weather_service.get_forecast(days)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/weather/solar":
            try:
                result = weather_service.get_solar_data()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/weather/correlation":
            try:
                # Get latest indoor sensor data
                latest = query_latest()
                indoor_data = None
                if latest:
                    indoor_data = {
                        'temperature': latest.get('temperature'),
                        'humidity': latest.get('humidity'),
                    }
                result = weather_service.get_greenhouse_correlation(indoor_data)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/weather/advisory":
            try:
                variety = query.get("variety", [None])[0]
                result = weather_service.get_growing_conditions_advisory(variety)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Market Data (Phase 2) ───────────────────────────
        elif path == "/api/market/prices":
            try:
                result = market_data_service.get_market_prices()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/market/demand":
            try:
                result = market_data_service.get_seasonal_demand()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Crop Intelligence (Phase 3) ─────────────────────
        elif path == "/api/intelligence/correlations":
            try:
                variety = query.get("variety", ["rosso_premium"])[0]
                result = crop_intelligence.get_condition_harvest_correlation(variety)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path.startswith("/api/intelligence/recommendations/"):
            try:
                crop_id = int(path.split("/api/intelligence/recommendations/")[1])
                result = crop_intelligence.get_growth_optimization_recommendations(crop_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path.startswith("/api/intelligence/predict/"):
            try:
                crop_id = int(path.split("/api/intelligence/predict/")[1])
                result = crop_intelligence.predict_yield(crop_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path.startswith("/api/intelligence/health/"):
            try:
                crop_id = int(path.split("/api/intelligence/health/")[1])
                result = crop_intelligence.get_crop_health_score(crop_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        # ── Data Export & Reports (Phase 4) ──────────────────
        elif path == "/api/export/sensor-csv":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                start = query.get("start", ["-7d"])[0]
                end = query.get("end", ["now()"])[0]
                fields = query.get("fields", None)
                aggregation = query.get("aggregation", [None])[0]
                csv_data = data_export_service.export_sensor_csv(
                    sensor_id, start, end, fields, aggregation
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="sensor_{sensor_id}.csv"')
                self.end_headers()
                self.wfile.write(csv_data.encode())
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path.startswith("/api/export/crop-report/"):
            try:
                crop_id = int(path.split("/api/export/crop-report/")[1])
                result = data_export_service.export_crop_report(crop_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/reports/weekly":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                result = data_export_service.generate_weekly_summary(sensor_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/reports/monthly":
            try:
                sensor_id = query.get("sensor_id", ["arduino_1"])[0]
                result = data_export_service.generate_monthly_summary(sensor_id)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

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

                # Feed analytics engine (VPD, DLI, trends, anomalies)
                try:
                    analytics_result = sensor_analytics.ingest_reading(data, sensor_id)
                except Exception as analytics_err:
                    logger.warning(f"Analytics ingestion error: {analytics_err}")
                    analytics_result = {}

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
                    "triggered_rules": [t['rule_id'] for t in triggered],
                    "analytics": analytics_result,
                })

            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error saving data: {e}")
                self._send_json(500, {"error": str(e)})

        # ── Dual Sensor System: Drift Detection ───────────
        elif path == "/api/sensors/dual":
            try:
                data = self._read_body()

                # Extract data
                sensor_id = data.get("sensor_id", "unknown")
                primary = data.get("primary", {})
                secondary = data.get("secondary", {})
                drift_data = data.get("drift", {})

                # Analyze drift
                analysis = drift_detector.analyze_dual_reading(
                    sensor_id=sensor_id,
                    primary=primary,
                    secondary=secondary,
                    sensor_tier="medium"  # Can be configured per client
                )

                # Calculate revenue risk
                revenue_risk = drift_detector.calculate_revenue_risk(analysis)

                # Get drift trend
                trend = drift_detector.get_drift_trend(sensor_id)

                # Check if alert should be sent
                if drift_detector.should_send_alert(sensor_id, analysis):
                    # Determine client (if sensor linked to client)
                    # For now, use sensor_id as client name
                    client_name = sensor_id.replace("_", " ").title()

                    # Format business alert
                    alert = drift_detector.format_business_alert(
                        sensor_id, client_name, analysis, revenue_risk
                    )

                    # Determine alert level
                    if analysis.status == "failing":
                        alert_level = AlertLevel.AGGRESSIVE
                    elif analysis.status == "degraded":
                        alert_level = AlertLevel.MEDIUM
                    else:
                        alert_level = AlertLevel.OPTIMIST

                    # Send to business private channel
                    multi_notifier.send(
                        channel=ChannelType.BUSINESS_PRIVATE,
                        level=alert_level,
                        title=alert["title"],
                        body=alert["body"]
                    )

                    # Update client health score (if client linked)
                    # client_manager.update_health_score(
                    #     client_id=client_id,
                    #     delta=-10 if analysis.status == "degraded" else -20,
                    #     reason=f"Sensor drift detected: {analysis.status}"
                    # )

                    logger.info(f"[Drift Alert] {sensor_id}: {analysis.status} - Alert sent")

                # Write to InfluxDB (both sensors + drift metrics)
                write_to_influx({
                    "temperature": primary.get("temperature"),
                    "humidity": primary.get("humidity"),
                    "temperature_secondary": secondary.get("temperature"),
                    "humidity_secondary": secondary.get("humidity"),
                    "temp_drift": analysis.temp_diff,
                    "humidity_drift": analysis.humidity_diff,
                    "drift_status": analysis.status,
                }, sensor_id)

                self._send_json(201, {
                    "status": "analyzed",
                    "sensor_id": sensor_id,
                    "analysis": {
                        "status": analysis.status,
                        "temp_diff": analysis.temp_diff,
                        "humidity_diff": analysis.humidity_diff,
                        "needs_calibration": analysis.needs_calibration,
                        "days_until_failure": analysis.estimated_days_until_failure,
                    },
                    "revenue_risk": revenue_risk,
                    "trend": trend,
                    "alert_sent": drift_detector.should_send_alert(sensor_id, analysis),
                })

            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Drift detection error: {e}")
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
                data = self._read_body() if int(self.headers.get("Content-Length", 0)) > 0 else {}
                crop_id = data.get('crop_id')

                # Get latest real data from InfluxDB
                latest = query_latest()

                if not latest:
                    self._send_json(404, {
                        "error": "No sensor data available. Arduino may not be sending data yet."
                    })
                    return

                response = {
                    "status": "test_sent_with_real_data",
                    "sensor_data": latest,
                }

                # If crop_id provided, include production context
                if crop_id is not None:
                    crop_id = int(crop_id)
                    conditions = growth_manager.get_current_conditions(crop_id)
                    if not conditions:
                        # Return available crops so user can pick
                        crops = db.get_active_crops()
                        self._send_json(404, {
                            "error": f"Crop {crop_id} not found",
                            "available_crops": crops,
                        })
                        return

                    response["crop"] = {
                        "crop_id": crop_id,
                        "variety": conditions["variety"],
                        "current_stage": conditions["current_stage"],
                        "days_in_stage": conditions["days_in_stage"],
                        "optimal_conditions": conditions["conditions"],
                    }
                else:
                    # No crop selected — list available productions
                    crops = db.get_active_crops()
                    response["available_crops"] = crops

                # Send notification with real data
                results = notifier.test_alert(sensor_data=latest)
                response["channels"] = results

                self._send_json(200, response)
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

        # ── Market Data: Update Prices (Phase 2) ────────────
        elif path == "/api/market/prices":
            try:
                data = self._read_body()
                result = market_data_service.update_market_prices(data)
                if 'error' in result:
                    self._send_json(400, result)
                else:
                    self._send_json(200, result)
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
    print("")
    print("Sensor Analytics (Phase 1):")
    print("  GET    /api/analytics/summary   - Full analytics snapshot (VPD, DLI, trends)")
    print("  GET    /api/analytics/vpd       - Current VPD with classification")
    print("  GET    /api/analytics/dli       - DLI progress + projected daily total")
    print("  GET    /api/analytics/trends    - Trend direction for all sensors")
    print("  GET    /api/analytics/anomalies - Active anomaly detections")
    print("  GET    /api/analytics/history   - Historical data with aggregation")
    print("")
    print("Weather & Market (Phase 2):")
    print("  GET    /api/weather/current     - Current outdoor weather (Open-Meteo)")
    print("  GET    /api/weather/forecast    - 3-day forecast")
    print("  GET    /api/weather/solar       - Sunrise/sunset + light advisory")
    print("  GET    /api/weather/correlation - Indoor vs outdoor comparison")
    print("  GET    /api/weather/advisory    - Growing conditions advisory")
    print("  GET    /api/market/prices       - Market prices")
    print("  POST   /api/market/prices       - Update market prices")
    print("  GET    /api/market/demand       - Seasonal demand multipliers")
    print("")
    print("Crop Intelligence (Phase 3):")
    print("  GET    /api/intelligence/correlations         - Condition-to-harvest correlations")
    print("  GET    /api/intelligence/recommendations/{id} - Optimization recommendations")
    print("  GET    /api/intelligence/predict/{id}         - Yield prediction")
    print("  GET    /api/intelligence/health/{id}          - Crop health score")
    print("")
    print("Data Export & Reports (Phase 4):")
    print("  GET    /api/export/sensor-csv          - CSV file download")
    print("  GET    /api/export/crop-report/{id}    - Crop lifecycle report")
    print("  GET    /api/reports/weekly              - Weekly summary")
    print("  GET    /api/reports/monthly             - Monthly summary")

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
