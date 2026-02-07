import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class TemperatureHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/temperature":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            temp = data["temperature"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Temperature: {temp} °C")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] {e}")
            self.send_error(400, "Invalid JSON or missing 'temperature' key")

    # Suppress the default log line per request
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), TemperatureHandler)
    print("Server running on http://0.0.0.0:5000")
    print("Waiting for POST to /temperature ...\n")
    server.serve_forever()
