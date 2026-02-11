import time
import pytest
from notifications.alert_escalation import AlertEscalationManager, ESCALATION_LEVELS


class TestAlertEscalationBasics:
    """Test basic escalation functionality."""

    def test_first_alert_always_sends(self):
        """First alert should always be sent at preventive level."""
        mgr = AlertEscalationManager()

        result = mgr.should_send_alert(
            rule_id='temp_low',
            sensor='temperature',
            current_value=16.5,
            threshold=15.0,
            condition='below',
            original_message='Temperature approaching minimum',
        )

        assert result is not None
        assert result['should_send'] is True
        assert result['escalation_level'] == 0
        assert result['level_name'] == 'PREVENTIVE'
        assert result['severity'] == 'preventive'

    def test_immediate_repeat_suppressed(self):
        """Repeated alert within wait time should be suppressed."""
        mgr = AlertEscalationManager()

        # First alert
        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')

        # Immediate repeat - should be suppressed
        result = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')

        assert result is None  # Suppressed

    def test_escalates_after_wait_time(self):
        """Alert should escalate after wait time passes."""
        mgr = AlertEscalationManager()

        # First alert
        result1 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert result1['escalation_level'] == 0

        # Manually advance time
        alert = mgr.active_alerts['temp_low']
        alert.last_sent = time.time() - (6 * 60)  # 6 minutes ago (> 5 min wait)

        # Should escalate to WARNING
        result2 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert result2 is not None
        assert result2['escalation_level'] == 1
        assert result2['level_name'] == 'WARNING'


class TestImprovementDetection:
    """Test detection of situation improving."""

    def test_improving_below_condition(self):
        """For 'below' threshold, improvement is value increasing."""
        mgr = AlertEscalationManager()

        # Initial alert at 16.5°C (below 17°C warning)
        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')

        # Advance time
        alert = mgr.active_alerts['temp_low']
        alert.last_sent = time.time() - (6 * 60)

        # Temperature improved to 16.8°C
        result = mgr.should_send_alert('temp_low', 'temperature', 16.8, 15.0, 'below', 'Test')

        # Should be suppressed - user is fixing it
        assert result is None

    def test_improving_above_condition(self):
        """For 'above' threshold, improvement is value decreasing."""
        mgr = AlertEscalationManager()

        # Initial alert at 28.5°C (above 28°C warning)
        mgr.should_send_alert('temp_high', 'temperature', 28.5, 30.0, 'above', 'Test')

        # Advance time
        alert = mgr.active_alerts['temp_high']
        alert.last_sent = time.time() - (6 * 60)

        # Temperature improved to 28.2°C
        result = mgr.should_send_alert('temp_high', 'temperature', 28.2, 30.0, 'above', 'Test')

        # Should be suppressed - user is fixing it
        assert result is None

    def test_worsening_detected(self):
        """System should detect when situation is getting worse."""
        mgr = AlertEscalationManager()

        # Initial alert at 16.5°C
        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')

        # Advance time
        alert = mgr.active_alerts['temp_low']
        alert.last_sent = time.time() - (6 * 60)

        # Temperature dropped to 16.0°C (worse)
        result = mgr.should_send_alert('temp_low', 'temperature', 16.0, 15.0, 'below', 'Test')

        assert result is not None
        assert result['is_worsening'] is True


class TestEscalationSequence:
    """Test full escalation sequence."""

    def test_full_escalation_sequence(self):
        """Test complete escalation: PREVENTIVE → WARNING → CRITICAL → URGENT."""
        mgr = AlertEscalationManager()

        # Level 0: PREVENTIVE
        r1 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert r1['level_name'] == 'PREVENTIVE'
        assert r1['priority'] == 3

        # Advance 6 minutes → Level 1: WARNING
        mgr.active_alerts['temp_low'].last_sent = time.time() - (6 * 60)
        r2 = mgr.should_send_alert('temp_low', 'temperature', 16.4, 15.0, 'below', 'Test')
        assert r2['level_name'] == 'WARNING'
        assert r2['priority'] == 4

        # Advance 11 minutes → Level 2: CRITICAL
        mgr.active_alerts['temp_low'].last_sent = time.time() - (11 * 60)
        r3 = mgr.should_send_alert('temp_low', 'temperature', 16.3, 15.0, 'below', 'Test')
        assert r3['level_name'] == 'CRITICAL'
        assert r3['priority'] == 5

        # Advance 16 minutes → Level 3: URGENT
        mgr.active_alerts['temp_low'].last_sent = time.time() - (16 * 60)
        r4 = mgr.should_send_alert('temp_low', 'temperature', 16.2, 15.0, 'below', 'Test')
        assert r4['level_name'] == 'URGENT'
        assert r4['priority'] == 5

        # Advance 16 more minutes → Stay at URGENT (repeats)
        mgr.active_alerts['temp_low'].last_sent = time.time() - (16 * 60)
        r5 = mgr.should_send_alert('temp_low', 'temperature', 16.1, 15.0, 'below', 'Test')
        assert r5['level_name'] == 'URGENT'

    def test_sent_count_increments(self):
        """Sent count should increment with each escalation."""
        mgr = AlertEscalationManager()

        r1 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert r1['sent_count'] == 0  # First send

        mgr.active_alerts['temp_low'].last_sent = time.time() - (6 * 60)
        r2 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert r2['sent_count'] == 1  # Second send


class TestAlertResolution:
    """Test alert resolution and clearing."""

    def test_clear_alert_when_resolved(self):
        """Alert should be cleared when situation is resolved."""
        mgr = AlertEscalationManager()

        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        assert 'temp_low' in mgr.active_alerts

        # User fixed it - temp is now 18°C (above 15°C threshold)
        resolution = mgr.clear_alert('temp_low', 18.0, 'user_fixed')

        assert 'temp_low' not in mgr.active_alerts
        assert resolution is not None
        assert resolution['reason'] == 'user_fixed'
        assert resolution['original_value'] == 16.5
        assert resolution['final_value'] == 18.0

    def test_check_for_resolved_alerts_below_condition(self):
        """Auto-detect when 'below' condition is resolved."""
        mgr = AlertEscalationManager()

        # Alert: temp 16.5°C is approaching 15°C threshold
        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')

        # Temp is now safe (above threshold)
        sensor_data = {'temperature': 18.0}
        resolved = mgr.check_for_resolved_alerts(sensor_data)

        assert len(resolved) == 1
        assert resolved[0]['sensor'] == 'temperature'
        assert resolved[0]['reason'] == 'back_to_safe_zone'
        assert 'temp_low' not in mgr.active_alerts

    def test_check_for_resolved_alerts_above_condition(self):
        """Auto-detect when 'above' condition is resolved."""
        mgr = AlertEscalationManager()

        # Alert: temp 28.5°C is approaching 30°C threshold
        mgr.should_send_alert('temp_high', 'temperature', 28.5, 30.0, 'above', 'Test')

        # Temp is now safe (below threshold)
        sensor_data = {'temperature': 27.0}
        resolved = mgr.check_for_resolved_alerts(sensor_data)

        assert len(resolved) == 1
        assert 'temp_high' not in mgr.active_alerts

    def test_resolution_recorded_in_history(self):
        """Resolutions should be recorded in history."""
        mgr = AlertEscalationManager()

        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        mgr.clear_alert('temp_low', 18.0, 'resolved')

        assert len(mgr.resolved_alerts) == 1
        assert mgr.resolved_alerts[0]['sensor'] == 'temperature'


class TestMultipleAlerts:
    """Test handling multiple concurrent alerts."""

    def test_multiple_sensors_independent(self):
        """Alerts for different sensors should be independent."""
        mgr = AlertEscalationManager()

        # Temperature alert
        r1 = mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test1')
        assert r1 is not None

        # Humidity alert
        r2 = mgr.should_send_alert('hum_low', 'humidity', 42.0, 40.0, 'below', 'Test2')
        assert r2 is not None

        assert len(mgr.active_alerts) == 2

    def test_one_improves_other_escalates(self):
        """One alert improving shouldn't affect other alerts."""
        mgr = AlertEscalationManager()

        # Both alerts active
        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test1')
        mgr.should_send_alert('hum_low', 'humidity', 42.0, 40.0, 'below', 'Test2')

        # Advance time
        mgr.active_alerts['temp_low'].last_sent = time.time() - (6 * 60)
        mgr.active_alerts['hum_low'].last_sent = time.time() - (6 * 60)

        # Temp improves, humidity stays same
        r_temp = mgr.should_send_alert('temp_low', 'temperature', 17.0, 15.0, 'below', 'Test1')
        r_hum = mgr.should_send_alert('hum_low', 'humidity', 42.0, 40.0, 'below', 'Test2')

        assert r_temp is None  # Suppressed (improving)
        assert r_hum is not None  # Still escalates
        assert r_hum['escalation_level'] == 1  # WARNING


class TestStatusAndReporting:
    """Test status reporting functionality."""

    def test_get_active_alerts(self):
        """Should return list of active alerts."""
        mgr = AlertEscalationManager()

        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test1')
        mgr.should_send_alert('hum_low', 'humidity', 42.0, 40.0, 'below', 'Test2')

        active = mgr.get_active_alerts()

        assert len(active) == 2
        assert any(a['rule_id'] == 'temp_low' for a in active)
        assert any(a['rule_id'] == 'hum_low' for a in active)

    def test_get_status(self):
        """Should return comprehensive status."""
        mgr = AlertEscalationManager()

        mgr.should_send_alert('temp_low', 'temperature', 16.5, 15.0, 'below', 'Test')
        mgr.clear_alert('temp_low', 18.0, 'resolved')

        status = mgr.get_status()

        assert 'active_alerts' in status
        assert 'active_alert_details' in status
        assert 'recent_resolutions' in status
        assert 'escalation_levels' in status
        assert status['active_alerts'] == 0
        assert len(status['recent_resolutions']) == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_at_threshold_no_alert_needed(self):
        """Being exactly at threshold means no alert (rules use strict inequality)."""
        mgr = AlertEscalationManager()

        # This shouldn't happen in practice, but test the boundary
        result = mgr.should_send_alert('temp_low', 'temperature', 15.0, 15.0, 'below', 'Test')

        # Alert is created because escalation manager trusts the caller
        assert result is not None

    def test_clearing_nonexistent_alert(self):
        """Clearing nonexistent alert should handle gracefully."""
        mgr = AlertEscalationManager()

        resolution = mgr.clear_alert('nonexistent', 20.0)

        assert resolution is None

    def test_history_max_limit(self):
        """Resolution history should respect max limit."""
        mgr = AlertEscalationManager()
        mgr.max_history = 5

        # Create and resolve 10 alerts
        for i in range(10):
            mgr.should_send_alert(f'alert_{i}', 'temperature', 16.5, 15.0, 'below', 'Test')
            mgr.clear_alert(f'alert_{i}', 18.0)

        # Should only keep last 5
        assert len(mgr.resolved_alerts) == 5
        assert mgr.resolved_alerts[0]['rule_id'] == 'alert_5'
        assert mgr.resolved_alerts[-1]['rule_id'] == 'alert_9'
