"""
Tier-Aware Notification Router

Routes notifications through appropriate channels based on:
- Customer subscription tier
- Notification severity
- Feature availability
- Business rules (upselling, engagement)

Author: AgriTech Hydroponics - SaaS Division
License: Proprietary
"""

import logging
from typing import List, Dict, Any, Optional
from business_model import business_db, SUBSCRIPTION_TIERS
from notification_service import notifier

logger = logging.getLogger('tier-notification-router')


class TierNotificationRouter:
    """
    Routes notifications based on customer tier and business rules.

    Features:
    - Tier-based channel filtering
    - Upsell opportunity detection
    - Calibration reminders per tier
    - Engagement notifications
    """

    def __init__(self):
        self.business_db = business_db

    def send_notification(self, customer_id: int, notification_type: str,
                         severity: str, message: str, sensor_data: Dict[str, Any] = None,
                         recommended_action: str = None) -> Dict[str, Any]:
        """
        Send notification through tier-appropriate channels.

        Args:
            customer_id: Customer ID
            notification_type: Type of notification (alert, calibration, upsell)
            severity: Severity level
            message: Message content
            sensor_data: Current sensor readings
            recommended_action: Suggested action

        Returns:
            Notification result with tier info and channels used
        """
        # Get customer tier config
        tier_config = self.business_db.get_customer_tier_config(customer_id)
        tier_name = tier_config['name']

        # Check if customer can receive this severity level
        allowed_severities = tier_config['features']['alert_types']

        if severity not in allowed_severities:
            # Tier doesn't allow this severity - send upsell opportunity
            logger.info(f"Customer {customer_id} ({tier_name}) can't receive {severity} alerts")

            self._create_tier_upgrade_opportunity(
                customer_id,
                tier_name,
                f"Upgrade to receive {severity} alerts and prevent issues"
            )

            # Log as restricted
            self.business_db.log_notification(
                customer_id,
                notification_type,
                'restricted',
                message,
                delivered=False,
                tier_restricted=True
            )

            return {
                'status': 'tier_restricted',
                'customer_tier': tier_name,
                'required_tier': self._get_tier_for_severity(severity),
                'message': f"{tier_name} tier doesn't include {severity} alerts",
                'upsell_created': True
            }

        # Get allowed channels for this tier
        allowed_channels = tier_config['features']['notification_channels']

        # Send through notifier (it will use available channels)
        results = notifier.notify(
            rule_id=f"customer_{customer_id}_{notification_type}",
            severity=severity,
            message=message,
            sensor_data=sensor_data,
            recommended_action=recommended_action
        )

        # Log notifications sent
        for result in results:
            if result['channel'] in allowed_channels:
                self.business_db.log_notification(
                    customer_id,
                    notification_type,
                    result['channel'],
                    message,
                    delivered=result['sent']
                )

        return {
            'status': 'sent',
            'customer_tier': tier_name,
            'channels_used': [r['channel'] for r in results if r['sent'] and r['channel'] in allowed_channels],
            'channels_available': allowed_channels,
            'results': results
        }

    def send_calibration_reminder(self, customer_id: int, sensor_type: str,
                                  last_calibration_days_ago: int):
        """
        Send calibration reminder based on tier frequency.

        Bronze: Quarterly (90 days) - Email only
        Silver: Monthly (30 days) - Email + SMS
        Gold: Bi-weekly (14 days) - Email + SMS + WhatsApp
        Platinum: Weekly (7 days) - All channels + priority
        """
        tier_config = self.business_db.get_customer_tier_config(customer_id)
        tier_name = tier_config['name']
        calibration_frequency = tier_config['features']['calibration_frequency_days']

        if last_calibration_days_ago < calibration_frequency:
            # Not due yet for this tier
            return {'status': 'not_due', 'tier': tier_name, 'days_remaining': calibration_frequency - last_calibration_days_ago}

        # Determine severity based on how overdue
        if last_calibration_days_ago > calibration_frequency * 1.5:
            severity = 'critical'
            message = f"🚨 OVERDUE: {sensor_type} calibration required! Last done {last_calibration_days_ago} days ago"
        elif last_calibration_days_ago > calibration_frequency * 1.2:
            severity = 'warning'
            message = f"⚠️ {sensor_type} calibration due soon (last: {last_calibration_days_ago} days ago)"
        else:
            severity = 'preventive'
            message = f"📐 {sensor_type} calibration reminder - optimal performance maintenance"

        # Add tier-specific recommendations
        if tier_name == 'platinum':
            recommended_action = "Your dedicated account manager will contact you to schedule calibration. Or call priority support: +351-XXX-XXXX"
        elif tier_name == 'gold':
            recommended_action = "Call 24/7 support for remote guidance: +351-XXX-XXXX. We can walk you through the calibration."
        elif tier_name == 'silver':
            recommended_action = "Schedule calibration this week. Call support during business hours if you need assistance."
        else:  # bronze
            recommended_action = "Calibrate your sensors following the manual. Email support@agritech.com if you need help."

        return self.send_notification(
            customer_id,
            'calibration_reminder',
            severity,
            message,
            recommended_action=recommended_action
        )

    def send_sensor_recommendation(self, customer_id: int, sensor_type: str,
                                   reason: str, expected_improvement: str):
        """
        Send sensor recommendation (upsell) if tier allows.

        Only Silver+ customers get proactive sensor recommendations.
        """
        tier_config = self.business_db.get_customer_tier_config(customer_id)

        if not tier_config['features']['sensor_recommendations']:
            # Bronze tier doesn't get recommendations
            logger.info(f"Customer {customer_id} tier doesn't include sensor recommendations")
            return {'status': 'tier_restricted', 'tier': tier_config['name']}

        # Create recommendation in database
        rec_id = self.business_db.recommend_sensor(
            customer_id,
            sensor_type,
            reason,
            expected_improvement
        )

        # Send notification
        message = f"💡 Sensor Upgrade Opportunity: Add {sensor_type} sensor"
        recommended_action = f"{reason}. Expected improvement: {expected_improvement}. Reply to this message or contact your account manager."

        result = self.send_notification(
            customer_id,
            'sensor_recommendation',
            'info',
            message,
            recommended_action=recommended_action
        )

        result['recommendation_id'] = rec_id
        return result

    def send_tier_upgrade_suggestion(self, customer_id: int, current_tier: str,
                                    suggested_tier: str, reason: str):
        """Send tier upgrade suggestion (upsell)."""
        current_config = SUBSCRIPTION_TIERS[current_tier]
        suggested_config = SUBSCRIPTION_TIERS[suggested_tier]

        price_diff = suggested_config['price_monthly'] - current_config['price_monthly']

        message = f"🚀 Upgrade Opportunity: {suggested_config['name']} Tier"
        recommended_action = f"{reason}. For just €{price_diff} more per month, unlock:\n"

        # List new features
        current_features = set(current_config['features'].keys())
        new_features = set(suggested_config['features'].keys()) - current_features

        for feature in list(new_features)[:5]:  # Top 5 features
            recommended_action += f"\n  ✓ {feature.replace('_', ' ').title()}"

        recommended_action += f"\n\nContact us to upgrade: sales@agritech.com"

        return self.send_notification(
            customer_id,
            'tier_upgrade',
            'info',
            message,
            recommended_action=recommended_action
        )

    def _create_tier_upgrade_opportunity(self, customer_id: int, current_tier: str, reason: str):
        """Create tier upgrade opportunity when feature is restricted."""
        # Determine which tier would provide the needed feature
        tier_hierarchy = ['bronze', 'silver', 'gold', 'platinum']
        current_index = tier_hierarchy.index(current_tier)

        if current_index < len(tier_hierarchy) - 1:
            suggested_tier = tier_hierarchy[current_index + 1]

            # Send upgrade suggestion
            self.send_tier_upgrade_suggestion(
                customer_id,
                current_tier,
                suggested_tier,
                reason
            )

    def _get_tier_for_severity(self, severity: str) -> str:
        """Get minimum tier required for severity level."""
        severity_tier_map = {
            'critical': 'bronze',
            'warning': 'silver',
            'preventive': 'silver',
            'urgent': 'gold'
        }
        return severity_tier_map.get(severity, 'bronze')

    def send_engagement_notification(self, customer_id: int, engagement_type: str):
        """
        Send engagement notifications to keep customers active.

        Types:
        - weekly_summary: Weekly performance report
        - monthly_report: Monthly analytics
        - milestone: Achievement notifications
        - tips: Optimization tips
        """
        tier_config = self.business_db.get_customer_tier_config(customer_id)
        tier_name = tier_config['name']

        messages = {
            'weekly_summary': {
                'message': f"📊 Your Weekly Summary - {tier_name} Tier",
                'action': "Review your crops' performance, sensor data trends, and receive optimization tips."
            },
            'monthly_report': {
                'message': f"📈 Monthly Performance Report - {tier_name} Tier",
                'action': "See your harvest analytics, ROI calculations, and growth recommendations."
            },
            'milestone': {
                'message': "🎉 Milestone Achieved!",
                'action': "Congratulations on your successful harvest! See detailed analytics in your dashboard."
            },
            'tips': {
                'message': "💡 Pro Tip for Better Yields",
                'action': "Based on your current growth stage, here's how to optimize your conditions..."
            }
        }

        notification_info = messages.get(engagement_type, messages['tips'])

        return self.send_notification(
            customer_id,
            f'engagement_{engagement_type}',
            'info',
            notification_info['message'],
            recommended_action=notification_info['action']
        )


# Global instance
tier_router = TierNotificationRouter()
