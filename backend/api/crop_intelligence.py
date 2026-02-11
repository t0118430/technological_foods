"""
Crop Intelligence Service - Predictive & correlation analytics.

Correlates sensor conditions with harvest outcomes, provides growth
optimization recommendations, yield predictions, and health scoring.

Author: AgriTech Hydroponics
License: MIT
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger('crop-intelligence')


class CropIntelligence:
    """Predictive analytics and crop health scoring."""

    def __init__(self):
        self._db = None
        self._config_loader = None

    @property
    def db(self):
        if self._db is None:
            from database import db
            self._db = db
        return self._db

    @property
    def config_loader(self):
        if self._config_loader is None:
            from config_loader import config_loader
            self._config_loader = config_loader
        return self._config_loader

    # ── Condition-Harvest Correlation ──────────────────────────────

    def get_condition_harvest_correlation(self, variety: str) -> Dict[str, Any]:
        """
        Correlate average sensor conditions during growth with yield/quality outcomes.

        Queries crop_condition_snapshots and harvests tables to find
        which conditions produced the best results.

        Args:
            variety: Variety name (e.g., 'rosso_premium')

        Returns:
            Dict with correlation data, best/worst batches, insights
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Get harvested crops with condition snapshots
                cursor.execute('''
                    SELECT
                        c.id as crop_id,
                        c.plant_date,
                        h.weight_kg,
                        h.quality_grade,
                        h.market_value,
                        AVG(cs.avg_temperature) as avg_temp,
                        AVG(cs.avg_humidity) as avg_humidity,
                        AVG(cs.avg_ph) as avg_ph,
                        AVG(cs.avg_ec) as avg_ec,
                        AVG(cs.avg_vpd) as avg_vpd,
                        AVG(cs.avg_dli) as avg_dli,
                        AVG(cs.time_in_optimal_pct) as avg_optimal_pct
                    FROM crops c
                    JOIN harvests h ON c.id = h.crop_id
                    LEFT JOIN crop_condition_snapshots cs ON c.id = cs.crop_id
                    WHERE c.variety = ?
                      AND c.status = 'harvested'
                    GROUP BY c.id
                    ORDER BY h.weight_kg DESC
                ''', (variety,))

                rows = cursor.fetchall()

                if not rows:
                    return {
                        'variety': variety,
                        'status': 'insufficient_data',
                        'message': 'No harvested crops with condition data found',
                        'batches_analyzed': 0,
                    }

                batches = [dict(row) for row in rows]

                # Best and worst batches
                best = batches[0] if batches else None
                worst = batches[-1] if len(batches) > 1 else None

                # Average conditions across all batches
                avg_conditions = {}
                for field in ['avg_temp', 'avg_humidity', 'avg_ph', 'avg_ec', 'avg_vpd', 'avg_dli', 'avg_optimal_pct']:
                    values = [b[field] for b in batches if b.get(field) is not None]
                    if values:
                        avg_conditions[field] = round(sum(values) / len(values), 2)

                # Yield statistics
                yields = [b['weight_kg'] for b in batches if b.get('weight_kg') is not None]
                yield_stats = {}
                if yields:
                    yield_stats = {
                        'avg_yield_kg': round(sum(yields) / len(yields), 2),
                        'best_yield_kg': round(max(yields), 2),
                        'worst_yield_kg': round(min(yields), 2),
                    }

                # Insights
                insights = _generate_correlation_insights(batches, variety)

                return {
                    'variety': variety,
                    'batches_analyzed': len(batches),
                    'yield_statistics': yield_stats,
                    'average_conditions': avg_conditions,
                    'best_batch': _format_batch(best) if best else None,
                    'worst_batch': _format_batch(worst) if worst else None,
                    'insights': insights,
                }

        except Exception as e:
            logger.error(f"Correlation analysis error: {e}")
            return {'variety': variety, 'error': str(e)}

    # ── Growth Optimization Recommendations ────────────────────────

    def get_growth_optimization_recommendations(self, crop_id: int) -> Dict[str, Any]:
        """
        Compare current conditions to best historical outcomes.
        Suggest adjustments to optimize growth.

        Args:
            crop_id: Active crop ID

        Returns:
            Dict with current vs optimal conditions, recommendations
        """
        try:
            crop = self.db.get_crop(crop_id)
            if not crop:
                return {'error': f'Crop {crop_id} not found'}

            variety = crop['variety']
            current_stage = None
            for stage in crop.get('stages', []):
                if stage.get('ended_at') is None:
                    current_stage = stage['stage']
                    break

            # Load variety config for optimal ranges
            config = self.config_loader.load_variety(variety)
            optimal_ranges = config.get('optimal_ranges', {})
            growth_stages = config.get('growth_stages', {})
            stage_config = growth_stages.get(current_stage, {})

            # Get latest condition snapshot
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM crop_condition_snapshots
                    WHERE crop_id = ?
                    ORDER BY snapshot_date DESC
                    LIMIT 1
                ''', (crop_id,))
                latest = cursor.fetchone()

            recommendations = []
            current_conditions = {}

            if latest:
                latest = dict(latest)
                current_conditions = {
                    'temperature': latest.get('avg_temperature'),
                    'humidity': latest.get('avg_humidity'),
                    'ph': latest.get('avg_ph'),
                    'ec': latest.get('avg_ec'),
                    'vpd': latest.get('avg_vpd'),
                    'dli': latest.get('avg_dli'),
                    'time_in_optimal': latest.get('time_in_optimal_pct'),
                }

                # Compare each parameter against optimal ranges
                for param in ['temperature', 'humidity', 'ph', 'ec']:
                    ranges = optimal_ranges.get(param, {})
                    current = current_conditions.get(param)
                    if current is None:
                        continue

                    opt_min = ranges.get('optimal_min')
                    opt_max = ranges.get('optimal_max')
                    if opt_min is None or opt_max is None:
                        continue

                    if current < opt_min:
                        recommendations.append({
                            'parameter': param,
                            'current': round(current, 2),
                            'target_range': f'{opt_min}-{opt_max}',
                            'action': f'Increase {param} — currently below optimal',
                            'priority': 'high' if current < ranges.get('critical_min', opt_min) else 'medium',
                        })
                    elif current > opt_max:
                        recommendations.append({
                            'parameter': param,
                            'current': round(current, 2),
                            'target_range': f'{opt_min}-{opt_max}',
                            'action': f'Decrease {param} — currently above optimal',
                            'priority': 'high' if current > ranges.get('critical_max', opt_max) else 'medium',
                        })

                # Stage-specific EC recommendation
                ec_range_str = stage_config.get('ec_range', '')
                if ec_range_str and '-' in ec_range_str and current_conditions.get('ec') is not None:
                    parts = ec_range_str.split('-')
                    stage_ec_min, stage_ec_max = float(parts[0]), float(parts[1])
                    current_ec = current_conditions['ec']
                    if current_ec < stage_ec_min or current_ec > stage_ec_max:
                        recommendations.append({
                            'parameter': 'ec_stage_specific',
                            'current': round(current_ec, 2),
                            'target_range': ec_range_str,
                            'action': f'Adjust EC for {current_stage} stage (target: {ec_range_str} mS/cm)',
                            'priority': 'medium',
                        })

            # Get historical best for comparison
            best_correlation = self.get_condition_harvest_correlation(variety)
            best_conditions = best_correlation.get('average_conditions', {})

            return {
                'crop_id': crop_id,
                'variety': variety,
                'current_stage': current_stage,
                'current_conditions': current_conditions,
                'optimal_ranges': {k: {'min': v.get('optimal_min'), 'max': v.get('optimal_max')}
                                   for k, v in optimal_ranges.items()},
                'recommendations': recommendations,
                'historical_best_conditions': best_conditions,
                'recommendation_count': len(recommendations),
            }

        except Exception as e:
            logger.error(f"Optimization recommendations error: {e}")
            return {'crop_id': crop_id, 'error': str(e)}

    # ── Yield Prediction ───────────────────────────────────────────

    def predict_yield(self, crop_id: int) -> Dict[str, Any]:
        """
        Simple yield prediction based on historical data + current conditions.

        Uses average yield from same variety, adjusted by time-in-optimal percentage.

        Args:
            crop_id: Active crop ID

        Returns:
            Dict with predicted yield, confidence, factors
        """
        try:
            crop = self.db.get_crop(crop_id)
            if not crop:
                return {'error': f'Crop {crop_id} not found'}

            variety = crop['variety']

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Historical yields for this variety
                cursor.execute('''
                    SELECT h.weight_kg, h.quality_grade
                    FROM harvests h
                    JOIN crops c ON h.crop_id = c.id
                    WHERE c.variety = ?
                    ORDER BY h.harvest_date DESC
                    LIMIT 20
                ''', (variety,))

                historical = cursor.fetchall()

                if not historical:
                    return {
                        'crop_id': crop_id,
                        'variety': variety,
                        'status': 'insufficient_data',
                        'message': 'No historical harvests for yield prediction',
                    }

                yields = [row[0] for row in historical if row[0] is not None]
                avg_yield = sum(yields) / len(yields) if yields else 0

                # Get current crop condition snapshots
                cursor.execute('''
                    SELECT AVG(time_in_optimal_pct) as avg_optimal
                    FROM crop_condition_snapshots
                    WHERE crop_id = ?
                ''', (crop_id,))

                condition_row = cursor.fetchone()
                avg_optimal_pct = condition_row[0] if condition_row and condition_row[0] else None

            # Adjust prediction based on time in optimal conditions
            adjustment_factor = 1.0
            if avg_optimal_pct is not None:
                # More time in optimal = better yield
                # 100% optimal -> 1.1x, 50% optimal -> 0.9x, etc.
                adjustment_factor = 0.7 + (avg_optimal_pct / 100.0) * 0.4

            predicted_yield = round(avg_yield * adjustment_factor, 2)

            # Confidence based on sample size
            if len(yields) >= 10:
                confidence = 'high'
            elif len(yields) >= 5:
                confidence = 'medium'
            else:
                confidence = 'low'

            # Quality prediction
            grades = [row[1] for row in historical if row[1]]
            most_common_grade = max(set(grades), key=grades.count) if grades else 'standard'

            return {
                'crop_id': crop_id,
                'variety': variety,
                'predicted_yield_kg': predicted_yield,
                'historical_avg_yield_kg': round(avg_yield, 2),
                'adjustment_factor': round(adjustment_factor, 2),
                'optimal_time_percent': round(avg_optimal_pct, 1) if avg_optimal_pct else None,
                'predicted_quality': most_common_grade,
                'confidence': confidence,
                'historical_batches': len(yields),
                'factors': {
                    'historical_average': round(avg_yield, 2),
                    'condition_adjustment': round(adjustment_factor, 2),
                    'condition_data_available': avg_optimal_pct is not None,
                },
            }

        except Exception as e:
            logger.error(f"Yield prediction error: {e}")
            return {'crop_id': crop_id, 'error': str(e)}

    # ── Crop Health Score ──────────────────────────────────────────

    def get_crop_health_score(self, crop_id: int) -> Dict[str, Any]:
        """
        0-100 health score based on time in optimal ranges for current growth stage.

        Scores: temperature (25pts), humidity (15pts), pH (25pts), EC (25pts), VPD (10pts)

        Args:
            crop_id: Crop ID

        Returns:
            Dict with overall score, per-parameter scores, status
        """
        try:
            crop = self.db.get_crop(crop_id)
            if not crop:
                return {'error': f'Crop {crop_id} not found'}

            variety = crop['variety']

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Get recent condition snapshots (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
                cursor.execute('''
                    SELECT * FROM crop_condition_snapshots
                    WHERE crop_id = ? AND snapshot_date >= ?
                    ORDER BY snapshot_date DESC
                ''', (crop_id, week_ago))

                snapshots = [dict(row) for row in cursor.fetchall()]

            if not snapshots:
                return {
                    'crop_id': crop_id,
                    'variety': variety,
                    'status': 'no_data',
                    'message': 'No condition snapshots available for health scoring',
                    'score': None,
                }

            # Load optimal ranges
            config = self.config_loader.load_variety(variety)
            optimal_ranges = config.get('optimal_ranges', {})

            # Calculate per-parameter scores
            param_scores = {}
            weights = {'temperature': 25, 'humidity': 15, 'ph': 25, 'ec': 25, 'vpd': 10}
            field_map = {
                'temperature': 'avg_temperature',
                'humidity': 'avg_humidity',
                'ph': 'avg_ph',
                'ec': 'avg_ec',
                'vpd': 'avg_vpd',
            }

            total_score = 0
            total_weight = 0

            for param, weight in weights.items():
                db_field = field_map.get(param)
                if not db_field:
                    continue

                values = [s[db_field] for s in snapshots if s.get(db_field) is not None]
                if not values:
                    continue

                avg_val = sum(values) / len(values)
                ranges = optimal_ranges.get(param, {})
                opt_min = ranges.get('optimal_min')
                opt_max = ranges.get('optimal_max')
                crit_min = ranges.get('critical_min', opt_min)
                crit_max = ranges.get('critical_max', opt_max)

                if opt_min is not None and opt_max is not None:
                    pct = _range_pct(avg_val, opt_min, opt_max, crit_min, crit_max)
                    param_scores[param] = {
                        'score': round(pct * weight, 1),
                        'max_score': weight,
                        'average_value': round(avg_val, 2),
                        'optimal_range': f'{opt_min}-{opt_max}',
                        'status': 'optimal' if opt_min <= avg_val <= opt_max
                                  else 'warning' if crit_min <= avg_val <= crit_max
                                  else 'critical',
                    }
                    total_score += pct * weight
                    total_weight += weight

            overall = round(total_score, 1) if total_weight > 0 else 0

            if overall >= 80:
                status = 'healthy'
            elif overall >= 60:
                status = 'warning'
            else:
                status = 'critical'

            # Time in optimal from snapshots
            optimal_pcts = [s['time_in_optimal_pct'] for s in snapshots
                           if s.get('time_in_optimal_pct') is not None]
            avg_optimal = round(sum(optimal_pcts) / len(optimal_pcts), 1) if optimal_pcts else None

            return {
                'crop_id': crop_id,
                'variety': variety,
                'score': overall,
                'status': status,
                'parameter_scores': param_scores,
                'time_in_optimal_pct': avg_optimal,
                'snapshots_analyzed': len(snapshots),
                'period': f'Last 7 days ({len(snapshots)} snapshots)',
            }

        except Exception as e:
            logger.error(f"Health score error: {e}")
            return {'crop_id': crop_id, 'error': str(e)}

    # ── Stage Performance Report ───────────────────────────────────

    def get_stage_performance_report(self, crop_id: int) -> Dict[str, Any]:
        """
        Per-stage condition tracking for post-harvest analysis.

        Args:
            crop_id: Crop ID

        Returns:
            Dict with per-stage averages, duration, and condition quality
        """
        try:
            crop = self.db.get_crop(crop_id)
            if not crop:
                return {'error': f'Crop {crop_id} not found'}

            variety = crop['variety']
            stages = crop.get('stages', [])

            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                stage_reports = []
                for stage in stages:
                    stage_name = stage['stage']
                    started = stage['started_at']
                    ended = stage.get('ended_at')

                    # Get condition snapshots for this stage period
                    if ended:
                        cursor.execute('''
                            SELECT * FROM crop_condition_snapshots
                            WHERE crop_id = ? AND snapshot_date >= ? AND snapshot_date <= ?
                            ORDER BY snapshot_date
                        ''', (crop_id, started[:10], ended[:10]))
                    else:
                        cursor.execute('''
                            SELECT * FROM crop_condition_snapshots
                            WHERE crop_id = ? AND snapshot_date >= ?
                            ORDER BY snapshot_date
                        ''', (crop_id, started[:10]))

                    snapshots = [dict(row) for row in cursor.fetchall()]

                    # Duration
                    start_dt = datetime.fromisoformat(started)
                    end_dt = datetime.fromisoformat(ended) if ended else datetime.now()
                    duration_days = (end_dt - start_dt).days

                    # Average conditions during stage
                    avg_conditions = {}
                    for field in ['avg_temperature', 'avg_humidity', 'avg_ph', 'avg_ec', 'avg_vpd', 'avg_dli']:
                        values = [s[field] for s in snapshots if s.get(field) is not None]
                        if values:
                            avg_conditions[field.replace('avg_', '')] = round(sum(values) / len(values), 2)

                    optimal_pcts = [s['time_in_optimal_pct'] for s in snapshots
                                   if s.get('time_in_optimal_pct') is not None]
                    avg_optimal = round(sum(optimal_pcts) / len(optimal_pcts), 1) if optimal_pcts else None

                    stage_reports.append({
                        'stage': stage_name,
                        'started_at': started,
                        'ended_at': ended,
                        'duration_days': duration_days,
                        'snapshots_count': len(snapshots),
                        'average_conditions': avg_conditions,
                        'time_in_optimal_pct': avg_optimal,
                        'status': 'completed' if ended else 'active',
                    })

            # Get harvest data if available
            harvest_data = None
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM harvests WHERE crop_id = ? LIMIT 1
                ''', (crop_id,))
                harvest_row = cursor.fetchone()
                if harvest_row:
                    harvest_data = dict(harvest_row)

            return {
                'crop_id': crop_id,
                'variety': variety,
                'plant_date': crop.get('plant_date'),
                'status': crop.get('status'),
                'stages': stage_reports,
                'total_stages': len(stage_reports),
                'harvest': harvest_data,
            }

        except Exception as e:
            logger.error(f"Stage performance report error: {e}")
            return {'crop_id': crop_id, 'error': str(e)}


# ── Helper functions ───────────────────────────────────────────────

def _format_batch(batch: Dict) -> Dict:
    """Format a batch dict for API response."""
    return {
        'crop_id': batch.get('crop_id'),
        'plant_date': batch.get('plant_date'),
        'weight_kg': batch.get('weight_kg'),
        'quality_grade': batch.get('quality_grade'),
        'conditions': {
            'avg_temperature': batch.get('avg_temp'),
            'avg_humidity': batch.get('avg_humidity'),
            'avg_ph': batch.get('avg_ph'),
            'avg_ec': batch.get('avg_ec'),
            'avg_vpd': batch.get('avg_vpd'),
            'avg_dli': batch.get('avg_dli'),
            'time_in_optimal_pct': batch.get('avg_optimal_pct'),
        },
    }


def _generate_correlation_insights(batches: List[Dict], variety: str) -> List[str]:
    """Generate human-readable insights from batch correlation data."""
    insights = []

    if len(batches) < 2:
        insights.append('Need more harvested batches for meaningful correlation analysis')
        return insights

    # Compare best vs worst batch
    best = batches[0]
    worst = batches[-1]

    if best.get('avg_temp') and worst.get('avg_temp'):
        temp_diff = best['avg_temp'] - worst['avg_temp']
        if abs(temp_diff) > 1:
            direction = 'warmer' if temp_diff > 0 else 'cooler'
            insights.append(f'Best batch grew {abs(temp_diff):.1f}°C {direction} than worst batch')

    if best.get('avg_optimal_pct') and worst.get('avg_optimal_pct'):
        opt_diff = best['avg_optimal_pct'] - worst['avg_optimal_pct']
        if opt_diff > 5:
            insights.append(f'Best batch spent {opt_diff:.0f}% more time in optimal conditions')

    if best.get('avg_vpd') and worst.get('avg_vpd'):
        if 0.8 <= best['avg_vpd'] <= 1.2 and not (0.8 <= worst['avg_vpd'] <= 1.2):
            insights.append('Best batch maintained optimal VPD range (0.8-1.2 kPa)')

    return insights


def _range_pct(value: float, opt_min: float, opt_max: float,
               crit_min: float, crit_max: float) -> float:
    """Calculate 0-1 score for value within optimal/critical ranges."""
    if opt_min <= value <= opt_max:
        return 1.0
    elif crit_min <= value < opt_min:
        return max(0, (value - crit_min) / (opt_min - crit_min)) * 0.7
    elif opt_max < value <= crit_max:
        return max(0, (crit_max - value) / (crit_max - opt_max)) * 0.7
    else:
        return 0.0


# Global instance
crop_intelligence = CropIntelligence()
