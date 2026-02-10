import pytest
from config_loader import ConfigLoader


class TestConfigLoader:
    """Test configuration loading and merging."""

    def test_base_config_loads(self):
        """Base configuration should load successfully."""
        loader = ConfigLoader()
        assert loader.base_config is not None
        assert 'base_ranges' in loader.base_config
        assert 'sensors' in loader.base_config

    def test_variety_rosso_loads(self):
        """Rosso premium variety should load and merge."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        assert config is not None
        assert 'variety' in config
        assert config['variety']['name'] == 'Rosso Premium'

    def test_variety_curly_loads(self):
        """Curly green variety should load and merge."""
        loader = ConfigLoader()
        config = loader.load_variety('curly_green')

        assert config is not None
        assert 'variety' in config
        assert config['variety']['name'] == 'Curly Green'

    def test_variety_overrides_base(self):
        """Variety-specific settings should override base settings."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        # Rosso has different optimal ranges than base
        assert 'optimal_ranges' in config
        temp = config['optimal_ranges']['temperature']

        # Rosso prefers warmer temps (20-24) vs base (18-24)
        assert temp['optimal_min'] == 20.0

    def test_base_values_inherited(self):
        """Base values should be inherited when not overridden."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        # Common settings should be inherited
        assert 'common' in config
        assert config['common']['system_name'] == 'AgriTech Hydroponics'

    def test_rules_generated_for_variety(self):
        """Rules should be automatically generated for each variety."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        assert 'rules' in config
        rules = config['rules']
        assert len(rules) > 0

        # Should have temperature rules
        temp_rules = [r for r in rules if 'temp' in r['id']]
        assert len(temp_rules) >= 2  # low and high

    def test_rule_ids_include_variety_name(self):
        """Rule IDs should include variety name for uniqueness."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        rule_ids = [r['id'] for r in config['rules']]
        assert any('rosso_premium' in rid for rid in rule_ids)

    def test_different_varieties_different_rules(self):
        """Different varieties should have different rule thresholds."""
        loader = ConfigLoader()
        rosso = loader.load_variety('rosso_premium')
        curly = loader.load_variety('curly_green')

        # Find temperature rules
        rosso_temp_high = next(r for r in rosso['rules'] if r['id'] == 'rosso_premium_temp_high')
        curly_temp_high = next(r for r in curly['rules'] if r['id'] == 'curly_green_temp_high')

        # Rosso tolerates higher temps (28°C) vs Curly (26°C)
        assert rosso_temp_high['threshold'] > curly_temp_high['threshold']

    def test_get_all_varieties(self):
        """Should list all available varieties."""
        loader = ConfigLoader()
        varieties = loader.get_all_varieties()

        assert 'rosso_premium' in varieties
        assert 'curly_green' in varieties

    def test_calibration_schedule(self):
        """Should extract calibration schedule from config."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')
        schedule = loader.get_calibration_schedule(config)

        assert 'temperature' in schedule
        assert 'ph' in schedule

        # pH needs more frequent calibration
        assert schedule['ph']['interval_days'] < schedule['temperature']['interval_days']

    def test_maintenance_schedule(self):
        """Should extract maintenance schedule from config."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')
        maintenance = loader.get_maintenance_schedule(config)

        assert 'daily' in maintenance
        assert 'weekly' in maintenance
        assert 'monthly' in maintenance

    def test_time_based_notifications(self):
        """Should extract time-based notification schedule."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')
        notifications = loader.get_time_based_notifications(config)

        assert 'morning_check' in notifications
        assert 'monthly_calibration' in notifications


class TestVarietySpecifics:
    """Test variety-specific configurations."""

    def test_rosso_higher_light_requirement(self):
        """Rosso should require more light for color development."""
        loader = ConfigLoader()
        rosso = loader.load_variety('rosso_premium')
        curly = loader.load_variety('curly_green')

        rosso_light = rosso['optimal_ranges']['light']['optimal_min']
        curly_light = curly['optimal_ranges']['light']['optimal_min']

        assert rosso_light > curly_light

    def test_rosso_higher_ec_tolerance(self):
        """Rosso should tolerate higher EC for color/flavor."""
        loader = ConfigLoader()
        rosso = loader.load_variety('rosso_premium')
        curly = loader.load_variety('curly_green')

        rosso_ec = rosso['optimal_ranges']['ec']['optimal_max']
        curly_ec = curly['optimal_ranges']['ec']['optimal_max']

        assert rosso_ec > curly_ec

    def test_curly_cooler_temps(self):
        """Curly lettuce should prefer cooler temperatures."""
        loader = ConfigLoader()
        rosso = loader.load_variety('rosso_premium')
        curly = loader.load_variety('curly_green')

        rosso_temp = rosso['optimal_ranges']['temperature']['optimal_max']
        curly_temp = curly['optimal_ranges']['temperature']['optimal_max']

        assert curly_temp < rosso_temp

    def test_growth_stages_defined(self):
        """Both varieties should have growth stage definitions."""
        loader = ConfigLoader()
        rosso = loader.load_variety('rosso_premium')
        curly = loader.load_variety('curly_green')

        assert 'growth_stages' in rosso
        assert 'seedling' in rosso['growth_stages']
        assert 'vegetative' in rosso['growth_stages']
        assert 'maturity' in rosso['growth_stages']

        assert 'growth_stages' in curly

    def test_preventive_actions_specific(self):
        """Preventive actions should be variety-specific."""
        loader = ConfigLoader()
        curly = loader.load_variety('curly_green')

        actions = curly.get('preventive_actions', {})
        high_temp_action = actions.get('high_temperature', '')

        # Curly is more sensitive to heat
        assert 'URGENT' in high_temp_action or 'sensitive' in high_temp_action.lower()


class TestConfigMerging:
    """Test configuration merging logic."""

    def test_deep_merge(self):
        """Nested dictionaries should merge properly."""
        loader = ConfigLoader()
        base = {'a': {'b': 1, 'c': 2}, 'd': 3}
        override = {'a': {'b': 99}, 'e': 5}

        result = loader._merge_configs(base, override)

        assert result['a']['b'] == 99  # Override
        assert result['a']['c'] == 2   # Inherited
        assert result['d'] == 3         # Inherited
        assert result['e'] == 5         # New

    def test_metadata_preserved(self):
        """Metadata fields (_prefixed) should be preserved."""
        loader = ConfigLoader()
        config = loader.load_variety('rosso_premium')

        assert '_comment' in config
        assert '_scientific_name' in config
        assert '_type' in config
