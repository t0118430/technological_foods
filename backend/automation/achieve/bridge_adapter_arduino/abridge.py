import serial
import time
import json
import re
import os
from pathlib import Path
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load .env from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Config from .env
SERIAL_PORT = os.getenv('SERIAL_PORT', 'COM7')
SERIAL_BAUD = int(os.getenv('SERIAL_BAUD', '9600'))
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC_BASE = os.getenv('MQTT_TOPIC_SENSORS', 'hydroponics/sensors')
MQTT_TOPIC_SUBSCRIBE = os.getenv('MQTT_TOPIC_COMMANDS', 'hydroponics/commands')

ser = None

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC_SUBSCRIBE)
        print(f"[MQTT] Subscribed to {MQTT_TOPIC_SUBSCRIBE}")
    else:
        print(f"[MQTT] Connection failed: {reason_code}")

def on_message(client, userdata, msg):
    """Receive from MQTT -> Send to Arduino"""
    payload = msg.payload.decode()
    print(f"[MQTT -> Arduino] {payload}")
    if ser and ser.is_open:
        ser.write((payload + '\n').encode())

def publish_to_mqtt(client, data):
    """Receive from Arduino -> Send to MQTT"""
    # Try to parse as JSON first
    try:
        json.loads(data)  # Validate JSON
        # Valid JSON - send to combined topic
        topic = f"{MQTT_TOPIC_BASE}/all"
        client.publish(topic, data)
        print(f"[Arduino -> MQTT] {topic}: {data}")
        return
    except json.JSONDecodeError:
        pass

    # Fallback: parse old format "Temperature = 25.5 C"
    match = re.match(r'(\w+)\s*=\s*([\d.]+)', data)
    if match:
        sensor_type = match.group(1).lower()
        value = float(match.group(2))
        topic = f"{MQTT_TOPIC_BASE}/{sensor_type}"
        json_payload = json.dumps({"value": value})
        client.publish(topic, json_payload)
        print(f"[Arduino -> MQTT] {topic}: {json_payload}")
    else:
        # Raw data
        client.publish(MQTT_TOPIC_BASE, data)
        print(f"[Arduino -> MQTT] {data} (raw)")

# Setup MQTT
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()
except Exception as e:
    print(f"[MQTT] Error connecting: {e}")
    exit(1)

# Setup Serial
try:
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    print(f"[Serial] Connected to {SERIAL_PORT}")
    time.sleep(2)  # Wait for Arduino reset

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            if line:
                print(f"[Arduino] {line}")
                publish_to_mqtt(mqtt_client, line)

except serial.SerialException:
    print(f"[Serial] Error: Cannot open {SERIAL_PORT}")
    print("Action: Check the port or unplug/replug USB")
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    if ser and ser.is_open:
        ser.close()
    print("Cleanup done.") 