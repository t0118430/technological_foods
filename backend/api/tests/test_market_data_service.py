"""
Tests for MarketDataService (market_data_service.py)

Covers: initialization, market prices, seasonal demand, price updates,
seasonal price adjustments, and planting recommendation helper.
"""

import copy
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from market_data_service import (
    MarketDataService,
    SEASONAL_DEMAND,
    DEFAULT_PRICES,
    _get_planting_recommendation,
)


@pytest.fixture
def service(tmp_path):
    """Fresh MarketDataService with file I/O redirected to a temp directory.

    Uses deep copy of DEFAULT_PRICES to prevent cross-test mutation
    (the service's _load_prices does a shallow copy).
    """
    import market_data_service

    original_file = market_data_service.MARKET_DATA_FILE
    original_dir = market_data_service.DATA_DIR
    original_defaults = market_data_service.DEFAULT_PRICES
    market_data_service.DATA_DIR = tmp_path
    market_data_service.MARKET_DATA_FILE = tmp_path / 'test_prices.json'
    market_data_service.DEFAULT_PRICES = copy.deepcopy(original_defaults)
    svc = MarketDataService()
    yield svc
    market_data_service.MARKET_DATA_FILE = original_file
    market_data_service.DATA_DIR = original_dir
    market_data_service.DEFAULT_PRICES = original_defaults


# -- Initialization ---------------------------------------------------------

class TestInitialization:
    def test_loads_default_prices_when_no_file_exists(self, service):
        """When no market_prices.json exists, defaults are loaded."""
        assert len(service.prices) == len(DEFAULT_PRICES)
        for key in DEFAULT_PRICES:
            assert key in service.prices

    def test_all_six_default_products_present(self, service):
        expected = {
            'lettuce_rosso_premium',
            'lettuce_curly_green',
            'arugula',
            'basil_genovese',
            'mint_spearmint',
            'tomato_cherry',
        }
        assert set(service.prices.keys()) == expected

    def test_default_prices_values(self, service):
        """Verify the specific default price for key products."""
        assert service.prices['basil_genovese']['price_per_kg'] == 20.00
        assert service.prices['tomato_cherry']['price_per_kg'] == 5.00
        assert service.prices['lettuce_rosso_premium']['price_per_kg'] == 10.00
        assert service.prices['lettuce_curly_green']['price_per_kg'] == 6.00
        assert service.prices['arugula']['price_per_kg'] == 8.00
        assert service.prices['mint_spearmint']['price_per_kg'] == 15.00

    def test_basil_is_highest_priced(self, service):
        prices = {k: v['price_per_kg'] for k, v in service.prices.items()}
        assert max(prices, key=prices.get) == 'basil_genovese'

    def test_tomato_is_lowest_priced(self, service):
        prices = {k: v['price_per_kg'] for k, v in service.prices.items()}
        assert min(prices, key=prices.get) == 'tomato_cherry'


# -- get_market_prices() ----------------------------------------------------

class TestGetMarketPrices:
    def test_returns_required_keys(self, service):
        result = service.get_market_prices()
        assert 'products' in result
        assert 'categories' in result
        assert 'current_season' in result
        assert 'demand_multiplier' in result
        assert result['source'] == 'curated_algarve'

    def test_products_count_matches_defaults(self, service):
        result = service.get_market_prices()
        assert len(result['products']) == 6

    def test_product_structure(self, service):
        result = service.get_market_prices()
        product = result['products'][0]
        required_fields = {
            'id', 'name', 'base_price_per_kg', 'seasonal_price_per_kg',
            'unit', 'category', 'premium', 'notes',
        }
        assert required_fields.issubset(set(product.keys()))

    def test_categories_computed(self, service):
        result = service.get_market_prices()
        categories = result['categories']
        assert 'lettuce' in categories
        assert 'herbs' in categories
        assert 'vegetables' in categories
        assert categories['lettuce']['products'] == 2
        assert categories['herbs']['products'] == 3
        assert categories['vegetables']['products'] == 1

    @patch('market_data_service.datetime')
    def test_seasonal_price_adjustment_july(self, mock_dt, service):
        """In July (multiplier 3.0), seasonal prices should be 3x base."""
        mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = service.get_market_prices()

        assert result['demand_multiplier'] == 3.0
        assert result['current_season'] == 'peak'

        basil = next(p for p in result['products'] if p['id'] == 'basil_genovese')
        assert basil['base_price_per_kg'] == 20.00
        assert basil['seasonal_price_per_kg'] == 60.00

        tomato = next(p for p in result['products'] if p['id'] == 'tomato_cherry')
        assert tomato['base_price_per_kg'] == 5.00
        assert tomato['seasonal_price_per_kg'] == 15.00

    @patch('market_data_service.datetime')
    def test_seasonal_price_adjustment_january(self, mock_dt, service):
        """In January (multiplier 0.8), seasonal prices should be 80% of base."""
        mock_dt.now.return_value = datetime(2026, 1, 10, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = service.get_market_prices()

        assert result['demand_multiplier'] == 0.8
        assert result['current_season'] == 'winter'

        rosso = next(p for p in result['products'] if p['id'] == 'lettuce_rosso_premium')
        assert rosso['seasonal_price_per_kg'] == 8.00  # 10.00 * 0.8

    @patch('market_data_service.datetime')
    def test_seasonal_price_adjustment_august(self, mock_dt, service):
        """August also has multiplier 3.0 (peak tourist month)."""
        mock_dt.now.return_value = datetime(2026, 8, 1, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = service.get_market_prices()
        assert result['demand_multiplier'] == 3.0

    @patch('market_data_service.datetime')
    def test_seasonal_price_adjustment_june(self, mock_dt, service):
        """June has multiplier 2.5."""
        mock_dt.now.return_value = datetime(2026, 6, 15, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = service.get_market_prices()
        assert result['demand_multiplier'] == 2.5

        basil = next(p for p in result['products'] if p['id'] == 'basil_genovese')
        assert basil['seasonal_price_per_kg'] == 50.00  # 20.00 * 2.5

    def test_category_average_prices(self, service):
        result = service.get_market_prices()
        herbs = result['categories']['herbs']
        # herbs: arugula(8) + basil(20) + mint(15) = 43 / 3 = 14.33
        assert herbs['avg_base_price'] == round((8.00 + 20.00 + 15.00) / 3, 2)


# -- get_seasonal_demand() --------------------------------------------------

class TestGetSeasonalDemand:
    def test_returns_required_keys(self, service):
        result = service.get_seasonal_demand()
        assert 'current_month' in result
        assert 'monthly' in result
        assert 'planning' in result
        assert 'current_multiplier' in result
        assert 'current_season' in result

    def test_monthly_data_has_12_months(self, service):
        result = service.get_seasonal_demand()
        assert len(result['monthly']) == 12

    def test_monthly_entries_structure(self, service):
        result = service.get_seasonal_demand()
        for month_name, data in result['monthly'].items():
            assert 'month' in data
            assert 'multiplier' in data
            assert 'season' in data
            assert 'notes' in data
            assert 'is_current' in data

    def test_exactly_one_month_is_current(self, service):
        result = service.get_seasonal_demand()
        current_count = sum(
            1 for data in result['monthly'].values() if data['is_current']
        )
        assert current_count == 1

    def test_peak_months_include_june_july_august(self, service):
        result = service.get_seasonal_demand()
        peak_months = result['planning']['peak_demand_months']
        assert 'June' in peak_months
        assert 'July' in peak_months
        assert 'August' in peak_months

    def test_peak_multiplier_is_3_0(self, service):
        result = service.get_seasonal_demand()
        assert result['planning']['peak_multiplier'] == 3.0

    def test_low_demand_months_include_january(self, service):
        result = service.get_seasonal_demand()
        low_months = result['planning']['low_demand_months']
        assert 'January' in low_months
        assert 'February' in low_months

    def test_planning_has_recommendation(self, service):
        result = service.get_seasonal_demand()
        assert isinstance(result['planning']['recommendation'], str)
        assert len(result['planning']['recommendation']) > 0

    @patch('market_data_service.datetime')
    def test_current_month_displayed_correctly(self, mock_dt, service):
        mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = service.get_seasonal_demand()
        assert result['current_month'] == 'July'
        assert result['current_multiplier'] == 3.0
        assert result['current_season'] == 'peak'

    def test_june_through_august_multiplier_at_least_2_5(self):
        """Peak months (June-August) should all have multiplier >= 2.5."""
        for month in (6, 7, 8):
            assert SEASONAL_DEMAND[month]['multiplier'] >= 2.5


# -- update_market_prices() -------------------------------------------------

class TestUpdateMarketPrices:
    def test_update_existing_product(self, service):
        result = service.update_market_prices({
            'products': {
                'lettuce_rosso_premium': {'price_per_kg': 12.50}
            }
        })
        assert result['status'] == 'updated'
        assert service.prices['lettuce_rosso_premium']['price_per_kg'] == 12.50
        updated_items = result['updated_products']
        assert len(updated_items) == 1
        assert updated_items[0]['action'] == 'updated'
        assert updated_items[0]['id'] == 'lettuce_rosso_premium'

    def test_update_preserves_other_fields(self, service):
        original_name = service.prices['arugula']['name']
        service.update_market_prices({
            'products': {
                'arugula': {'price_per_kg': 9.50}
            }
        })
        assert service.prices['arugula']['name'] == original_name
        assert service.prices['arugula']['price_per_kg'] == 9.50

    def test_create_new_product(self, service):
        result = service.update_market_prices({
            'products': {
                'microgreens_sunflower': {
                    'name': 'Microgreens Girassol',
                    'price_per_kg': 30.00,
                    'category': 'microgreens',
                    'premium': True,
                }
            }
        })
        assert result['status'] == 'updated'
        assert 'microgreens_sunflower' in service.prices
        assert service.prices['microgreens_sunflower']['price_per_kg'] == 30.00
        assert service.prices['microgreens_sunflower']['category'] == 'microgreens'
        assert result['updated_products'][0]['action'] == 'created'

    def test_new_product_defaults(self, service):
        """New product without all fields gets sensible defaults."""
        service.update_market_prices({
            'products': {
                'watercress': {'price_per_kg': 12.00}
            }
        })
        entry = service.prices['watercress']
        assert entry['unit'] == 'EUR/kg'
        assert entry['category'] == 'other'
        assert entry['premium'] is False
        assert entry['name'] == 'Watercress'  # auto-generated from key

    def test_no_products_provided_returns_error(self, service):
        result = service.update_market_prices({})
        assert 'error' in result

    def test_empty_products_dict_returns_error(self, service):
        result = service.update_market_prices({'products': {}})
        assert 'error' in result

    def test_update_multiple_products(self, service):
        result = service.update_market_prices({
            'products': {
                'basil_genovese': {'price_per_kg': 22.00},
                'tomato_cherry': {'price_per_kg': 6.00},
            }
        })
        assert result['status'] == 'updated'
        assert len(result['updated_products']) == 2
        assert service.prices['basil_genovese']['price_per_kg'] == 22.00
        assert service.prices['tomato_cherry']['price_per_kg'] == 6.00

    def test_update_returns_total_products(self, service):
        result = service.update_market_prices({
            'products': {
                'new_herb': {'price_per_kg': 18.00}
            }
        })
        assert result['total_products'] == 7  # 6 defaults + 1 new

    def test_update_notes_field(self, service):
        service.update_market_prices({
            'products': {
                'basil_genovese': {'notes': 'Organic certified'}
            }
        })
        assert service.prices['basil_genovese']['notes'] == 'Organic certified'
        # Price should remain unchanged
        assert service.prices['basil_genovese']['price_per_kg'] == 20.00

    @patch.object(MarketDataService, '_save_prices')
    def test_save_prices_called_on_update(self, mock_save, service):
        service.update_market_prices({
            'products': {
                'basil_genovese': {'price_per_kg': 25.00}
            }
        })
        mock_save.assert_called_once()


# -- _get_planting_recommendation() -----------------------------------------

class TestGetPlantingRecommendation:
    def test_january_recommendation(self):
        rec = _get_planting_recommendation(1)
        assert 'seedlings' in rec.lower() or 'Start' in rec

    def test_february_recommendation(self):
        rec = _get_planting_recommendation(2)
        assert 'seedlings' in rec.lower() or 'Start' in rec

    def test_march_recommendation(self):
        rec = _get_planting_recommendation(3)
        assert 'peak' in rec.lower() or 'planting' in rec.lower()

    def test_april_recommendation(self):
        rec = _get_planting_recommendation(4)
        assert 'Maximize' in rec or 'peak' in rec.lower()

    def test_may_june_high_production(self):
        for month in (5, 6):
            rec = _get_planting_recommendation(month)
            assert 'production' in rec.lower() or 'peak' in rec.lower()

    def test_july_august_continue_production(self):
        for month in (7, 8):
            rec = _get_planting_recommendation(month)
            assert 'production' in rec.lower() or 'heat' in rec.lower()

    def test_september_october_reduce(self):
        for month in (9, 10):
            rec = _get_planting_recommendation(month)
            assert 'Reduce' in rec or 'shoulder' in rec.lower()

    def test_november_december_herbs(self):
        for month in (11, 12):
            rec = _get_planting_recommendation(month)
            assert 'herbs' in rec.lower() or 'winter' in rec.lower()

    def test_returns_string_for_all_months(self):
        for month in range(1, 13):
            rec = _get_planting_recommendation(month)
            assert isinstance(rec, str)
            assert len(rec) > 10


# -- SEASONAL_DEMAND data structure -----------------------------------------

class TestSeasonalDemandData:
    def test_all_12_months_present(self):
        assert len(SEASONAL_DEMAND) == 12
        for month in range(1, 13):
            assert month in SEASONAL_DEMAND

    def test_july_and_august_are_peak(self):
        assert SEASONAL_DEMAND[7]['multiplier'] == 3.0
        assert SEASONAL_DEMAND[8]['multiplier'] == 3.0

    def test_winter_months_are_low(self):
        assert SEASONAL_DEMAND[1]['multiplier'] < 1.0
        assert SEASONAL_DEMAND[2]['multiplier'] < 1.0

    def test_each_month_has_required_keys(self):
        for month, data in SEASONAL_DEMAND.items():
            assert 'multiplier' in data
            assert 'season' in data
            assert 'notes' in data

    def test_multipliers_are_positive(self):
        for month, data in SEASONAL_DEMAND.items():
            assert data['multiplier'] > 0
