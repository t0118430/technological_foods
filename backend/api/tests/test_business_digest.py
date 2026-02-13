"""
Tests for the Business Digest Service.

Tests digest generation, tone formatting, and ntfy sending.

Run: pytest test_business_digest.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from business.business_digest import BusinessDigestService


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_dashboard():
    """Create a MagicMock dashboard instance."""
    dashboard = MagicMock()
    dashboard.get_business_overview.return_value = {
        'active_clients': 5,
        'mrr': 750.0,
        'active_crops': 12,
        'visits_this_month': 3,
        'service_revenue_month': 150.0,
        'total_revenue_month': 900.0,
        'growth_rate_percent': 15.0,
        'status': 'healthy',
    }
    dashboard.get_revenue_metrics.return_value = {
        'by_tier': {
            'bronze': {'client_count': 3, 'mrr': 147.0},
            'silver': {'client_count': 1, 'mrr': 199.0},
            'gold': {'client_count': 1, 'mrr': 399.0},
        },
        'service_revenue_30d': 300.0,
        'avg_revenue_per_client': 150.0,
        'projected_annual': 10800.0,
        'churn_rate_percent': 0.0,
    }
    dashboard.get_crop_status.return_value = {
        'by_stage': {'vegetative': 4, 'seedling': 3, 'germination': 5},
        'by_variety': {'rosso_premium': 5, 'basil_genovese': 4, 'arugula_rocket': 3},
        'upcoming_harvests': [],
        'harvests_this_month': 2,
        'avg_yield_kg': 1.8,
        'total_active': 12,
    }
    dashboard.get_revenue_opportunities.return_value = [
        {
            'type': 'upsell',
            'description': 'Healthy client — pitch Silver tier',
            'priority': 'medium',
            'estimated_value': 150,
        },
        {
            'type': 'new_market',
            'description': 'Faro Sunday Market',
            'priority': 'medium',
            'estimated_value': 400,
        },
    ]
    return dashboard


@pytest.fixture
def service(mock_dashboard):
    """BusinessDigestService with mocked dashboard."""
    svc = BusinessDigestService()
    svc._dashboard = mock_dashboard
    return svc


# ── Digest Generation Tests ──────────────────────────────────────

class TestGenerateDigest:
    def test_default_tone_is_medium(self, service):
        """Default tone should be 'medium'."""
        result = service.generate_digest()
        assert result['tone'] == 'medium'

    def test_aggressive_tone(self, service):
        """Aggressive tone should be applied."""
        result = service.generate_digest('aggressive')
        assert result['tone'] == 'aggressive'
        assert 'BUSINESS DIGEST' in result['formatted_message']

    def test_optimist_tone(self, service):
        """Optimist tone should be applied."""
        result = service.generate_digest('optimist')
        assert result['tone'] == 'optimist'
        assert 'growing' in result['formatted_message'].lower() or 'up' in result['formatted_message'].lower()

    def test_invalid_tone_defaults_to_medium(self, service):
        """Invalid tone should default to 'medium'."""
        result = service.generate_digest('invalid_tone')
        assert result['tone'] == 'medium'

    def test_digest_structure(self, service):
        """Digest should contain all expected keys."""
        result = service.generate_digest()
        assert result['report_type'] == 'business_digest'
        assert 'generated_at' in result
        assert 'overview' in result
        assert 'revenue' in result
        assert 'crops' in result
        assert 'opportunities_count' in result
        assert 'formatted_message' in result

    def test_digest_overview_data(self, service):
        """Digest should contain correct overview data."""
        result = service.generate_digest()
        assert result['overview']['active_clients'] == 5
        assert result['overview']['mrr'] == 750.0

    def test_digest_opportunities_count(self, service):
        """Digest should count opportunities correctly."""
        result = service.generate_digest()
        assert result['opportunities_count'] == 2

    def test_digest_error_handling(self, service, mock_dashboard):
        """Digest should return error dict on failure."""
        mock_dashboard.get_business_overview.side_effect = Exception('DB down')
        result = service.generate_digest()
        assert 'error' in result
        assert 'DB down' in result['error']


# ── Formatted Message Tests ──────────────────────────────────────

class TestFormatDigest:
    def test_message_contains_revenue(self, service):
        """Formatted message should mention revenue."""
        result = service.generate_digest()
        msg = result['formatted_message']
        assert '750' in msg  # MRR
        assert '10800' in msg  # projected annual

    def test_aggressive_tone_has_urgency(self, service, mock_dashboard):
        """Aggressive tone should push for action."""
        mock_dashboard.get_business_overview.return_value['growth_rate_percent'] = 5.0
        result = service.generate_digest('aggressive')
        msg = result['formatted_message']
        assert 'below target' in msg.lower() or 'action' in msg.lower()

    def test_aggressive_tone_churn_warning(self, service, mock_dashboard):
        """Aggressive tone should highlight churn."""
        mock_dashboard.get_revenue_metrics.return_value['churn_rate_percent'] = 8.5
        result = service.generate_digest('aggressive')
        msg = result['formatted_message']
        assert '8.5%' in msg
        assert 'immediately' in msg.lower()

    def test_optimist_tone_highlights_wins(self, service):
        """Optimist tone should highlight positive metrics."""
        result = service.generate_digest('optimist')
        msg = result['formatted_message']
        assert '5 active clients' in msg or 'growing' in msg.lower()
        assert 'momentum' in msg.lower() or 'keep it up' in msg.lower()

    def test_message_contains_tier_breakdown(self, service):
        """Formatted message should include tier breakdown."""
        result = service.generate_digest()
        msg = result['formatted_message']
        assert 'bronze' in msg.lower() or 'silver' in msg.lower()

    def test_message_contains_crop_info(self, service):
        """Formatted message should include crop info."""
        result = service.generate_digest()
        msg = result['formatted_message']
        assert '12' in msg  # active crops
        assert 'Harvests this month' in msg

    def test_message_contains_opportunities(self, service):
        """Formatted message should list opportunities."""
        result = service.generate_digest()
        msg = result['formatted_message']
        assert 'Opportunities' in msg
        assert '550' in msg  # total value (150 + 400)

    def test_message_stages_listed(self, service):
        """Formatted message should show crop stages."""
        result = service.generate_digest()
        msg = result['formatted_message']
        assert 'vegetative' in msg.lower() or 'seedling' in msg.lower()


# ── Send Digest Tests ────────────────────────────────────────────

class TestSendDigest:
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', '')
    def test_send_without_topic_configured(self, service):
        """Send should report not sent when topic is not configured."""
        result = service.send_digest()
        assert result['ntfy_sent'] is False
        assert 'not configured' in result['ntfy_topic']

    @patch('business.business_digest.urllib.request.urlopen')
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', 'agritech-biz')
    def test_send_success(self, mock_urlopen, service):
        """Send should succeed when topic is configured."""
        mock_urlopen.return_value = MagicMock()
        result = service.send_digest('medium')
        assert result['ntfy_sent'] is True
        assert result['ntfy_topic'] == 'agritech-biz'
        mock_urlopen.assert_called_once()

    @patch('business.business_digest.urllib.request.urlopen')
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', 'agritech-biz')
    def test_send_failure(self, mock_urlopen, service):
        """Send should handle ntfy errors gracefully."""
        mock_urlopen.side_effect = Exception('Connection refused')
        result = service.send_digest()
        assert result['ntfy_sent'] is False
        assert result['report_type'] == 'business_digest'

    @patch('business.business_digest.urllib.request.urlopen')
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', 'agritech-biz')
    @patch('business.business_digest.NTFY_TOKEN', 'test-token')
    def test_send_with_auth_token(self, mock_urlopen, service):
        """Send should include Authorization header when token is set."""
        mock_urlopen.return_value = MagicMock()
        service.send_digest()
        req = mock_urlopen.call_args[0][0]
        assert req.get_header('Authorization') == 'Bearer test-token'

    @patch('business.business_digest.urllib.request.urlopen')
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', 'agritech-biz')
    def test_send_aggressive_sets_high_priority(self, mock_urlopen, service):
        """Aggressive tone should use priority 4."""
        mock_urlopen.return_value = MagicMock()
        service.send_digest('aggressive')
        req = mock_urlopen.call_args[0][0]
        assert req.get_header('Priority') == '4'

    @patch('business.business_digest.urllib.request.urlopen')
    @patch('business.business_digest.NTFY_BUSINESS_TOPIC', 'agritech-biz')
    def test_send_optimist_sets_low_priority(self, mock_urlopen, service):
        """Optimist tone should use priority 2."""
        mock_urlopen.return_value = MagicMock()
        service.send_digest('optimist')
        req = mock_urlopen.call_args[0][0]
        assert req.get_header('Priority') == '2'

    def test_send_with_dashboard_error(self, service, mock_dashboard):
        """Send should return error when dashboard fails."""
        mock_dashboard.get_business_overview.side_effect = Exception('Offline')
        result = service.send_digest()
        assert 'error' in result


# ── Lazy Dashboard Property Test ─────────────────────────────────

class TestDashboardProperty:
    def test_lazy_initialization(self):
        """Dashboard property should start as None."""
        svc = BusinessDigestService()
        assert svc._dashboard is None

    def test_uses_injected_value(self, service, mock_dashboard):
        """When _dashboard is set directly, the property returns it."""
        assert service.dashboard is mock_dashboard
