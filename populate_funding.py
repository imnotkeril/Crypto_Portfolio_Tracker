"""
Auto-populate historical Coin-M funding data
Automatically fills database with estimated funding rates
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_database, add_funding_rate


def auto_populate_funding():
    """Automatically populate funding data with estimated values"""
    init_database()
    
    # Estimated annual funding rates (5-10% as mentioned by user)
    funding_rates = {
        2022: {'BTC': 7.5, 'ETH': 8.0},
        2023: {'BTC': 6.5, 'ETH': 7.0},
        2024: {'BTC': 5.5, 'ETH': 6.0},
        2025: {'BTC': 5.0, 'ETH': 5.5},
    }
    
    print("Populating Coin-M funding data...")
    count = 0
    
    for year in range(2022, 2026):
        for month in range(1, 13):
            if year == 2025 and month > datetime.now().month:
                break
            
            for asset in ['BTC', 'ETH']:
                annual_rate = funding_rates.get(year, {}).get(asset, 6.0)
                # Add funding rate (percentage only, amount calculated automatically)
                add_funding_rate(year, month, asset, annual_rate)
                count += 1
                if count % 10 == 0:
                    print(f"Added {count} records...")
    
    print(f"\n✅ Added {count} funding records!")
    print("Data populated for period from 2022 to current month.")


if __name__ == "__main__":
    auto_populate_funding()
