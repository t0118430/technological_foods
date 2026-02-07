import os
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('ac-controller')

# Haier hOn credentials
HON_EMAIL = os.getenv('HON_EMAIL', '')
HON_PASSWORD = os.getenv('HON_PASSWORD', '')

# AC state cache
ac_state = {
    "available": False,
    "power": False,
    "target_temp": 24,
    "current_temp": None,
    "mode": "auto",  # auto, cool, heat, fan, dry
    "fan_speed": "auto",
    "last_update": None
}

# Temperature thresholds for auto control
AUTO_CONTROL = {
    "enabled": False,
    "max_temp": 28.0,  # Turn AC on (cooling) above this
    "min_temp": 18.0,  # Turn AC off below this
    "target_temp": 24   # Target temperature for AC
}


class HaierACController:
    def __init__(self):
        self.hon = None
        self.ac_device = None
        self._initialized = False

    async def initialize(self):
        """Initialize connection to Haier hOn API"""
        if not HON_EMAIL or not HON_PASSWORD:
            logger.warning("HON_EMAIL and HON_PASSWORD not set")
            return False

        try:
            from pyhon import Hon

            self.hon = Hon(HON_EMAIL, HON_PASSWORD)
            await self.hon.create()

            # Find AC device
            for device in self.hon.appliances:
                if device.appliance_type.lower() in ['ac', 'climate', 'airconditioner']:
                    self.ac_device = device
                    logger.info(f"Found AC: {device.nick_name} ({device.model_name})")
                    break

            if self.ac_device:
                self._initialized = True
                await self.update_state()
                return True
            else:
                logger.warning("No AC device found in hOn account")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Haier API: {e}")
            return False

    async def update_state(self):
        """Update AC state from API"""
        if not self._initialized:
            return

        try:
            await self.ac_device.load_attributes()

            ac_state["available"] = True
            ac_state["power"] = self.ac_device.get("onOffStatus", False)
            ac_state["target_temp"] = self.ac_device.get("tempSel", 24)
            ac_state["current_temp"] = self.ac_device.get("tempIndoor", None)
            ac_state["mode"] = self.ac_device.get("machMode", "auto")
            ac_state["fan_speed"] = self.ac_device.get("windSpeed", "auto")
            ac_state["last_update"] = asyncio.get_event_loop().time()

        except Exception as e:
            logger.error(f"Failed to update AC state: {e}")
            ac_state["available"] = False

    async def set_power(self, on: bool) -> bool:
        """Turn AC on or off"""
        if not self._initialized:
            return False

        try:
            await self.ac_device.commands["onOffStatus"].set(on)
            await self.ac_device.commands["onOffStatus"].send()
            ac_state["power"] = on
            logger.info(f"AC power set to: {'ON' if on else 'OFF'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set power: {e}")
            return False

    async def set_temperature(self, temp: int) -> bool:
        """Set target temperature"""
        if not self._initialized:
            return False

        try:
            temp = max(16, min(30, temp))  # Clamp between 16-30
            await self.ac_device.commands["tempSel"].set(temp)
            await self.ac_device.commands["tempSel"].send()
            ac_state["target_temp"] = temp
            logger.info(f"AC temperature set to: {temp}°C")
            return True
        except Exception as e:
            logger.error(f"Failed to set temperature: {e}")
            return False

    async def set_mode(self, mode: str) -> bool:
        """Set AC mode (auto, cool, heat, fan, dry)"""
        if not self._initialized:
            return False

        mode_map = {
            "auto": 0,
            "cool": 1,
            "heat": 4,
            "fan": 2,
            "dry": 3
        }

        if mode.lower() not in mode_map:
            return False

        try:
            await self.ac_device.commands["machMode"].set(mode_map[mode.lower()])
            await self.ac_device.commands["machMode"].send()
            ac_state["mode"] = mode.lower()
            logger.info(f"AC mode set to: {mode}")
            return True
        except Exception as e:
            logger.error(f"Failed to set mode: {e}")
            return False

    def get_state(self) -> Dict[str, Any]:
        """Get current AC state"""
        return ac_state.copy()


# Global controller instance
controller = HaierACController()


def check_auto_control(current_temp: float) -> Optional[str]:
    """
    Check if AC should be automatically controlled based on temperature.
    Returns action taken: 'turned_on', 'turned_off', or None
    """
    if not AUTO_CONTROL["enabled"]:
        return None

    if not controller._initialized:
        return None

    action = None

    if current_temp > AUTO_CONTROL["max_temp"] and not ac_state["power"]:
        # Too hot - turn on AC
        asyncio.create_task(controller.set_power(True))
        asyncio.create_task(controller.set_temperature(AUTO_CONTROL["target_temp"]))
        asyncio.create_task(controller.set_mode("cool"))
        action = "turned_on"
        logger.info(f"Auto control: Turning AC ON (temp: {current_temp}°C > {AUTO_CONTROL['max_temp']}°C)")

    elif current_temp < AUTO_CONTROL["min_temp"] and ac_state["power"]:
        # Cool enough - turn off AC
        asyncio.create_task(controller.set_power(False))
        action = "turned_off"
        logger.info(f"Auto control: Turning AC OFF (temp: {current_temp}°C < {AUTO_CONTROL['min_temp']}°C)")

    return action


def get_auto_control_settings() -> Dict[str, Any]:
    """Get auto control settings"""
    return AUTO_CONTROL.copy()


def set_auto_control_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update auto control settings"""
    if "enabled" in settings:
        AUTO_CONTROL["enabled"] = bool(settings["enabled"])
    if "max_temp" in settings:
        AUTO_CONTROL["max_temp"] = float(settings["max_temp"])
    if "min_temp" in settings:
        AUTO_CONTROL["min_temp"] = float(settings["min_temp"])
    if "target_temp" in settings:
        AUTO_CONTROL["target_temp"] = int(settings["target_temp"])

    return AUTO_CONTROL.copy()
