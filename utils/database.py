"""
Database module for portfolio tracker
Handles SQLite database operations
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'portfolio.db')


def get_connection():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_database():
    """Initialize database with all required tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            asset TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            value REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Funding rates table (Coin-M funding) - store only percentage, amount calculated automatically
    # Check if old structure exists and migrate
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='funding_rates'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(funding_rates)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'amount' in columns:
                # Old structure exists, migrate
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS funding_rates_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year INTEGER NOT NULL,
                        month INTEGER NOT NULL,
                        asset TEXT NOT NULL,
                        percentage REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(year, month, asset)
                    )
                ''')
                cursor.execute('''
                    INSERT OR IGNORE INTO funding_rates_new (id, year, month, asset, percentage, created_at)
                    SELECT id, year, month, asset, COALESCE(percentage, 0), created_at 
                    FROM funding_rates
                ''')
                cursor.execute("DROP TABLE funding_rates")
                cursor.execute("ALTER TABLE funding_rates_new RENAME TO funding_rates")
                conn.commit()
    except Exception as e:
        # Table doesn't exist or error, create new
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funding_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            asset TEXT NOT NULL,
            percentage REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, month, asset)
        )
    ''')
    
    # Pool rates table (USDT pools) - store only APY, amount calculated automatically
    # Check if old structure exists and migrate
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pool_rates'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(pool_rates)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'amount' in columns:
                # Old structure exists, migrate
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pool_rates_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year INTEGER NOT NULL,
                        month INTEGER NOT NULL,
                        apy REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(year, month)
                    )
                ''')
                cursor.execute('''
                    INSERT OR IGNORE INTO pool_rates_new (id, year, month, apy, created_at)
                    SELECT id, year, month, apy, created_at 
                    FROM pool_rates
                ''')
                cursor.execute("DROP TABLE pool_rates")
                cursor.execute("ALTER TABLE pool_rates_new RENAME TO pool_rates")
                conn.commit()
    except Exception as e:
        # Table doesn't exist or error, create new
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pool_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            apy REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, month)
        )
    ''')
    
    # Portfolio snapshots for metrics calculation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            btc_quantity REAL DEFAULT 0,
            eth_quantity REAL DEFAULT 0,
            usdt_quantity REAL DEFAULT 0,
            btc_value REAL DEFAULT 0,
            eth_value REAL DEFAULT 0,
            usdt_value REAL DEFAULT 0,
            total_value REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date)
        )
    ''')
    
    conn.commit()
    conn.close()


def add_transaction(date: str, asset: str, transaction_type: str, quantity: float, price: float, value: float):
    """Add a new transaction"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (date, asset, type, quantity, price, value)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, asset, transaction_type, quantity, price, value))
    conn.commit()
    conn.close()


def get_transactions() -> pd.DataFrame:
    """Get all transactions"""
    conn = get_connection()
    df = pd.read_sql_query('SELECT * FROM transactions ORDER BY date, id', conn)
    conn.close()
    return df


def delete_transaction(transaction_id: int):
    """Delete a transaction by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()


def add_funding_rate(year: int, month: int, asset: str, percentage: float):
    """Add or update funding rate (only percentage, amount calculated automatically)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO funding_rates (year, month, asset, percentage)
        VALUES (?, ?, ?, ?)
    ''', (year, month, asset, percentage))
    conn.commit()
    conn.close()


def get_funding_rates() -> pd.DataFrame:
    """Get all funding rates"""
    conn = get_connection()
    df = pd.read_sql_query('SELECT * FROM funding_rates ORDER BY year, month, asset', conn)
    conn.close()
    return df


def delete_funding_rate(funding_id: int):
    """Delete a funding rate by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM funding_rates WHERE id = ?', (funding_id,))
    conn.commit()
    conn.close()


def delete_pool_rate(pool_id: int):
    """Delete a pool rate by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pool_rates WHERE id = ?', (pool_id,))
    conn.commit()
    conn.close()


def add_pool_rate(year: int, month: int, apy: float):
    """Add or update pool rate (only APY, amount calculated automatically)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO pool_rates (year, month, apy)
        VALUES (?, ?, ?)
    ''', (year, month, apy))
    conn.commit()
    conn.close()


def get_pool_rates() -> pd.DataFrame:
    """Get all pool rates"""
    conn = get_connection()
    df = pd.read_sql_query('SELECT * FROM pool_rates ORDER BY year, month', conn)
    conn.close()
    return df


def save_portfolio_snapshot(date: str, btc_qty: float, eth_qty: float, usdt_qty: float,
                           btc_val: float, eth_val: float, usdt_val: float, total_val: float):
    """Save portfolio snapshot"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO portfolio_snapshots 
        (date, btc_quantity, eth_quantity, usdt_quantity, btc_value, eth_value, usdt_value, total_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, btc_qty, eth_qty, usdt_qty, btc_val, eth_val, usdt_val, total_val))
    conn.commit()
    conn.close()


def get_portfolio_snapshots() -> pd.DataFrame:
    """Get all portfolio snapshots"""
    conn = get_connection()
    df = pd.read_sql_query('SELECT * FROM portfolio_snapshots ORDER BY date', conn)
    conn.close()
    return df


def get_current_portfolio() -> Dict[str, float]:
    """Get current portfolio state from transactions"""
    transactions = get_transactions()
    
    # Sort by date to process chronologically
    transactions = transactions.sort_values('date')
    
    portfolio = {'BTC': 0.0, 'ETH': 0.0, 'USDT': 0.0}
    
    for _, row in transactions.iterrows():
        asset = row['asset']
        transaction_type = row['type']
        quantity = row['quantity']
        value = row['value']  # Value in USDT
        
        if asset in portfolio:
            if transaction_type == 'buy':
                portfolio[asset] += quantity
                # When buying crypto, reduce USDT only if we have enough
                # If not enough, consider it bought with external funds
                if asset != 'USDT':
                    if portfolio['USDT'] >= value:
                        portfolio['USDT'] -= value
                    # If not enough USDT, don't go negative (external funding)
                # When buying USDT, it's already added above
            elif transaction_type == 'sell':
                portfolio[asset] -= quantity
                # When selling crypto, add USDT
                if asset != 'USDT':
                    portfolio['USDT'] += value
                # When selling USDT, it's already subtracted above
    
    return portfolio


def get_portfolio_at_date(date: str) -> Dict[str, float]:
    """
    Get portfolio state at a specific date
    Args:
        date: Date string in format 'YYYY-MM-DD'
    Returns:
        Dictionary with portfolio quantities
    """
    transactions = get_transactions()
    
    portfolio = {'BTC': 0.0, 'ETH': 0.0, 'USDT': 0.0}
    
    # Filter transactions up to and including the date
    transactions_before = transactions[transactions['date'] <= date]
    
    for _, row in transactions_before.iterrows():
        asset = row['asset']
        transaction_type = row['type']
        quantity = row['quantity']
        
        if asset in portfolio:
            if transaction_type == 'buy':
                portfolio[asset] += quantity
            elif transaction_type == 'sell':
                portfolio[asset] -= quantity
    
    return portfolio
