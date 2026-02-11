"""
Multi-Channel Notification System for AgriTech Business
Supports redundant ntfy channels + business intelligence reporting
"""

import os
import logging
import urllib.request
from typing import Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger('multi-channel-notifier')


class AlertLevel(Enum):
    """3-tier alert system for client communications"""
    OPTIMIST = "optimist"      # 🟢 Everything improving, FYI only
    MEDIUM = "medium"          # 🟡 Attention needed soon
    AGGRESSIVE = "aggressive"  # 🔴 Urgent action required


class ChannelType(Enum):
    """Different notification channels for different audiences"""
    CLIENT_PUBLIC = "client_public"      # Public client-facing alerts
    BUSINESS_PRIVATE = "business_private"  # Internal business intelligence
    EMERGENCY = "emergency"              # Critical system failures


class MultiChannelNtfy:
    """Enhanced ntfy client supporting multiple topic channels"""

    def __init__(self):
        self.base_url = os.getenv('NTFY_URL', 'https://ntfy.sh')
        self.token = os.getenv('NTFY_TOKEN', '')

        # Multiple channel configuration
        self.channels = {
            ChannelType.CLIENT_PUBLIC: os.getenv('NTFY_TOPIC_CLIENT', ''),
            ChannelType.BUSINESS_PRIVATE: os.getenv('NTFY_TOPIC_BUSINESS', ''),
            ChannelType.EMERGENCY: os.getenv('NTFY_TOPIC_EMERGENCY', ''),
        }

    def _get_alert_style(self, level: AlertLevel) -> Dict[str, str]:
        """Map alert levels to ntfy priority and tags"""
        styles = {
            AlertLevel.OPTIMIST: {
                "priority": "3",
                "tags": "green_circle,chart_with_upwards_trend",
                "icon": "🟢",
                "prefix": "✅ BOA NOTÍCIA"
            },
            AlertLevel.MEDIUM: {
                "priority": "4",
                "tags": "yellow_circle,warning",
                "icon": "🟡",
                "prefix": "⚠️ ATENÇÃO"
            },
            AlertLevel.AGGRESSIVE: {
                "priority": "5",
                "tags": "red_circle,rotating_light,sos",
                "icon": "🔴",
                "prefix": "🚨 URGENTE"
            },
        }
        return styles.get(level, styles[AlertLevel.MEDIUM])

    def send(self, channel: ChannelType, level: AlertLevel, title: str,
             body: str, click_url: str = None) -> bool:
        """Send notification to specific channel with alert level styling"""

        topic = self.channels.get(channel)
        if not topic:
            logger.warning(f"Channel {channel.value} not configured (no NTFY_TOPIC)")
            return False

        style = self._get_alert_style(level)
        endpoint = f"{self.base_url.rstrip('/')}/{topic}"

        # Add alert level prefix to title
        styled_title = f"{style['icon']} {style['prefix']}: {title}"

        headers = {
            "Title": styled_title,
            "Priority": style["priority"],
            "Tags": style["tags"],
            "Markdown": "yes",
        }

        if click_url:
            headers["Click"] = click_url

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            req = urllib.request.Request(endpoint, data=body.encode(), headers=headers)
            urllib.request.urlopen(req, timeout=10)
            logger.info(f"Sent {level.value} alert to {channel.value}: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to {channel.value}: {e}")
            return False

    def send_all_channels(self, level: AlertLevel, title: str, body: str,
                          exclude: List[ChannelType] = None) -> Dict[str, bool]:
        """Send to all configured channels (with optional exclusions)"""
        exclude = exclude or []
        results = {}

        for channel_type, topic in self.channels.items():
            if channel_type in exclude or not topic:
                continue
            results[channel_type.value] = self.send(channel_type, level, title, body)

        return results


class BusinessIntelligenceReporter:
    """Generate business intelligence reports for private channel"""

    def __init__(self, notifier: MultiChannelNtfy):
        self.notifier = notifier

    def send_daily_digest(self, metrics: Dict[str, Any]) -> bool:
        """Send daily business digest to private channel"""

        # Determine overall health level
        alert_count = metrics.get('alert_count_24h', 0)
        if alert_count == 0:
            level = AlertLevel.OPTIMIST
            summary = "Sistema operando perfeitamente"
        elif alert_count < 5:
            level = AlertLevel.MEDIUM
            summary = "Alguns alertas detectados, tudo sob controle"
        else:
            level = AlertLevel.AGGRESSIVE
            summary = f"ATENÇÃO: {alert_count} alertas nas últimas 24h"

        # Build report body
        body_lines = [
            "# 📊 Relatório Diário AgriTech",
            f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"## {summary}",
            "",
            "### 🌱 Cultivos Ativos",
            f"- Total: {metrics.get('active_crops', 0)}",
            f"- Fase Seedling: {metrics.get('seedling_count', 0)}",
            f"- Fase Vegetativa: {metrics.get('vegetative_count', 0)}",
            f"- Fase Maturidade: {metrics.get('maturity_count', 0)}",
            "",
            "### 📈 Alertas (24h)",
            f"- **Total:** {metrics.get('alert_count_24h', 0)}",
            f"- Críticos: {metrics.get('critical_alerts', 0)}",
            f"- Avisos: {metrics.get('warning_alerts', 0)}",
            f"- Preventivos: {metrics.get('preventive_alerts', 0)}",
            "",
            "### 🔧 Clientes Necessitando Serviço",
        ]

        # Client health scores
        clients_needing_service = metrics.get('clients_needing_service', [])
        if not clients_needing_service:
            body_lines.append("- ✅ Nenhum cliente necessita calibração imediata")
        else:
            for client in clients_needing_service:
                body_lines.append(
                    f"- ⚠️ **{client['name']}** (Score: {client['health_score']}/100) "
                    f"- Último serviço: {client['days_since_service']} dias atrás"
                )

        body_lines.extend([
            "",
            "### 💰 Receita Potencial",
            f"- Calibrações agendadas: {metrics.get('scheduled_calibrations', 0)}",
            f"- Valor estimado: €{metrics.get('revenue_estimate', 0):.2f}",
            "",
            "### ⚡ Sistema",
            f"- Uptime: {metrics.get('uptime_percent', 100):.1f}%",
            f"- Sensores online: {metrics.get('sensors_online', 0)}/{metrics.get('total_sensors', 0)}",
            f"- Uso de disco: {metrics.get('disk_usage_percent', 0)}%",
        ])

        body = "\n".join(body_lines)

        return self.notifier.send(
            channel=ChannelType.BUSINESS_PRIVATE,
            level=level,
            title="Relatório Diário do Sistema",
            body=body,
        )

    def send_client_health_alert(self, client_name: str, health_score: int,
                                   issues: List[str]) -> bool:
        """Alert when client system needs attention"""

        if health_score >= 80:
            level = AlertLevel.OPTIMIST
            title = f"Cliente {client_name}: Sistema saudável"
        elif health_score >= 60:
            level = AlertLevel.MEDIUM
            title = f"Cliente {client_name}: Atenção necessária"
        else:
            level = AlertLevel.AGGRESSIVE
            title = f"Cliente {client_name}: SERVIÇO URGENTE"

        body_lines = [
            f"# 🏢 Status do Cliente: {client_name}",
            f"**Health Score:** {health_score}/100",
            "",
            "## Problemas Detectados:",
        ]

        for issue in issues:
            body_lines.append(f"- ⚠️ {issue}")

        body_lines.extend([
            "",
            "## Ações Recomendadas:",
            "1. 📞 Ligar para o cliente",
            "2. 🔧 Agendar visita de calibração",
            "3. 💼 Gerar proposta de serviço",
            "",
            "💡 **Oportunidade de Receita:** Cliente pode se beneficiar de contrato de manutenção preventiva",
        ])

        body = "\n".join(body_lines)

        return self.notifier.send(
            channel=ChannelType.BUSINESS_PRIVATE,
            level=level,
            title=title,
            body=body,
        )

    def send_revenue_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Alert about business revenue opportunities"""

        body = f"""# 💰 Oportunidade de Negócio

**Cliente:** {opportunity['client_name']}
**Tipo:** {opportunity['type']}
**Valor Estimado:** €{opportunity['estimated_value']:.2f}

## Detalhes:
{opportunity['description']}

## Próximos Passos:
1. Preparar proposta comercial
2. Contactar cliente em até 24h
3. Agendar demonstração/visita

⏰ **Urgência:** {opportunity.get('urgency', 'Normal')}
"""

        return self.notifier.send(
            channel=ChannelType.BUSINESS_PRIVATE,
            level=AlertLevel.MEDIUM,
            title=f"Nova Oportunidade: {opportunity['client_name']}",
            body=body,
        )


# Global instances
multi_notifier = MultiChannelNtfy()
business_reporter = BusinessIntelligenceReporter(multi_notifier)


# ── Convenience Functions ─────────────────────────────────────────

def send_client_alert(level: AlertLevel, title: str, body: str) -> bool:
    """Send alert to public client channel"""
    return multi_notifier.send(ChannelType.CLIENT_PUBLIC, level, title, body)


def send_business_alert(level: AlertLevel, title: str, body: str) -> bool:
    """Send alert to private business channel"""
    return multi_notifier.send(ChannelType.BUSINESS_PRIVATE, level, title, body)


def send_emergency_alert(title: str, body: str) -> bool:
    """Send to emergency channel (always aggressive)"""
    return multi_notifier.send(ChannelType.EMERGENCY, AlertLevel.AGGRESSIVE, title, body)


def send_daily_digest(metrics: Dict[str, Any]) -> bool:
    """Send daily business intelligence digest"""
    return business_reporter.send_daily_digest(metrics)
