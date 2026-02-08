"""
Growth Stage Manager - Stage-aware monitoring and rule application.

Manages crop lifecycle and applies different optimal conditions
based on growth stage (seedling, vegetative, maturity).

Author: AgriTech Hydroponics
License: MIT
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from database import db
from config_loader import config_loader

logger = logging.getLogger('growth-stage-manager')


class GrowthStageManager:
    """
    Manages growth stages and applies stage-specific monitoring.

    Responsibilities:
    - Track crop lifecycle
    - Provide stage-specific optimal ranges
    - Generate stage-aware rules
    - Auto-advance stages based on time
    - Report on crop progress
    """

    def __init__(self):
        self.db = db
        self.config_loader = config_loader

    def create_crop_batch(self, variety: str, plant_date: str = None,
                         zone: str = 'main', notes: str = None) -> Dict[str, Any]:
        """
        Start a new crop batch.

        Args:
            variety: Variety name (rosso_premium, curly_green)
            plant_date: Plant date (ISO format, defaults to today)
            zone: Growing zone identifier
            notes: Optional notes

        Returns:
            Crop information with ID
        """
        crop_id = self.db.create_crop(variety, plant_date, zone, notes)

        # Load variety config
        config = self.config_loader.load_variety(variety)

        # Get expected harvest date
        growth_stages = config.get('growth_stages', {})
        maturity_stage = growth_stages.get('maturity', {})
        maturity_days_str = maturity_stage.get('days', '30-60')

        # Parse max days for harvest estimate
        if '-' in maturity_days_str:
            _, max_days = maturity_days_str.split('-')
            max_days = int(max_days)
        else:
            max_days = int(maturity_days_str)

        plant_datetime = datetime.fromisoformat(plant_date) if plant_date else datetime.now()

        # Log event
        self.db.log_event(
            'crop_created',
            f"New {variety} crop planted",
            'info',
            {'crop_id': crop_id, 'variety': variety, 'zone': zone}
        )

        return {
            'crop_id': crop_id,
            'variety': variety,
            'plant_date': plant_date or datetime.now().date().isoformat(),
            'current_stage': 'seedling',
            'expected_harvest_days': max_days,
            'zone': zone
        }

    def get_current_conditions(self, crop_id: int) -> Optional[Dict[str, Any]]:
        """
        Get optimal conditions for crop's current stage.

        Args:
            crop_id: Crop ID

        Returns:
            Stage-specific optimal ranges
        """
        crop = self.db.get_crop(crop_id)
        if not crop:
            return None

        variety = crop['variety']
        current_stage_info = self.db.get_current_stage(crop_id)

        if not current_stage_info:
            return None

        current_stage = current_stage_info['stage']

        # Load variety config
        config = self.config_loader.load_variety(variety)
        growth_stages = config.get('growth_stages', {})
        stage_config = growth_stages.get(current_stage, {})

        # Get stage-specific EC and light hours
        stage_ec = stage_config.get('ec_range', '1.2-1.8')
        stage_light_hours = stage_config.get('light_hours', 14)
        stage_notes = stage_config.get('notes', '')

        # Parse EC range
        if '-' in stage_ec:
            ec_min, ec_max = stage_ec.split('-')
            ec_min, ec_max = float(ec_min), float(ec_max)
        else:
            ec_min = ec_max = float(stage_ec)

        # Get base optimal ranges (temp, humidity, pH don't change much by stage)
        optimal_ranges = config.get('optimal_ranges', {})

        return {
            'crop_id': crop_id,
            'variety': variety,
            'current_stage': current_stage,
            'stage_started': current_stage_info['started_at'],
            'days_in_stage': self._calculate_days(current_stage_info['started_at']),
            'conditions': {
                'temperature': optimal_ranges.get('temperature', {}),
                'humidity': optimal_ranges.get('humidity', {}),
                'ph': optimal_ranges.get('ph', {}),
                'ec': {
                    'optimal_min': ec_min,
                    'optimal_max': ec_max,
                    'unit': 'mS/cm',
                    'stage_specific': True
                },
                'light_hours': stage_light_hours,
                'notes': stage_notes
            }
        }

    def _calculate_days(self, started_at: str) -> int:
        """Calculate days since date."""
        started = datetime.fromisoformat(started_at)
        return (datetime.now() - started).days

    def check_and_advance_stages(self) -> List[Dict[str, Any]]:
        """
        Check all crops and advance stages if ready.

        Returns:
            List of stage advancements performed
        """
        ready_crops = self.db.check_stage_advancement()
        advanced = []

        for crop_info in ready_crops:
            crop_id = crop_info['crop_id']
            next_stage = crop_info['next_stage']
            variety = crop_info['variety']

            # Auto-advance
            self.db.advance_stage(
                crop_id,
                next_stage,
                notes=f"Auto-advanced from {crop_info['current_stage']} after {crop_info['days_in_stage']} days"
            )

            # Log event
            self.db.log_event(
                'stage_advanced',
                f"{variety} crop {crop_id} advanced to {next_stage}",
                'info',
                crop_info
            )

            advanced.append({
                'crop_id': crop_id,
                'variety': variety,
                'from_stage': crop_info['current_stage'],
                'to_stage': next_stage,
                'days_in_previous_stage': crop_info['days_in_stage']
            })

            logger.info(f"Auto-advanced crop {crop_id} to {next_stage}")

        return advanced

    def get_stage_specific_rules(self, crop_id: int) -> List[Dict[str, Any]]:
        """
        Generate monitoring rules specific to current growth stage.

        Args:
            crop_id: Crop ID

        Returns:
            List of stage-specific monitoring rules
        """
        conditions = self.get_current_conditions(crop_id)
        if not conditions:
            return []

        variety = conditions['variety']
        stage = conditions['current_stage']
        stage_conditions = conditions['conditions']

        # Load base config
        config = self.config_loader.load_variety(variety)
        preventive = config.get('preventive_actions', {})

        rules = []

        # EC rules (stage-specific!)
        ec_config = stage_conditions['ec']
        if ec_config.get('stage_specific'):
            rules.append({
                'id': f"{variety}_{stage}_ec_low",
                'name': f"{variety} ({stage}): EC Baixo",
                'enabled': True,
                'sensor': 'ec',
                'condition': 'below',
                'threshold': ec_config['optimal_min'],
                'warning_margin': 0.2,
                'stage': stage,
                'action': {
                    'type': 'notify',
                    'severity': 'warning',
                    'message': f"EC baixo para {stage} stage - nutrientes insuficientes",
                    'recommended_action': preventive.get('low_ec', 'Add nutrients')
                }
            })

            rules.append({
                'id': f"{variety}_{stage}_ec_high",
                'name': f"{variety} ({stage}): EC Alto",
                'enabled': True,
                'sensor': 'ec',
                'condition': 'above',
                'threshold': ec_config['optimal_max'],
                'warning_margin': 0.2,
                'stage': stage,
                'action': {
                    'type': 'notify',
                    'severity': 'warning',
                    'message': f"EC alto para {stage} stage - risco de queima",
                    'recommended_action': preventive.get('high_ec', 'Dilute solution')
                }
            })

        # Temperature rules (variety-specific, less stage variance)
        temp_config = stage_conditions.get('temperature', {})
        if temp_config:
            rules.append({
                'id': f"{variety}_{stage}_temp_low",
                'name': f"{variety} ({stage}): Temperatura Baixa",
                'enabled': True,
                'sensor': 'temperature',
                'condition': 'below',
                'threshold': temp_config.get('critical_min', 15.0),
                'warning_margin': temp_config.get('warning_margin', 2.0),
                'stage': stage,
                'action': {
                    'type': 'notify',
                    'severity': 'critical',
                    'message': f"Temperatura baixa - {stage} stage sensível",
                    'recommended_action': preventive.get('low_temperature', 'Check heating')
                }
            })

        return rules

    def get_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard of all active crops and their stages.

        Returns:
            Dashboard data with crop status, stages, and conditions
        """
        active_crops = self.db.get_active_crops()

        dashboard = {
            'total_active_crops': len(active_crops),
            'crops': [],
            'stage_summary': {
                'seedling': 0,
                'vegetative': 0,
                'maturity': 0
            },
            'variety_summary': {},
            'alerts': []
        }

        for crop in active_crops:
            crop_id = crop['id']
            variety = crop['variety']
            stage = crop['current_stage']

            # Get current conditions
            conditions = self.get_current_conditions(crop_id)

            # Count by stage
            if stage in dashboard['stage_summary']:
                dashboard['stage_summary'][stage] += 1

            # Count by variety
            if variety not in dashboard['variety_summary']:
                dashboard['variety_summary'][variety] = 0
            dashboard['variety_summary'][variety] += 1

            # Add to crops list
            dashboard['crops'].append({
                'crop_id': crop_id,
                'variety': variety,
                'plant_date': crop['plant_date'],
                'current_stage': stage,
                'days_in_stage': conditions['days_in_stage'] if conditions else 0,
                'zone': crop['zone'],
                'conditions': conditions['conditions'] if conditions else {}
            })

        # Check for crops ready to advance
        ready_to_advance = self.db.check_stage_advancement()
        if ready_to_advance:
            dashboard['alerts'].append({
                'type': 'stage_advancement_due',
                'count': len(ready_to_advance),
                'crops': ready_to_advance
            })

        # Check for calibrations due
        due_calibrations = self.db.get_due_calibrations()
        if due_calibrations:
            dashboard['alerts'].append({
                'type': 'calibration_due',
                'sensors': due_calibrations
            })

        return dashboard

    def record_manual_stage_advance(self, crop_id: int, new_stage: str,
                                   reason: str = None) -> bool:
        """
        Manually advance crop to next stage (operator decision).

        Args:
            crop_id: Crop ID
            new_stage: New stage name
            reason: Reason for manual advancement

        Returns:
            Success status
        """
        result = self.db.advance_stage(crop_id, new_stage, notes=reason)

        if result:
            crop = self.db.get_crop(crop_id)
            self.db.log_event(
                'stage_advanced_manual',
                f"Crop {crop_id} ({crop['variety']}) manually advanced to {new_stage}",
                'info',
                {'crop_id': crop_id, 'stage': new_stage, 'reason': reason}
            )

        return result

    def get_harvest_analytics(self) -> Dict[str, Any]:
        """Get harvest analytics and performance metrics."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Total harvests by variety
            cursor.execute('''
                SELECT c.variety, COUNT(*) as count, AVG(h.weight_kg) as avg_weight,
                       AVG(h.market_value) as avg_value
                FROM harvests h
                JOIN crops c ON h.crop_id = c.id
                GROUP BY c.variety
            ''')

            variety_stats = [dict(row) for row in cursor.fetchall()]

            # Recent harvests
            cursor.execute('''
                SELECT h.*, c.variety, c.plant_date
                FROM harvests h
                JOIN crops c ON h.crop_id = c.id
                ORDER BY h.harvest_date DESC
                LIMIT 10
            ''')

            recent = [dict(row) for row in cursor.fetchall()]

            return {
                'by_variety': variety_stats,
                'recent_harvests': recent
            }


# Global instance
growth_manager = GrowthStageManager()
