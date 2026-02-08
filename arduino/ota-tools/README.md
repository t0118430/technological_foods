# 🤖 Arduino R4 WiFi - OTA Deployment Tools

## Over-The-Air (OTA) Firmware Updates

Deploy firmware to your Arduino R4 WiFi **wirelessly** - no USB cable needed!

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or manually:
pip install requests pyserial
```

### Deploy Firmware

```bash
# Basic deployment
python deploy_ota.py --ip 192.168.1.100 --firmware ../build/sketch.bin

# With OTA password (if configured)
python deploy_ota.py --ip 192.168.1.100 --password mySecretPass --firmware sketch.bin
```

---

## 📋 Step-by-Step Guide

### 1. Build Firmware

#### Using Arduino CLI
```bash
# Install Arduino CLI
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Install Arduino R4 WiFi core
arduino-cli core install arduino:renesas_uno

# Install libraries
arduino-cli lib install "DHT sensor library"
arduino-cli lib install "ArduinoHttpClient"
arduino-cli lib install "WiFiS3"

# Compile sketch
cd ../temp_hum_light_sending_api
arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi --output-dir ../build
```

#### Using Arduino IDE
1. Open sketch in Arduino IDE
2. Select **Tools → Board → Arduino UNO R4 WiFi**
3. **Sketch → Export Compiled Binary**
4. Find `.bin` file in sketch folder

### 2. Find Arduino IP Address

```bash
# Check your router's DHCP table
# Or use the serial monitor to see IP at boot

# Arduino prints:
# "Connected to WiFi"
# "IP address: 192.168.1.100"
```

### 3. Deploy

```bash
python deploy_ota.py --ip 192.168.1.100 --firmware path/to/sketch.bin
```

**Output:**
```
============================================================
🤖 Arduino R4 WiFi OTA Deployment
============================================================
🔍 Checking connection to 192.168.1.100...
✅ Arduino is reachable (HTTP 200)
📦 Current firmware version: 1.2.0

============================================================
📤 Uploading firmware...
   File: temp_hum_light_sending_api.ino.bin
   Size: 123,456 bytes (120.56 KB)
   SHA256: abc123...
⏳ Uploading (this may take 30-60 seconds)...
✅ Upload successful!

============================================================
⏳ Waiting for Arduino to reboot (timeout: 60s)...
✅ Arduino back online after 8.3s

============================================================
✅ New firmware version: 1.3.0

============================================================
✅ OTA Deployment Complete!
============================================================

📍 Arduino is running at: http://192.168.1.100
🌡️  Check sensor data: http://192.168.1.100/sensors
```

---

## 🔧 Configuration

### Arduino Sketch Requirements

Your Arduino sketch must include OTA update capability. Add this to your sketch:

```cpp
#include <WiFiS3.h>
#include <WiFiServer.h>

// OTA Configuration
const int OTA_PORT = 8080;
const char* OTA_PASSWORD = "your-secret-password"; // Optional
WiFiServer otaServer(OTA_PORT);

void setup() {
    // ... your existing setup ...

    // Start OTA server
    otaServer.begin();
    Serial.println("OTA server started on port 8080");
}

void loop() {
    // ... your existing loop ...

    // Handle OTA updates
    handleOTA();
}

void handleOTA() {
    WiFiClient client = otaServer.available();
    if (client) {
        // Handle firmware upload
        // See full implementation in temp_hum_light_sending_api.ino
    }
}
```

### Environment Variables

Set these in your CI/CD pipeline (GitHub Secrets):

```bash
ARDUINO_IP=192.168.1.100          # Arduino IP address
ARDUINO_OTA_PASSWORD=secret       # OTA password (optional)
```

---

## 🔒 Security

### OTA Password (Recommended)

Protect OTA updates with a password:

**In Arduino sketch:**
```cpp
const char* OTA_PASSWORD = "MySecurePassword123";
```

**When deploying:**
```bash
python deploy_ota.py --ip 192.168.1.100 --password MySecurePassword123 --firmware sketch.bin
```

### Network Security

- ✅ Use WPA2/WPA3 WiFi encryption
- ✅ Keep Arduino on isolated VLAN if possible
- ✅ Use strong OTA password
- ✅ Regularly update firmware
- ⚠️ OTA transfers are **not encrypted** by default

---

## 📊 Automated Deployment (CI/CD)

### GitHub Actions Workflow

See `.github/workflows/deploy-arduino-ota.yml`

Automatically:
1. **Compiles** firmware on code push
2. **Validates** sketch syntax
3. **Deploys** via OTA
4. **Verifies** deployment success
5. **Creates releases** with binaries

### Manual Trigger

Deploy from GitHub Actions UI:
```
Actions → Deploy Arduino Firmware (OTA) → Run workflow
```

---

## 🛠️ Troubleshooting

### Arduino Not Reachable

```
❌ Cannot reach Arduino at 192.168.1.100
```

**Solutions:**
- Verify Arduino is powered on and connected to WiFi
- Check IP address (may have changed via DHCP)
- Ping Arduino: `ping 192.168.1.100`
- Check firewall rules

### Upload Timeout

```
❌ Upload error: Timeout
```

**Solutions:**
- Arduino may be rebooting (this is normal)
- Wait 30 seconds and check if new firmware is running
- Try again with longer timeout: `--timeout 180`

### Upload Failed

```
❌ Upload failed: HTTP 403
```

**Solutions:**
- Wrong OTA password
- Arduino OTA server not enabled
- Check Arduino serial monitor for errors

### Arduino Won't Reboot

```
⚠️ Timeout waiting for reboot
```

**Solutions:**
- Manually power cycle Arduino
- Check if new firmware has syntax errors
- Reflash via USB if Arduino is bricked

---

## 📈 Deployment Best Practices

### 1. Test First
```bash
# Always test on development Arduino first
python deploy_ota.py --ip 192.168.1.99 --firmware test.bin
```

### 2. Version Tracking
Add version info to your sketch:
```cpp
const char* FIRMWARE_VERSION = "1.3.0";
```

### 3. Rollback Plan
Keep previous `.bin` files:
```bash
cp sketch.bin backups/sketch_v1.2.0.bin
```

### 4. Monitor Logs
Watch serial output during deployment:
```bash
# Using Arduino CLI
arduino-cli monitor --port /dev/ttyACM0 --baud 115200
```

### 5. Deployment Windows
- ✅ Deploy during low-traffic periods
- ✅ Notify users of maintenance
- ⚠️ Avoid deploying during critical operations

---

## 🔄 Emergency Recovery

### If OTA Fails

1. **Try USB Flash**:
   ```bash
   arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port COM3 --input-file sketch.bin
   ```

2. **Factory Reset**:
   - Hold reset button for 10 seconds
   - Reflash known-good firmware via USB

3. **Check Backups**:
   ```bash
   ls -lh backups/
   python deploy_ota.py --ip 192.168.1.100 --firmware backups/last_known_good.bin
   ```

---

## 📚 Resources

- [Arduino R4 WiFi Documentation](https://docs.arduino.cc/hardware/uno-r4-wifi)
- [Arduino CLI](https://arduino.github.io/arduino-cli/)
- [OTA Updates Guide](https://docs.arduino.cc/learn/programming/ota-updates)

---

**Status**: ✅ Production Ready
**Tested on**: Arduino UNO R4 WiFi
**Python**: 3.8+
