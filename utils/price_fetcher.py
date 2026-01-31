"""
Price fetcher module for getting historical cryptocurrency prices
Uses Binance API via ccxt library with caching
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
import json

# Lazy import of ccxt
_ccxt = None
_exchange = None

def _get_ccxt():
    """Lazy import of ccxt module"""
    global _ccxt, _exchange
    if _ccxt is None:
        try:
            import ccxt
            _ccxt = ccxt
            _exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
        except ImportError:
            raise ImportError(
                "ccxt module is not installed. Install it with:\n"
                "  pip install ccxt\n"
                "Or install all dependencies:\n"
                "  pip install -r requirements.txt\n\n"
                "If you're using a virtual environment, make sure it's activated."
            )
    return _ccxt, _exchange


# Cache file path
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'price_cache.json')


def _load_cache() -> Dict:
    """Load price cache from file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def _save_cache(cache: Dict):
    """Save price cache to file"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def _get_cache_key(symbol: str, date: str) -> str:
    """Generate cache key"""
    return f"{symbol}_{date}"


def get_price(symbol: str, date: str) -> Optional[float]:
    """
    Get price for a symbol on a specific date
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT')
        date: Date string in format 'YYYY-MM-DD'
    Returns:
        Price as float or None if not found
    """
    # Normalize symbol
    if '/' not in symbol:
        symbol = f"{symbol}/USDT"
    
    symbol = symbol.upper()
    
    # Check cache first
    cache = _load_cache()
    cache_key = _get_cache_key(symbol, date)
    
    if cache_key in cache:
        return float(cache[cache_key])
    
    try:
        _, exchange = _get_ccxt()
        
        # Parse date
        target_date = datetime.strptime(date, '%Y-%m-%d')
        timestamp_ms = int(target_date.timestamp() * 1000)
        
        # Get OHLCV data for the date
        # Fetch a bit more data to ensure we get the right day
        since = timestamp_ms - 86400000  # 1 day before
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since, limit=2)
        
        if ohlcv:
            # Find the closest candle to our target date
            for candle in ohlcv:
                candle_date = datetime.fromtimestamp(candle[0] / 1000)
                if candle_date.date() == target_date.date():
                    price = candle[4]  # Close price
                    # Save to cache
                    cache[cache_key] = price
                    _save_cache(cache)
                    return float(price)
            
            # If exact date not found, use the closest one
            if ohlcv:
                price = ohlcv[-1][4]  # Close price of last candle
                cache[cache_key] = price
                _save_cache(cache)
                return float(price)
        
        return None
        
    except Exception as e:
        print(f"Error fetching price for {symbol} on {date}: {e}")
        return None


def get_price_range(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get prices for a date range
    Args:
        symbol: Trading pair
        start_date: Start date 'YYYY-MM-DD'
        end_date: End date 'YYYY-MM-DD'
    Returns:
        DataFrame with dates and prices
    """
    if '/' not in symbol:
        symbol = f"{symbol}/USDT"
    
    symbol = symbol.upper()
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    prices = []
    
    current_date = start
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        price = get_price(symbol, date_str)
        if price:
            dates.append(date_str)
            prices.append(price)
        current_date += timedelta(days=1)
    
    return pd.DataFrame({'date': dates, 'price': prices})


def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current price for a symbol
    Args:
        symbol: Trading pair
    Returns:
        Current price as float
    """
    if '/' not in symbol:
        symbol = f"{symbol}/USDT"
    
    symbol = symbol.upper()
    
    try:
        _, exchange = _get_ccxt()
        ticker = exchange.fetch_ticker(symbol)
        return float(ticker['last'])
    except Exception as e:
        print(f"Error fetching current price for {symbol}: {e}")
        return None


def find_dates_by_price(symbol: str, target_price: float, transaction_type: str, 
                        year: int, month: int, tolerance: float = 0.02) -> pd.DataFrame:
    """
    Find dates when price was close to target price in specified month
    Args:
        symbol: Trading pair (e.g., 'BTC', 'ETH')
        target_price: Target price to find
        transaction_type: 'buy' or 'sell'
        year: Year to search in
        month: Month to search in (1-12)
        tolerance: Price tolerance as fraction (default 2%)
    Returns:
        DataFrame with columns: date, close_price, high, low, match_type
        match_type: 'exact' if close price matches, 'high_low' if price was in range
    """
    if '/' not in symbol:
        symbol = f"{symbol}/USDT"
    
    symbol = symbol.upper()
    
    try:
        _, exchange = _get_ccxt()
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Get OHLCV data for the entire month
        since = int(start_date.timestamp() * 1000)
        days_in_month = (end_date - start_date).days + 1
        
        # Fetch daily candles for the month
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since, limit=days_in_month + 5)
        
        matching_dates = []
        
        for candle in ohlcv:
            candle_timestamp = candle[0] / 1000
            candle_date = datetime.fromtimestamp(candle_timestamp)
            
            # Check if date is in our target month
            if candle_date.year != year or candle_date.month != month:
                continue
            
            date_str = candle_date.strftime('%Y-%m-%d')
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            
            # Calculate tolerance range for close price matching
            price_tolerance = target_price * tolerance
            lower_bound = target_price - price_tolerance
            upper_bound = target_price + price_tolerance
            
            match_type = None
            is_match = False
            
            # Check if target price was within the day's actual price range
            target_exactly_in_range = low_price <= target_price <= high_price
            
            # Check if close price is close to target (within tolerance)
            close_price_close = lower_bound <= close_price <= upper_bound
            
            if transaction_type == 'buy':
                # For buy: we want to buy at target_price or lower
                # Only match if target price was actually in the day's range
                # (we don't want dates where we couldn't actually buy at target price)
                if target_exactly_in_range:
                    is_match = True
                    # Determine match type
                    # 'exact' only if close price is also very close to target
                    if abs(close_price - target_price) / target_price <= tolerance:
                        match_type = 'exact'
                    else:
                        match_type = 'high_low'
            else:  # sell
                # For sell: we want to sell at target_price or higher
                # Only match if target price was actually in the day's range
                # (we don't want dates where we couldn't actually sell at target price)
                if target_exactly_in_range:
                    is_match = True
                    # Determine match type
                    # 'exact' only if close price is also very close to target
                    if abs(close_price - target_price) / target_price <= tolerance:
                        match_type = 'exact'
                    else:
                        match_type = 'high_low'
            
            if is_match:
                # Calculate how close the match is
                if transaction_type == 'buy':
                    price_diff = abs(min(low_price, close_price) - target_price) / target_price
                else:
                    price_diff = abs(max(high_price, close_price) - target_price) / target_price
                
                matching_dates.append({
                    'date': date_str,
                    'close_price': close_price,
                    'high': high_price,
                    'low': low_price,
                    'match_type': match_type,
                    'price_diff_pct': price_diff * 100
                })
        
        if matching_dates:
            df = pd.DataFrame(matching_dates)
            # Sort by how close the price is to target
            df = df.sort_values('price_diff_pct')
            return df
        else:
            return pd.DataFrame(columns=['date', 'close_price', 'high', 'low', 'match_type', 'price_diff_pct'])
            
    except Exception as e:
        print(f"Error finding dates by price for {symbol}: {e}")
        return pd.DataFrame(columns=['date', 'close_price', 'high', 'low', 'match_type', 'price_diff_pct'])