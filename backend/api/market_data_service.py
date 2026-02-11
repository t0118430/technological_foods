"""
Market Data Service - Curated market prices and seasonal demand for Algarve.

Extends the existing get_local_market_data pattern in business_dashboard.py
with manual update capability and seasonal demand multipliers.

Author: AgriTech Hydroponics
License: MIT
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger('market-data')

# Persist prices to file so manual updates survive restarts
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
MARKET_DATA_FILE = DATA_DIR / 'market_prices.json'

# Default market prices (EUR/kg) for Algarve region
DEFAULT_PRICES = {
    'lettuce_rosso_premium': {
        'name': 'Alface Rosso Premium',
        'price_per_kg': 10.00,
        'unit': 'EUR/kg',
        'category': 'lettuce',
        'premium': True,
        'notes': 'Premium red lettuce - restaurant grade',
    },
    'lettuce_curly_green': {
        'name': 'Alface Frisada Verde',
        'price_per_kg': 6.00,
        'unit': 'EUR/kg',
        'category': 'lettuce',
        'premium': False,
        'notes': 'Standard curly green lettuce',
    },
    'arugula': {
        'name': 'Rúcula',
        'price_per_kg': 8.00,
        'unit': 'EUR/kg',
        'category': 'herbs',
        'premium': False,
        'notes': 'Baby arugula, pre-washed',
    },
    'basil_genovese': {
        'name': 'Manjericão Genovese',
        'price_per_kg': 20.00,
        'unit': 'EUR/kg',
        'category': 'herbs',
        'premium': True,
        'notes': 'Fresh basil - high margin herb',
    },
    'mint_spearmint': {
        'name': 'Hortelã',
        'price_per_kg': 15.00,
        'unit': 'EUR/kg',
        'category': 'herbs',
        'premium': False,
        'notes': 'Fresh spearmint',
    },
    'tomato_cherry': {
        'name': 'Tomate Cherry',
        'price_per_kg': 5.00,
        'unit': 'EUR/kg',
        'category': 'vegetables',
        'premium': False,
        'notes': 'Hydroponic cherry tomatoes',
    },
}

# Seasonal demand multipliers (Algarve tourism pattern)
SEASONAL_DEMAND = {
    1: {'multiplier': 0.8, 'season': 'winter', 'notes': 'Low season, local demand only'},
    2: {'multiplier': 0.8, 'season': 'winter', 'notes': 'Low season, carnival bump'},
    3: {'multiplier': 1.0, 'season': 'spring', 'notes': 'Easter tourists begin'},
    4: {'multiplier': 1.2, 'season': 'spring', 'notes': 'Easter peak, restaurants opening'},
    5: {'multiplier': 1.8, 'season': 'peak', 'notes': 'Tourist season starts'},
    6: {'multiplier': 2.5, 'season': 'peak', 'notes': 'High season, restaurant demand surges'},
    7: {'multiplier': 3.0, 'season': 'peak', 'notes': 'Peak tourist month'},
    8: {'multiplier': 3.0, 'season': 'peak', 'notes': 'Peak tourist month'},
    9: {'multiplier': 2.0, 'season': 'peak', 'notes': 'Late season, still strong demand'},
    10: {'multiplier': 1.2, 'season': 'autumn', 'notes': 'Shoulder season'},
    11: {'multiplier': 0.9, 'season': 'autumn', 'notes': 'Transitioning to low season'},
    12: {'multiplier': 1.0, 'season': 'winter', 'notes': 'Holiday season bump'},
}


class MarketDataService:
    """Market prices and seasonal demand for Algarve produce."""

    def __init__(self):
        self.prices: Dict[str, Dict] = {}
        self._load_prices()

    def _load_prices(self):
        """Load prices from file or use defaults."""
        if MARKET_DATA_FILE.exists():
            try:
                with open(MARKET_DATA_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.prices = saved.get('prices', DEFAULT_PRICES.copy())
                    logger.info("Market prices loaded from file")
                    return
            except Exception as e:
                logger.warning(f"Failed to load market prices file: {e}")

        self.prices = DEFAULT_PRICES.copy()
        logger.info("Using default market prices")

    def _save_prices(self):
        """Persist prices to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(MARKET_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'prices': self.prices,
                    'last_updated': datetime.now().isoformat(),
                }, f, indent=2, ensure_ascii=False)
            logger.info("Market prices saved to file")
        except Exception as e:
            logger.error(f"Failed to save market prices: {e}")

    # ── Market Prices ──────────────────────────────────────────────

    def get_market_prices(self) -> Dict[str, Any]:
        """
        Get current market prices for all produce.

        Returns:
            Dict with products, categories, price summary
        """
        current_month = datetime.now().month
        seasonal = SEASONAL_DEMAND.get(current_month, {'multiplier': 1.0, 'season': 'unknown'})

        products = []
        for product_id, info in self.prices.items():
            base_price = info.get('price_per_kg', 0)
            adjusted_price = round(base_price * seasonal['multiplier'], 2)

            products.append({
                'id': product_id,
                'name': info.get('name', product_id),
                'base_price_per_kg': base_price,
                'seasonal_price_per_kg': adjusted_price,
                'unit': info.get('unit', 'EUR/kg'),
                'category': info.get('category', 'other'),
                'premium': info.get('premium', False),
                'notes': info.get('notes', ''),
            })

        # Category averages
        categories = {}
        for p in products:
            cat = p['category']
            if cat not in categories:
                categories[cat] = {'products': 0, 'avg_base_price': 0, 'total': 0}
            categories[cat]['products'] += 1
            categories[cat]['total'] += p['base_price_per_kg']
        for cat in categories:
            categories[cat]['avg_base_price'] = round(
                categories[cat]['total'] / categories[cat]['products'], 2
            )
            del categories[cat]['total']

        return {
            'products': products,
            'categories': categories,
            'current_season': seasonal['season'],
            'demand_multiplier': seasonal['multiplier'],
            'season_notes': seasonal.get('notes', ''),
            'last_updated': datetime.now().isoformat(),
            'source': 'curated_algarve',
        }

    # ── Seasonal Demand ────────────────────────────────────────────

    def get_seasonal_demand(self) -> Dict[str, Any]:
        """
        Get month-by-month demand multipliers.

        Returns:
            Dict with monthly demand data, current month info, planning notes
        """
        current_month = datetime.now().month
        current = SEASONAL_DEMAND.get(current_month, {})

        monthly = {}
        for month_num, data in SEASONAL_DEMAND.items():
            month_name = datetime(2024, month_num, 1).strftime('%B')
            monthly[month_name] = {
                'month': month_num,
                'multiplier': data['multiplier'],
                'season': data['season'],
                'notes': data['notes'],
                'is_current': month_num == current_month,
            }

        # Planning insights
        peak_months = [m for m, d in SEASONAL_DEMAND.items() if d['multiplier'] >= 2.0]
        low_months = [m for m, d in SEASONAL_DEMAND.items() if d['multiplier'] < 1.0]

        return {
            'current_month': datetime.now().strftime('%B'),
            'current_multiplier': current.get('multiplier', 1.0),
            'current_season': current.get('season', 'unknown'),
            'monthly': monthly,
            'planning': {
                'peak_demand_months': [datetime(2024, m, 1).strftime('%B') for m in peak_months],
                'low_demand_months': [datetime(2024, m, 1).strftime('%B') for m in low_months],
                'peak_multiplier': max(d['multiplier'] for d in SEASONAL_DEMAND.values()),
                'recommendation': _get_planting_recommendation(current_month),
            },
        }

    # ── Update Prices ──────────────────────────────────────────────

    def update_market_prices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manual price update for user-observed prices.

        Args:
            data: Dict with product updates. Format:
                  {
                    "products": {
                      "lettuce_rosso_premium": {"price_per_kg": 12.00},
                      "basil_genovese": {"price_per_kg": 22.00, "notes": "Premium organic"}
                    }
                  }

        Returns:
            Dict with updated products and status
        """
        products_data = data.get('products', {})
        if not products_data:
            return {'error': 'No products provided. Use format: {"products": {"product_id": {"price_per_kg": X}}}'}

        updated = []
        for product_id, updates in products_data.items():
            if product_id not in self.prices:
                # New product — create entry
                self.prices[product_id] = {
                    'name': updates.get('name', product_id.replace('_', ' ').title()),
                    'price_per_kg': updates.get('price_per_kg', 0),
                    'unit': updates.get('unit', 'EUR/kg'),
                    'category': updates.get('category', 'other'),
                    'premium': updates.get('premium', False),
                    'notes': updates.get('notes', ''),
                }
                updated.append({'id': product_id, 'action': 'created'})
            else:
                # Update existing
                for key, value in updates.items():
                    self.prices[product_id][key] = value
                updated.append({'id': product_id, 'action': 'updated'})

        self._save_prices()

        return {
            'status': 'updated',
            'updated_products': updated,
            'total_products': len(self.prices),
            'timestamp': datetime.now().isoformat(),
        }


# ── Helper functions ───────────────────────────────────────────────

def _get_planting_recommendation(current_month: int) -> str:
    """Get planting recommendation based on current month."""
    if current_month in (1, 2):
        return 'Start seedlings now for April/May harvest — peak season supply'
    elif current_month in (3, 4):
        return 'Maximize planting — peak tourist season demand in 6-8 weeks'
    elif current_month in (5, 6):
        return 'Maintain high production — peak demand period active'
    elif current_month in (7, 8):
        return 'Continue production — demand still high, watch for heat stress'
    elif current_month in (9, 10):
        return 'Reduce planting volume — transitioning to shoulder season'
    elif current_month in (11, 12):
        return 'Focus on high-value herbs — lower volume, higher margins for winter'
    return 'Monitor demand and adjust production accordingly'


# Global instance
market_data_service = MarketDataService()
