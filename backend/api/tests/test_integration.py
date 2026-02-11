"""
Integration tests for the AgriTech Hydroponics API.

Requires the server to be running:
    python server.py

And InfluxDB to be available (via docker-compose).

Usage:
    python test_integration.py
    python -m pytest test_integration.py -v
"""

import json
import time
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:3001"

# Test counters
passed = 0
failed = 0
errors = []


def request(method, path, data=None):
    """Make an HTTP request and return (status_code, response_body)."""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except urllib.error.URLError:
        return None, {"error": "Server not reachable"}


def test(name, condition, detail=""):
    """Register a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(name)


def test_server_reachable():
    """Test that the server is running and reachable."""
    print("\n--- Server Connectivity ---")
    status, body = request("GET", "/")
    test("GET / returns 200", status == 200, f"got {status}")
    test("GET / returns welcome message",
         body.get("message") == "AgriTech Hydroponics API",
         f"got {body}")


def test_health():
    """Test the health endpoint."""
    print("\n--- Health Check ---")
    status, body = request("GET", "/api/health")
    test("GET /api/health returns 200", status == 200, f"got {status}")
    test("Health status is 'healthy'",
         body.get("status") == "healthy",
         f"got {body.get('status')}")
    test("Health includes version",
         body.get("version") is not None,
         f"got {body}")


def test_post_sensor_data():
    """Test posting sensor data (simulates Arduino sending data)."""
    print("\n--- POST /api/data (Simulate Arduino) ---")

    payload = {"temperature": 22.5, "humidity": 55.0}
    status, body = request("POST", "/api/data", payload)
    test("POST /api/data returns 201", status == 201, f"got {status}")
    test("Response status is 'saved'",
         body.get("status") == "saved",
         f"got {body.get('status')}")
    test("Response echoes temperature",
         body.get("data", {}).get("temperature") == 22.5,
         f"got {body.get('data')}")
    test("Response echoes humidity",
         body.get("data", {}).get("humidity") == 55.0,
         f"got {body.get('data')}")


def test_post_sensor_data_with_sensor_id():
    """Test posting with a custom sensor_id."""
    print("\n--- POST /api/data (Custom sensor_id) ---")

    payload = {"temperature": 19.0, "humidity": 45.0, "sensor_id": "test_sensor"}
    status, body = request("POST", "/api/data", payload)
    test("POST with sensor_id returns 201", status == 201, f"got {status}")
    test("sensor_id is not in response data (popped)",
         "sensor_id" not in body.get("data", {}),
         f"got {body.get('data')}")


def test_post_invalid_json():
    """Test posting invalid JSON."""
    print("\n--- POST /api/data (Invalid JSON) ---")

    url = f"{BASE_URL}/api/data"
    req = urllib.request.Request(url, data=b"not json", method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        status = e.code
        body = json.loads(e.read().decode())

    test("POST invalid JSON returns 400", status == 400, f"got {status}")
    test("Error message present",
         "error" in body,
         f"got {body}")


def test_get_latest_data():
    """Test getting latest sensor data from InfluxDB."""
    print("\n--- GET /api/data/latest ---")

    # Wait a moment for InfluxDB to index the data we posted
    time.sleep(1)

    status, body = request("GET", "/api/data/latest")
    test("GET /api/data/latest returns 200", status == 200, f"got {status}")
    test("Response has 'latest' key",
         "latest" in body,
         f"got {body}")


def test_not_found():
    """Test 404 for unknown routes."""
    print("\n--- Unknown Routes ---")

    status, body = request("GET", "/api/nonexistent")
    test("GET unknown route returns 404", status == 404, f"got {status}")
    test("Error message is 'Not found'",
         body.get("error") == "Not found",
         f"got {body}")


def test_ac_endpoints():
    """Test AC control endpoints."""
    print("\n--- AC Endpoints ---")

    status, body = request("GET", "/api/ac")
    test("GET /api/ac returns 200", status == 200, f"got {status}")
    test("AC state has 'power' field",
         "power" in body,
         f"got {body}")
    test("AC state has 'target_temp' field",
         "target_temp" in body,
         f"got {body}")


def test_ac_auto_settings():
    """Test AC auto control settings."""
    print("\n--- AC Auto Control Settings ---")

    # GET current settings
    status, body = request("GET", "/api/ac/auto")
    test("GET /api/ac/auto returns 200", status == 200, f"got {status}")
    test("Has 'enabled' field",
         "enabled" in body,
         f"got {body}")

    # POST update settings
    new_settings = {"enabled": True, "max_temp": 30.0, "min_temp": 20.0}
    status, body = request("POST", "/api/ac/auto", new_settings)
    test("POST /api/ac/auto returns 200", status == 200, f"got {status}")
    test("Settings updated — enabled is True",
         body.get("settings", {}).get("enabled") is True,
         f"got {body}")
    test("Settings updated — max_temp is 30.0",
         body.get("settings", {}).get("max_temp") == 30.0,
         f"got {body}")

    # Reset back
    request("POST", "/api/ac/auto", {"enabled": False})


def test_arduino_flow():
    """End-to-end: simulate the Arduino sending data and verify it's stored."""
    print("\n--- End-to-End Arduino Flow ---")

    # 1. Post sensor data (simulates what the Arduino sketch does)
    payload = {"temperature": 25.3, "humidity": 62.1}
    status, body = request("POST", "/api/data", payload)
    test("Arduino POST accepted", status == 201, f"got {status}")

    # 2. Wait for InfluxDB write
    time.sleep(1)

    # 3. Query latest
    status, body = request("GET", "/api/data/latest")
    test("Latest data available", status == 200, f"got {status}")
    latest = body.get("latest", {})
    test("Latest has temperature",
         "temperature" in latest,
         f"got {latest}")
    test("Latest has humidity",
         "humidity" in latest,
         f"got {latest}")


if __name__ == "__main__":
    print("=" * 50)
    print("AgriTech Hydroponics API — Integration Tests")
    print(f"Target: {BASE_URL}")
    print("=" * 50)

    # Check server is reachable first
    status, _ = request("GET", "/api/health")
    if status is None:
        print(f"\nERROR: Server not reachable at {BASE_URL}")
        print("Start it with: python server.py")
        sys.exit(1)

    test_server_reachable()
    test_health()
    test_post_sensor_data()
    test_post_sensor_data_with_sensor_id()
    test_post_invalid_json()
    test_get_latest_data()
    test_not_found()
    test_ac_endpoints()
    test_ac_auto_settings()
    test_arduino_flow()

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"Failed tests: {', '.join(errors)}")
    print("=" * 50)

    sys.exit(1 if failed > 0 else 0)
