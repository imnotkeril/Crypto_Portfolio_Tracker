"""
Assets module - list of tradeable assets (Binance USDT pairs) with caching
"""
import os
import json
from typing import List

# Fallback list when Binance API is unavailable
DEFAULT_USDT_ASSETS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "USDT", "ADA", "DOGE", "AVAX", "DOT",
    "LINK", "MATIC", "UNI", "ATOM", "LTC", "ETC", "XLM", "BCH", "NEAR", "APT",
    "ARB", "OP", "INJ", "SUI", "SEI", "TIA", "FET", "RENDER", "PEPE", "WIF",
    "BONK", "FLOKI", "NOT", "STRK", "MANTA", "JUP", "PYTH", "ORDI", "STX",
]

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
ASSETS_CACHE_FILE = os.path.join(CACHE_DIR, 'binance_usdt_assets.json')
CACHE_MAX_AGE_SECONDS = 86400  # 24 hours


def _load_cached_assets() -> List[str]:
    """Load cached asset list from file"""
    if not os.path.exists(ASSETS_CACHE_FILE):
        return []
    try:
        with open(ASSETS_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('assets', [])
    except Exception:
        return []


def _save_assets_cache(assets: List[str]):
    """Save asset list to cache file"""
    os.makedirs(os.path.dirname(ASSETS_CACHE_FILE), exist_ok=True)
    try:
        with open(ASSETS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'assets': assets}, f, indent=2)
    except Exception:
        pass


def get_available_assets(use_cache: bool = True) -> List[str]:
    """
    Get list of assets available as USDT pairs on Binance.
    Uses cache if valid; on API error returns fallback list.
    """
    import time
    if use_cache and os.path.exists(ASSETS_CACHE_FILE):
        try:
            with open(ASSETS_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assets = data.get('assets', [])
            cached_at = data.get('cached_at', 0)
            if assets and (time.time() - cached_at) < CACHE_MAX_AGE_SECONDS:
                return assets
        except Exception:
            pass

    try:
        from utils.price_fetcher import _get_ccxt
        _, exchange = _get_ccxt()
        markets = exchange.load_markets()
        assets = []
        for symbol in markets:
            if (symbol.endswith('/USDT')
                    and markets[symbol].get('active', True)):
                base = symbol.replace('/USDT', '')
                if base not in assets:
                    assets.append(base)
        assets.sort()
        if assets:
            os.makedirs(os.path.dirname(ASSETS_CACHE_FILE), exist_ok=True)
            with open(ASSETS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(
                    {'assets': assets, 'cached_at': time.time()}, f, indent=2)
            return assets
    except Exception:
        pass

    return list(DEFAULT_USDT_ASSETS)


def get_assets_for_funding() -> List[str]:
    """Assets that can have funding (exclude USDT)"""
    all_assets = get_available_assets()
    return [a for a in all_assets if a != 'USDT']
