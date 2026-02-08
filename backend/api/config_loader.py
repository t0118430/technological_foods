"""
Configuration Loader - DRY principle for variety-specific hydroponics configs.

Loads base configuration and merges with variety-specific overrides.
Supports multiple lettuce varieties with shared base settings.

Author: AgriTech Hydroponics
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy

logger = logging.getLogger('config-loader')

CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'
BASE_CONFIG_FILE = CONFIG_DIR / 'base_hydroponics.json'


class ConfigLoader:
    """
    Loads and merges hydroponic variety configurations.

    DRY Principle:
    - Base config contains common settings
    - Variety configs contain only overrides
    - Merged result provides complete configuration
    """

    def __init__(self):
        self.base_config: Optional[Dict[str, Any]] = None
        self.varieties: Dict[str, Dict[str, Any]] = {}
        self.load_base_config()

    def load_base_config(self):
        """Load the base hydroponics configuration."""
        if not BASE_CONFIG_FILE.exists():
            logger.error(f"Base config not found: {BASE_CONFIG_FILE}")
            self.base_config = {}
            return

        with open(BASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.base_config = json.load(f)

        logger.info("Base hydroponics configuration loaded")

    def load_variety(self, variety_name: str) -> Dict[str, Any]:
        """
        Load a variety configuration and merge with base.

        Args:
            variety_name: Name of variety (e.g., 'rosso_premium', 'curly_green')

        Returns:
            Complete merged configuration
        """
        if variety_name in self.varieties:
            return self.varieties[variety_name]

        variety_file = CONFIG_DIR / f'variety_{variety_name}.json'

        if not variety_file.exists():
            logger.error(f"Variety config not found: {variety_file}")
            return self.base_config.copy()

        with open(variety_file, 'r', encoding='utf-8') as f:
            variety_config = json.load(f)

        # Merge configs (variety overrides base)
        merged = self._merge_configs(self.base_config, variety_config)

        # Add variety rules for automatic use
        merged['rules'] = self._generate_rules_for_variety(variety_name, merged)

        self.varieties[variety_name] = merged
        logger.info(f"Variety '{variety_name}' configuration loaded and merged")

        return merged

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configurations (override takes precedence).

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = deepcopy(base)

        for key, value in override.items():
            if key.startswith('_'):
                # Metadata fields - just set them
                result[key] = value
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursive merge for nested dicts
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def _generate_rules_for_variety(self, variety_name: str, config: Dict[str, Any]) -> list:
        """
        Generate monitoring rules based on variety configuration.

        Args:
            variety_name: Name of the variety
            config: Merged configuration

        Returns:
            List of monitoring rules
        """
        rules = []
        optimal = config.get('optimal_ranges', {})
        preventive = config.get('preventive_actions', {})

        variety_display = config.get('variety', {}).get('display_name', variety_name)

        # Temperature rules
        if 'temperature' in optimal:
            temp = optimal['temperature']
            base_temp = config.get('base_ranges', {}).get('temperature', {})

            rules.append({
                "id": f"{variety_name}_temp_low",
                "name": f"{variety_display}: Temperatura Baixa",
                "enabled": True,
                "sensor": "temperature",
                "condition": "below",
                "threshold": temp.get('critical_min', base_temp.get('critical_min', 15.0)),
                "warning_margin": temp.get('warning_margin', 2.0),
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": f"{variety_display}: Temperatura muito baixa",
                    "recommended_action": preventive.get('low_temperature', 'Check heating system')
                },
                "preventive_message": f"{variety_display}: Temperatura aproximando mínimo",
                "preventive_action": preventive.get('low_temperature', 'Monitor heating')
            })

            rules.append({
                "id": f"{variety_name}_temp_high",
                "name": f"{variety_display}: Temperatura Alta",
                "enabled": True,
                "sensor": "temperature",
                "condition": "above",
                "threshold": temp.get('critical_max', base_temp.get('critical_max', 28.0)),
                "warning_margin": temp.get('warning_margin', 2.0),
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": f"{variety_display}: Temperatura muito alta",
                    "recommended_action": preventive.get('high_temperature', 'Increase ventilation')
                },
                "preventive_message": f"{variety_display}: Temperatura aproximando máximo",
                "preventive_action": preventive.get('high_temperature', 'Increase air circulation')
            })

        # Humidity rules
        if 'humidity' in optimal:
            hum = optimal['humidity']
            base_hum = config.get('base_ranges', {}).get('humidity', {})

            rules.append({
                "id": f"{variety_name}_humidity_low",
                "name": f"{variety_display}: Humidade Baixa",
                "enabled": True,
                "sensor": "humidity",
                "condition": "below",
                "threshold": hum.get('critical_min', base_hum.get('critical_min', 40.0)),
                "warning_margin": hum.get('warning_margin', 5.0),
                "action": {
                    "type": "notify",
                    "severity": "warning",
                    "message": f"{variety_display}: Humidade muito baixa",
                    "recommended_action": preventive.get('low_humidity', 'Add humidifier')
                },
                "preventive_message": f"{variety_display}: Humidade aproximando mínimo",
                "preventive_action": preventive.get('low_humidity', 'Prepare humidifier')
            })

            rules.append({
                "id": f"{variety_name}_humidity_high",
                "name": f"{variety_display}: Humidade Alta",
                "enabled": True,
                "sensor": "humidity",
                "condition": "above",
                "threshold": hum.get('critical_max', base_hum.get('critical_max', 80.0)),
                "warning_margin": hum.get('warning_margin', 5.0),
                "action": {
                    "type": "notify",
                    "severity": "warning",
                    "message": f"{variety_display}: Humidade muito alta - risco de mofo",
                    "recommended_action": preventive.get('high_humidity', 'Increase ventilation')
                },
                "preventive_message": f"{variety_display}: Humidade aproximando máximo",
                "preventive_action": preventive.get('high_humidity', 'Turn on exhaust fans')
            })

        # pH rules
        if 'ph' in optimal:
            ph = optimal['ph']
            base_ph = config.get('base_ranges', {}).get('ph', {})

            rules.append({
                "id": f"{variety_name}_ph_low",
                "name": f"{variety_display}: pH Ácido",
                "enabled": True,
                "sensor": "ph",
                "condition": "below",
                "threshold": ph.get('critical_min', base_ph.get('critical_min', 5.5)),
                "warning_margin": ph.get('warning_margin', 0.3),
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": f"{variety_display}: pH muito ácido",
                    "recommended_action": preventive.get('low_ph', 'Add pH up solution')
                },
                "preventive_message": f"{variety_display}: pH aproximando mínimo",
                "preventive_action": preventive.get('low_ph', 'Prepare pH up solution')
            })

            rules.append({
                "id": f"{variety_name}_ph_high",
                "name": f"{variety_display}: pH Alcalino",
                "enabled": True,
                "sensor": "ph",
                "condition": "above",
                "threshold": ph.get('critical_max', base_ph.get('critical_max', 7.0)),
                "warning_margin": ph.get('warning_margin', 0.3),
                "action": {
                    "type": "notify",
                    "severity": "critical",
                    "message": f"{variety_display}: pH muito alcalino",
                    "recommended_action": preventive.get('high_ph', 'Add pH down solution')
                },
                "preventive_message": f"{variety_display}: pH aproximando máximo",
                "preventive_action": preventive.get('high_ph', 'Prepare pH down solution')
            })

        # EC rules
        if 'ec' in optimal:
            ec = optimal['ec']
            base_ec = config.get('base_ranges', {}).get('ec', {})

            rules.append({
                "id": f"{variety_name}_ec_low",
                "name": f"{variety_display}: EC Baixo",
                "enabled": True,
                "sensor": "ec",
                "condition": "below",
                "threshold": ec.get('critical_min', base_ec.get('critical_min', 0.8)),
                "warning_margin": ec.get('warning_margin', 0.3),
                "action": {
                    "type": "notify",
                    "severity": "warning",
                    "message": f"{variety_display}: Nutrientes insuficientes",
                    "recommended_action": preventive.get('low_ec', 'Add nutrient solution')
                },
                "preventive_message": f"{variety_display}: EC aproximando mínimo",
                "preventive_action": preventive.get('low_ec', 'Prepare nutrient solution')
            })

            rules.append({
                "id": f"{variety_name}_ec_high",
                "name": f"{variety_display}: EC Alto",
                "enabled": True,
                "sensor": "ec",
                "condition": "above",
                "threshold": ec.get('critical_max', base_ec.get('critical_max', 2.5)),
                "warning_margin": ec.get('warning_margin', 0.3),
                "action": {
                    "type": "notify",
                    "severity": "warning",
                    "message": f"{variety_display}: Concentração de nutrientes muito alta",
                    "recommended_action": preventive.get('high_ec', 'Dilute with fresh water')
                },
                "preventive_message": f"{variety_display}: EC aproximando máximo",
                "preventive_action": preventive.get('high_ec', 'Prepare to dilute solution')
            })

        return rules

    def get_all_varieties(self) -> list:
        """Get list of available variety configurations."""
        varieties = []
        for file in CONFIG_DIR.glob('variety_*.json'):
            variety_name = file.stem.replace('variety_', '')
            varieties.append(variety_name)
        return varieties

    def get_calibration_schedule(self, variety_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get sensor calibration schedule from configuration.

        Args:
            variety_config: Merged variety configuration

        Returns:
            Calibration schedule with sensor details
        """
        sensors = variety_config.get('sensors', {})
        schedule = {}

        for sensor_name, sensor_info in sensors.items():
            interval_days = sensor_info.get('calibration_interval_days', 90)
            schedule[sensor_name] = {
                'interval_days': interval_days,
                'accuracy': sensor_info.get('accuracy', 'N/A'),
                'type': sensor_info.get('sensor_type', 'unknown'),
                'requires_solution': sensor_info.get('requires_buffer_solution', False)
                                    or sensor_info.get('requires_standard_solution', False),
                'solutions': sensor_info.get('buffer_solutions', []) or [sensor_info.get('standard_solution', '')]
            }

        return schedule

    def get_maintenance_schedule(self, variety_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get maintenance schedule from configuration."""
        return variety_config.get('maintenance_schedule', {})

    def get_time_based_notifications(self, variety_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get time-based notification schedule."""
        return variety_config.get('time_based_notifications', {})


# Global instance
config_loader = ConfigLoader()
