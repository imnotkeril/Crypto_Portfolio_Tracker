"""
Script to migrate database from old structure to new
Removes 'amount' field from funding_rates and pool_rates
"""
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.database import DB_PATH

def migrate_database():
    """Migrate database structure"""
    if not os.path.exists(DB_PATH):
        print("Database doesn't exist, no migration needed")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check funding_rates structure
        cursor.execute("PRAGMA table_info(funding_rates)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'amount' in columns:
            print("Migrating funding_rates table...")
            # Create new table
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
            # Copy data (use percentage, default to 0 if null)
            cursor.execute('''
                INSERT OR IGNORE INTO funding_rates_new (id, year, month, asset, percentage, created_at)
                SELECT id, year, month, asset, COALESCE(percentage, 0), created_at 
                FROM funding_rates
            ''')
            # Drop old table
            cursor.execute("DROP TABLE funding_rates")
            # Rename new table
            cursor.execute("ALTER TABLE funding_rates_new RENAME TO funding_rates")
            print("✅ funding_rates migrated")
        else:
            print("✅ funding_rates already migrated")
        
        # Check pool_rates structure
        cursor.execute("PRAGMA table_info(pool_rates)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'amount' in columns:
            print("Migrating pool_rates table...")
            # Create new table
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
            # Copy data
            cursor.execute('''
                INSERT OR IGNORE INTO pool_rates_new (id, year, month, apy, created_at)
                SELECT id, year, month, apy, created_at 
                FROM pool_rates
            ''')
            # Drop old table
            cursor.execute("DROP TABLE pool_rates")
            # Rename new table
            cursor.execute("ALTER TABLE pool_rates_new RENAME TO pool_rates")
            print("✅ pool_rates migrated")
        else:
            print("✅ pool_rates already migrated")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
