"""
Business Digest Service.

Generates periodic business digest reports and sends them
via a dedicated ntfy channel (private business topic).

Tones:
- aggressive: Focuses on growth targets, missed opportunities, urgency
- medium: Balanced view of metrics, progress, and next steps
- optimist: Highlights wins, positive trends, and momentum

Author: AgriTech Hydroponics
License: MIT
"""

import os
import logging
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('business-digest')

NTFY_URL = os.getenv('NTFY_URL', 'https://ntfy.sh')
NTFY_BUSINESS_TOPIC = os.getenv('NTFY_BUSINESS_TOPIC', '')
NTFY_TOKEN = os.getenv('NTFY_TOKEN', '')


class BusinessDigestService:
    """Generate and send business digest reports."""

    def __init__(self):
        self._dashboard = None

    @property
    def dashboard(self):
        if self._dashboard is None:
            from business.business_dashboard import dashboard
            self._dashboard = dashboard
        return self._dashboard

    def generate_digest(self, tone: str = 'medium') -> Dict[str, Any]:
        """
        Generate a business digest report.

        Args:
            tone: Framing style — 'aggressive', 'medium', or 'optimist'

        Returns:
            Dict with digest data and formatted message
        """
        tone = tone.lower()
        if tone not in ('aggressive', 'medium', 'optimist'):
            tone = 'medium'

        try:
            overview = self.dashboard.get_business_overview()
            revenue = self.dashboard.get_revenue_metrics()
            crops = self.dashboard.get_crop_status()
            opportunities = self.dashboard.get_revenue_opportunities()
        except Exception as e:
            logger.error(f"Digest data collection error: {e}")
            return {'error': str(e)}

        # Format the digest message
        message = self._format_digest(tone, overview, revenue, crops, opportunities)

        return {
            'report_type': 'business_digest',
            'tone': tone,
            'generated_at': datetime.now().isoformat(),
            'overview': overview,
            'revenue': revenue,
            'crops': crops,
            'opportunities_count': len(opportunities),
            'formatted_message': message,
        }

    def send_digest(self, tone: str = 'medium') -> Dict[str, Any]:
        """
        Generate and send digest via the private business ntfy channel.

        Args:
            tone: Framing style — 'aggressive', 'medium', or 'optimist'

        Returns:
            Dict with digest data and send result
        """
        digest = self.generate_digest(tone)
        if 'error' in digest:
            return digest

        sent = self._send_ntfy(digest['formatted_message'], tone)
        digest['ntfy_sent'] = sent
        digest['ntfy_topic'] = NTFY_BUSINESS_TOPIC or '(not configured)'

        return digest

    def _send_ntfy(self, message: str, tone: str) -> bool:
        """Send digest to the private business ntfy topic."""
        if not NTFY_BUSINESS_TOPIC:
            logger.warning("NTFY_BUSINESS_TOPIC not configured — digest not sent")
            return False

        title_map = {
            'aggressive': 'Business Digest — Action Required',
            'medium': 'Business Digest — Weekly Overview',
            'optimist': 'Business Digest — Wins & Progress',
        }
        priority_map = {
            'aggressive': '4',
            'medium': '3',
            'optimist': '2',
        }

        endpoint = f"{NTFY_URL.rstrip('/')}/{NTFY_BUSINESS_TOPIC}"
        headers = {
            'Title': title_map.get(tone, title_map['medium']),
            'Priority': priority_map.get(tone, '3'),
            'Tags': 'chart_with_upwards_trend,briefcase',
            'Markdown': 'yes',
        }
        if NTFY_TOKEN:
            headers['Authorization'] = f'Bearer {NTFY_TOKEN}'

        try:
            req = urllib.request.Request(
                endpoint,
                data=message.encode('utf-8'),
                headers=headers,
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info(f"Business digest sent to ntfy topic '{NTFY_BUSINESS_TOPIC}' (tone={tone})")
            return True
        except Exception as e:
            logger.error(f"Failed to send business digest via ntfy: {e}")
            return False

    def _format_digest(self, tone: str, overview: Dict, revenue: Dict,
                       crops: Dict, opportunities: list) -> str:
        """Format digest message based on tone."""
        lines = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        mrr = overview.get('mrr', 0)
        total_rev = overview.get('total_revenue_month', 0)
        growth = overview.get('growth_rate_percent', 0)
        active_clients = overview.get('active_clients', 0)
        active_crops = overview.get('active_crops', 0)
        churn = revenue.get('churn_rate_percent', 0)
        projected = revenue.get('projected_annual', 0)

        # Header
        if tone == 'aggressive':
            lines.append(f'**BUSINESS DIGEST** — {now}')
            lines.append('')
            if growth < 10:
                lines.append(f'Growth at **{growth}%** — below target. Action needed.')
            else:
                lines.append(f'Growth at **{growth}%** — keep pushing.')
        elif tone == 'optimist':
            lines.append(f'**Business Digest** — {now}')
            lines.append('')
            if active_clients > 0:
                lines.append(f'Serving **{active_clients} active clients** and growing!')
            if growth > 0:
                lines.append(f'Revenue up **{growth}%** this month.')
        else:
            lines.append(f'**Business Digest** — {now}')
            lines.append('')
            lines.append(f'Clients: {active_clients} | MRR: {mrr} | Growth: {growth}%')

        # Revenue section
        lines.append('')
        lines.append('**Revenue**')
        lines.append(f'- MRR: {mrr}')
        lines.append(f'- Total this month: {total_rev}')
        lines.append(f'- Projected annual: {projected}')
        if tone == 'aggressive' and churn > 0:
            lines.append(f'- Churn: **{churn}%** — address immediately')
        elif churn > 0:
            lines.append(f'- Churn: {churn}%')

        # Tier breakdown
        tiers = revenue.get('by_tier', {})
        if tiers:
            lines.append('')
            lines.append('**Tier Breakdown**')
            for tier_name, tier_data in tiers.items():
                count = tier_data.get('client_count', 0)
                tier_mrr = tier_data.get('mrr', 0)
                lines.append(f'- {tier_name}: {count} clients, {tier_mrr}/mo')

        # Crops section
        lines.append('')
        lines.append('**Crops**')
        lines.append(f'- Active: {active_crops}')
        harvests = crops.get('harvests_this_month', 0)
        avg_yield = crops.get('avg_yield_kg', 0)
        if harvests > 0:
            lines.append(f'- Harvests this month: {harvests} (avg {avg_yield} kg)')
        upcoming = crops.get('upcoming_harvests', [])
        if upcoming:
            lines.append(f'- Upcoming harvests: {len(upcoming)} due this week')

        by_stage = crops.get('by_stage', {})
        if by_stage:
            stage_summary = ', '.join(f'{s}: {c}' for s, c in by_stage.items())
            lines.append(f'- Stages: {stage_summary}')

        # Opportunities
        if opportunities:
            lines.append('')
            if tone == 'aggressive':
                lines.append(f'**{len(opportunities)} Opportunities — Act Now**')
            elif tone == 'optimist':
                lines.append(f'**{len(opportunities)} Growth Opportunities**')
            else:
                lines.append(f'**Opportunities ({len(opportunities)})**')

            total_value = sum(o.get('estimated_value', 0) for o in opportunities)
            lines.append(f'- Total potential value: {total_value}')

            for opp in opportunities[:3]:
                desc = opp.get('description', '')
                val = opp.get('estimated_value', 0)
                lines.append(f'- {desc} (+{val})')

        # Closing
        lines.append('')
        if tone == 'aggressive':
            lines.append('---')
            lines.append('No excuses. Execute on the top opportunity today.')
        elif tone == 'optimist':
            lines.append('---')
            lines.append('Great momentum — keep it up!')
        else:
            lines.append('---')
            lines.append('Review dashboard for full details.')

        return '\n'.join(lines)


# Global instance
business_digest = BusinessDigestService()
