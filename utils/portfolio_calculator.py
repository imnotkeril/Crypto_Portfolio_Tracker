"""
Portfolio calculator module
Calculates portfolio value over time considering transactions, funding, and pools
Supports any assets from transactions (Binance USDT pairs).
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_transactions, get_funding_rates, get_pool_rates
from utils.price_fetcher import get_price, get_price_range


def calculate_portfolio_history(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame:
    """
    Calculate portfolio value history considering:
    - Transactions (buy/sell)
    - Funding rates (Coin-M) - calculated automatically based on real positions
    - Pool rates (USDT pools) - calculated automatically based on real USDT in pool
    - Auto pool logic (sell -> pool, buy -> from pool)
    
    Args:
        start_date: Start date for calculation
        end_date: End date (default: today)
    Returns:
        DataFrame with portfolio values over time
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Get all data
    transactions = get_transactions()
    funding_rates = get_funding_rates()
    pool_rates = get_pool_rates()

    # Portfolio: dynamic assets from transactions, always include USDT
    portfolio = {'USDT': 0.0}
    pool_balance_total = 0.0
    daily_pool_balances = {}
    daily_positions = {}  # {date_str: {asset: qty, ...}}
    monthly_funding_income = {}  # {year-month: amount}
    monthly_pool_income = {}  # {year-month: amount}
    
    # Create date range
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = pd.date_range(start, end, freq='D')
    
    portfolio_history = []
    
    # Process transactions chronologically
    if len(transactions) > 0:
        transactions_sorted = transactions.sort_values('date')
        
        current_month = None
        month_start_date = None
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            year_month = date.strftime('%Y-%m')
            year = date.year
            month = date.month
            
            # New month - calculate funding and pool income for previous month
            if current_month is not None and current_month != year_month:
                prev_month = current_month
                month_start = datetime.strptime(f"{prev_month}-01", '%Y-%m-%d')
                month_end = month_start + timedelta(days=32)
                month_end = month_end.replace(day=1) - timedelta(days=1)

                # Average position per asset over the month
                all_assets_in_month = set()
                for day in pd.date_range(month_start, month_end, freq='D'):
                    day_str = day.strftime('%Y-%m-%d')
                    if day_str in daily_positions:
                        all_assets_in_month.update(daily_positions[day_str].keys())
                avg_positions = {}
                for asset in all_assets_in_month:
                    qty_list = [
                        daily_positions[day.strftime('%Y-%m-%d')].get(asset, 0.0)
                        for day in pd.date_range(month_start, month_end, freq='D')
                        if day.strftime('%Y-%m-%d') in daily_positions
                    ]
                    avg_positions[asset] = np.mean(qty_list) if qty_list else 0.0

                prev_funding_rates = funding_rates[
                    (funding_rates['year'] == int(prev_month.split('-')[0])) &
                    (funding_rates['month'] == int(prev_month.split('-')[1]))
                ]
                funding_income = 0.0
                for _, fund_row in prev_funding_rates.iterrows():
                    asset = fund_row['asset']
                    percentage = fund_row['percentage']
                    position_qty = avg_positions.get(asset, 0.0)
                    if position_qty > 0:
                        mid_month = month_start + timedelta(days=15)
                        mid_month_str = mid_month.strftime('%Y-%m-%d')
                        price = get_price(asset, mid_month_str)
                        if price:
                            position_value = position_qty * price
                            monthly_funding = position_value * (percentage / 100) / 12
                            funding_income += monthly_funding
                monthly_funding_income[prev_month] = funding_income
                
                # Calculate pool income for previous month using average pool balance in that month
                month_pool_balances = []
                for day in pd.date_range(month_start, month_end, freq='D'):
                    day_str = day.strftime('%Y-%m-%d')
                    if day_str in daily_pool_balances:
                        month_pool_balances.append(daily_pool_balances[day_str])

                avg_pool_balance = np.mean(month_pool_balances) if month_pool_balances else 0.0
                prev_pool_rate = pool_rates[
                    (pool_rates['year'] == int(prev_month.split('-')[0])) &
                    (pool_rates['month'] == int(prev_month.split('-')[1]))
                ]
                
                pool_income = 0.0
                if len(prev_pool_rate) > 0 and avg_pool_balance > 0:
                    apy = prev_pool_rate.iloc[0]['apy']
                    # Monthly pool income = APY / 12
                    pool_income = avg_pool_balance * (apy / 100) / 12
                    monthly_pool_income[prev_month] = pool_income
                    portfolio['USDT'] += pool_income
                
                # Add funding income to USDT
                portfolio['USDT'] += funding_income
                
                # Update all portfolio history entries for previous month with calculated income
                # This ensures income is reflected in all days of the month
                # We need to update entries that were already added for prev_month
                for i, entry in enumerate(portfolio_history):
                    try:
                        entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                        entry_month = entry_date.strftime('%Y-%m')
                        if entry_month == prev_month:
                            portfolio_history[i]['funding_income'] = funding_income
                            portfolio_history[i]['pool_income'] = pool_income
                    except (ValueError, KeyError):
                        # Skip invalid entries
                        pass
            
            # Initialize month tracking
            if current_month != year_month:
                current_month = year_month
                month_start_date = date
            
            # Process transactions for this date
            day_transactions = transactions_sorted[transactions_sorted['date'] == date_str]

            for _, tx in day_transactions.iterrows():
                asset = tx['asset']
                tx_type = tx['type']
                quantity = tx['quantity']
                value = tx['value']
                if asset not in portfolio:
                    portfolio[asset] = 0.0
                if tx_type == 'buy':
                    if asset == 'USDT':
                        if pool_balance_total > 0:
                            reduce_amount = min(value, pool_balance_total)
                            pool_balance_total -= reduce_amount
                        portfolio[asset] += quantity
                    else:
                        use_from_pool = min(value, pool_balance_total)
                        pool_balance_total -= use_from_pool
                        remaining_value = value - use_from_pool
                        if remaining_value > 0 and portfolio['USDT'] >= remaining_value:
                            portfolio['USDT'] -= remaining_value
                        portfolio[asset] += quantity
                elif tx_type == 'sell':
                    if asset == 'USDT':
                        pool_balance_total += value
                        portfolio[asset] -= quantity
                    else:
                        pool_balance_total += value
                        portfolio[asset] -= quantity

            daily_positions[date_str] = dict(portfolio)
            daily_pool_balances[date_str] = pool_balance_total

            should_calculate = len(day_transactions) > 0 or date == dates[-1] or date.day == 1

            if should_calculate:
                try:
                    assets_value = {}
                    total_value = 0.0
                    for ast, qty in portfolio.items():
                        if ast == 'USDT':
                            assets_value['USDT'] = qty
                            total_value += qty
                        else:
                            price = get_price(ast, date_str)
                            if price is not None:
                                val = qty * price
                                assets_value[ast] = val
                                total_value += val
                    if assets_value:
                        pool_balance_current = pool_balance_total
                        funding_income_current = monthly_funding_income.get(current_month, 0.0)
                        pool_income_current = monthly_pool_income.get(current_month, 0.0)
                        entry = {
                            'date': date_str,
                            'assets_value': json.dumps(assets_value),
                            'pool_balance': pool_balance_current,
                            'total_value': total_value + pool_balance_current,
                            'funding_income': funding_income_current,
                            'pool_income': pool_income_current
                        }
                        # Backward compat columns for analytics
                        entry['BTC_value'] = assets_value.get('BTC', 0.0)
                        entry['ETH_value'] = assets_value.get('ETH', 0.0)
                        entry['USDT_value'] = assets_value.get('USDT', 0.0)
                        portfolio_history.append(entry)
                except Exception:
                    pass
        
        # Calculate funding and pool for last month
        if current_month:
            month_start = datetime.strptime(f"{current_month}-01", '%Y-%m-%d')
            month_end = month_start + timedelta(days=32)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            all_assets_in_month = set()
            for day in pd.date_range(month_start, month_end, freq='D'):
                day_str = day.strftime('%Y-%m-%d')
                if day_str in daily_positions:
                    all_assets_in_month.update(daily_positions[day_str].keys())
            avg_positions = {}
            for asset in all_assets_in_month:
                qty_list = [
                    daily_positions[day.strftime('%Y-%m-%d')].get(asset, 0.0)
                    for day in pd.date_range(month_start, month_end, freq='D')
                    if day.strftime('%Y-%m-%d') in daily_positions
                ]
                avg_positions[asset] = np.mean(qty_list) if qty_list else 0.0
            prev_funding_rates = funding_rates[
                (funding_rates['year'] == int(current_month.split('-')[0])) &
                (funding_rates['month'] == int(current_month.split('-')[1]))
            ]
            funding_income = 0.0
            for _, fund_row in prev_funding_rates.iterrows():
                asset = fund_row['asset']
                percentage = fund_row['percentage']
                position_qty = avg_positions.get(asset, 0.0)
                if position_qty > 0:
                    mid_month = month_start + timedelta(days=15)
                    mid_month_str = mid_month.strftime('%Y-%m-%d')
                    price = get_price(asset, mid_month_str)
                    if price:
                        position_value = position_qty * price
                        monthly_funding = position_value * (percentage / 100) / 12
                        funding_income += monthly_funding
            monthly_funding_income[current_month] = funding_income
            
            # Calculate pool income for last month using average pool balance in that month
            month_pool_balances = []
            for day in pd.date_range(month_start, month_end, freq='D'):
                day_str = day.strftime('%Y-%m-%d')
                if day_str in daily_pool_balances:
                    month_pool_balances.append(daily_pool_balances[day_str])

            avg_pool_balance = np.mean(month_pool_balances) if month_pool_balances else 0.0
            prev_pool_rate = pool_rates[
                (pool_rates['year'] == int(current_month.split('-')[0])) &
                (pool_rates['month'] == int(current_month.split('-')[1]))
            ]
            
            pool_income = 0.0
            if len(prev_pool_rate) > 0 and avg_pool_balance > 0:
                apy = prev_pool_rate.iloc[0]['apy']
                pool_income = avg_pool_balance * (apy / 100) / 12
                monthly_pool_income[current_month] = pool_income
            
            # Update all portfolio history entries for last month with calculated income
            for i, entry in enumerate(portfolio_history):
                try:
                    entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                    entry_month = entry_date.strftime('%Y-%m')
                    if entry_month == current_month:
                        portfolio_history[i]['funding_income'] = funding_income
                        portfolio_history[i]['pool_income'] = pool_income
                except (ValueError, KeyError):
                    # Skip invalid entries
                    pass
            
            # (Removed duplicate update loop for last month)
    
    if len(portfolio_history) == 0:
        # Return empty dataframe with correct structure
        return pd.DataFrame(columns=['date', 'total_value'])
    
    df = pd.DataFrame(portfolio_history)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    return df


def get_transactions_with_prices() -> pd.DataFrame:
    """Get transactions with current prices for display"""
    transactions = get_transactions()
    
    if len(transactions) == 0:
        return transactions
    
    result = []
    for _, tx in transactions.iterrows():
        asset = tx['asset']
        date = tx['date']
        price = tx['price']
        
        # Get current price for comparison
        from utils.price_fetcher import get_current_price
        current_price = get_current_price(f"{asset}/USDT") if asset != 'USDT' else 1.0
        
        result.append({
            'date': date,
            'asset': asset,
            'type': tx['type'],
            'quantity': tx['quantity'],
            'price': price,
            'value': tx['value'],
            'current_price': current_price,
            'pnl_pct': ((current_price - price) / price * 100) if asset != 'USDT' and price > 0 else 0
        })
    
    return pd.DataFrame(result)
