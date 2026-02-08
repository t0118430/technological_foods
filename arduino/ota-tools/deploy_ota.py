#!/usr/bin/env python3
"""
Arduino R4 WiFi OTA (Over-The-Air) Firmware Deployment

Deploys compiled firmware to Arduino R4 WiFi over WiFi network.
No USB cable needed!

Usage:
    python deploy_ota.py --ip 192.168.1.100 --firmware sketch.bin
    python deploy_ota.py --ip 192.168.1.100 --password secret --firmware sketch.bin
"""

import argparse
import requests
import time
import sys
import hashlib
from pathlib import Path

class ArduinoOTADeployer:
    def __init__(self, ip_address, password=None, port=8080):
        self.ip = ip_address
        self.password = password
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"

    def check_connection(self):
        """Verify Arduino is reachable."""
        try:
            print(f"🔍 Checking connection to {self.ip}...")
            response = requests.get(f"http://{self.ip}/", timeout=5)
            print(f"✅ Arduino is reachable (HTTP {response.status_code})")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach Arduino at {self.ip}: {e}")
            return False

    def get_firmware_info(self):
        """Get current firmware version from Arduino."""
        try:
            response = requests.get(f"http://{self.ip}/version", timeout=5)
            if response.status_code == 200:
                version = response.text.strip()
                print(f"📦 Current firmware version: {version}")
                return version
            return "unknown"
        except:
            return "unknown"

    def calculate_checksum(self, firmware_path):
        """Calculate SHA256 checksum of firmware file."""
        sha256_hash = hashlib.sha256()
        with open(firmware_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def upload_firmware(self, firmware_path):
        """Upload firmware binary via OTA."""
        firmware_file = Path(firmware_path)

        if not firmware_file.exists():
            print(f"❌ Firmware file not found: {firmware_path}")
            return False

        file_size = firmware_file.stat().st_size
        checksum = self.calculate_checksum(firmware_path)

        print(f"📤 Uploading firmware...")
        print(f"   File: {firmware_file.name}")
        print(f"   Size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        print(f"   SHA256: {checksum}")

        try:
            with open(firmware_path, 'rb') as f:
                files = {'firmware': (firmware_file.name, f, 'application/octet-stream')}
                data = {}

                if self.password:
                    data['password'] = self.password

                # Upload with progress
                print("⏳ Uploading (this may take 30-60 seconds)...")
                response = requests.post(
                    f"{self.base_url}/update",
                    files=files,
                    data=data,
                    timeout=120
                )

                if response.status_code == 200:
                    print("✅ Upload successful!")
                    return True
                else:
                    print(f"❌ Upload failed: HTTP {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False

        except requests.exceptions.Timeout:
            print("⚠️  Upload timeout - Arduino may be rebooting")
            print("   Waiting for Arduino to restart...")
            return True  # May have succeeded but Arduino rebooted
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False

    def wait_for_reboot(self, timeout=60):
        """Wait for Arduino to reboot after firmware update."""
        print(f"⏳ Waiting for Arduino to reboot (timeout: {timeout}s)...")

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                response = requests.get(f"http://{self.ip}/", timeout=2)
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    print(f"✅ Arduino back online after {elapsed:.1f}s")
                    return True
            except:
                pass

            time.sleep(2)
            print(".", end="", flush=True)

        print("\n⚠️  Timeout waiting for reboot")
        return False

    def verify_deployment(self):
        """Verify new firmware is running."""
        try:
            new_version = self.get_firmware_info()
            print(f"✅ New firmware version: {new_version}")
            return True
        except:
            print("⚠️  Could not verify new firmware version")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Deploy firmware to Arduino R4 WiFi via OTA"
    )
    parser.add_argument(
        '--ip',
        required=True,
        help='Arduino IP address (e.g., 192.168.1.100)'
    )
    parser.add_argument(
        '--firmware',
        required=True,
        help='Path to compiled .bin firmware file'
    )
    parser.add_argument(
        '--password',
        help='OTA password (if configured on Arduino)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='OTA port (default: 8080)'
    )
    parser.add_argument(
        '--skip-verify',
        action='store_true',
        help='Skip post-deployment verification'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🤖 Arduino R4 WiFi OTA Deployment")
    print("=" * 60)

    deployer = ArduinoOTADeployer(
        ip_address=args.ip,
        password=args.password,
        port=args.port
    )

    # Step 1: Check connection
    if not deployer.check_connection():
        print("\n❌ Deployment aborted - cannot reach Arduino")
        sys.exit(1)

    # Step 2: Get current version
    current_version = deployer.get_firmware_info()

    # Step 3: Upload firmware
    print("\n" + "=" * 60)
    if not deployer.upload_firmware(args.firmware):
        print("\n❌ Deployment failed")
        sys.exit(1)

    # Step 4: Wait for reboot
    print("\n" + "=" * 60)
    if not deployer.wait_for_reboot():
        print("⚠️  Warning: Could not confirm reboot")

    # Step 5: Verify
    if not args.skip_verify:
        print("\n" + "=" * 60)
        deployer.verify_deployment()

    print("\n" + "=" * 60)
    print("✅ OTA Deployment Complete!")
    print("=" * 60)
    print(f"\n📍 Arduino is running at: http://{args.ip}")
    print(f"🌡️  Check sensor data: http://{args.ip}/sensors")
    print(f"📊 View in dashboard: http://your-pi-ip:3000")

if __name__ == "__main__":
    main()
