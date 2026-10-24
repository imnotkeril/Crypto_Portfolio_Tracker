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


def _drop_legacy_amount_column(conn, table: str, new_cols: str, create_new_sql: str, select_cols: str):
    """
    Migrate a legacy table that still has an 'amount' column to the new structure.
    Safe: backs up the DB file first, runs in one transaction, and aborts (rolls back,
    old table kept) if any row would be lost. Errors are raised, never swallowed.
    """
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cur.fetchone():
        return
    cur.execute(f"PRAGMA table_info({table})")
    if 'amount' not in [col[1] for col in cur.fetchall()]:
        return

    backup_path = f"{DB_PATH}.pre-migration-{datetime.now():%Y%m%d%H%M%S}.bak"
    backup = sqlite3.connect(backup_path)
    try:
        conn.backup(backup)
    finally:
        backup.close()

    new_table = f"{table}_new"
    try:
        cur.execute("BEGIN")
        cur.execute(f"DROP TABLE IF EXISTS {new_table}")
        cur.execute(create_new_sql)
        cur.execute(f"INSERT OR IGNORE INTO {new_table} ({new_cols}) "
                    f"SELECT {select_cols} FROM {table}")
        old_n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        new_n = cur.execute(f"SELECT COUNT(*) FROM {new_table}").fetchone()[0]
        if new_n != old_n:
            raise RuntimeError(f"Migration of {table} would lose rows ({old_n} -> {new_n}); aborted, backup: {backup_path}")
        cur.execute(f"DROP TABLE {table}")
        cur.execute(f"ALTER TABLE {new_table} RENAME TO {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


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
    _drop_legacy_amount_column(conn, 'funding_rates', 'id, year, month, asset, percentage, created_at', '''
        CREATE TABLE funding_rates_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            asset TEXT NOT NULL,
            percentage REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, month, asset)
        )
    ''', 'id, year, month, asset, COALESCE(percentage, 0), created_at')
    cursor = conn.cursor()

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
    _drop_legacy_amount_column(conn, 'pool_rates', 'id, year, month, apy, created_at', '''
        CREATE TABLE pool_rates_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            apy REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, month)
        )
    ''', 'id, year, month, apy, created_at')
    cursor = conn.cursor()

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
    """Get current portfolio state from transactions (all assets from transactions + USDT)"""
    transactions = get_transactions()
    if len(transactions) == 0:
        return {'USDT': 0.0}

    transactions = transactions.sort_values('date')
    # Build portfolio dynamically: ensure USDT exists, add any asset from transactions
    portfolio = {'USDT': 0.0}

    for _, row in transactions.iterrows():
        asset = row['asset']
        transaction_type = row['type']
        quantity = row['quantity']
        value = row['value']  # Value in USDT

        if asset not in portfolio:
            portfolio[asset] = 0.0

        if transaction_type == 'buy':
            portfolio[asset] += quantity
            if asset != 'USDT':
                if portfolio['USDT'] >= value:
                    portfolio['USDT'] -= value
            # When buying USDT, quantity already added above
        elif transaction_type == 'sell':
            portfolio[asset] -= quantity
            if asset != 'USDT':
                portfolio['USDT'] += value

    return portfolio


def get_portfolio_at_date(date: str) -> Dict[str, float]:
    """
    Get portfolio state at a specific date (all assets from transactions + USDT)
    Args:
        date: Date string in format 'YYYY-MM-DD'
    Returns:
        Dictionary with portfolio quantities
    """
    transactions = get_transactions()
    transactions_before = transactions[transactions['date'] <= date]
    if len(transactions_before) == 0:
        return {'USDT': 0.0}

    portfolio = {'USDT': 0.0}
    for _, row in transactions_before.iterrows():
        asset = row['asset']
        transaction_type = row['type']
        quantity = row['quantity']
        if asset not in portfolio:
            portfolio[asset] = 0.0
        if transaction_type == 'buy':
            portfolio[asset] += quantity
        elif transaction_type == 'sell':
            portfolio[asset] -= quantity

    return portfolio
