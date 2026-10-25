import sqlite3

import pytest


def test_empty_portfolio(db):
    assert db.get_current_portfolio() == {"USDT": 0.0}


def test_buy_sell_flow(db):
    db.add_transaction("2024-01-01", "USDT", "buy", 5000, 1, 5000)
    db.add_transaction("2024-01-02", "BTC", "buy", 0.1, 40000, 4000)
    db.add_transaction("2024-01-03", "BTC", "sell", 0.04, 50000, 2000)
    p = db.get_current_portfolio()
    assert p["BTC"] == pytest.approx(0.06)
    assert p["USDT"] == pytest.approx(5000 - 4000 + 2000)


def test_buy_without_enough_usdt_does_not_go_negative(db):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 40000, 40000)
    p = db.get_current_portfolio()
    assert p["BTC"] == 1
    assert p["USDT"] == 0.0


def test_dynamic_assets(db):
    db.add_transaction("2024-01-01", "SOL", "buy", 10, 100, 1000)
    assert "SOL" in db.get_current_portfolio()


def test_portfolio_at_date_ignores_future(db):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-03-01", "BTC", "buy", 2, 100, 200)
    assert db.get_portfolio_at_date("2024-02-01")["BTC"] == 1
    assert db.get_portfolio_at_date("2023-12-31") == {"USDT": 0.0}


def test_delete_transaction(db):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    tid = int(db.get_transactions().iloc[0]["id"])
    db.delete_transaction(tid)
    assert len(db.get_transactions()) == 0


def test_rates_upsert(db):
    db.add_funding_rate(2024, 1, "BTC", 5.0)
    db.add_funding_rate(2024, 1, "BTC", 7.0)
    df = db.get_funding_rates()
    assert len(df) == 1 and df.iloc[0]["percentage"] == 7.0
    db.add_pool_rate(2024, 1, 5.0)
    db.add_pool_rate(2024, 1, 6.0)
    assert len(db.get_pool_rates()) == 1


def _legacy_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE funding_rates (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, month INTEGER, "
                 "asset TEXT, amount REAL, percentage REAL, created_at TEXT, UNIQUE(year, month, asset))")
    conn.execute("INSERT INTO funding_rates (year, month, asset, amount, percentage, created_at) "
                 "VALUES (2024, 1, 'BTC', 10, 5, '2024-01-01')")
    conn.execute("INSERT INTO funding_rates (year, month, asset, amount, percentage, created_at) "
                 "VALUES (2024, 2, 'BTC', 11, NULL, '2024-02-01')")
    conn.commit()
    conn.close()


def test_legacy_migration_keeps_rows_and_makes_backup(tmp_path, monkeypatch):
    from utils import database
    path = str(tmp_path / "legacy.db")
    _legacy_db(path)
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_database()
    df = database.get_funding_rates()
    assert len(df) == 2 and "amount" not in df.columns
    assert df["percentage"].tolist() == [5.0, 0.0]
    assert list(tmp_path.glob("legacy.db.pre-migration-*.bak"))


def test_migration_failure_is_raised_and_old_table_kept(tmp_path, monkeypatch):
    from utils import database
    path = str(tmp_path / "legacy.db")
    _legacy_db(path)
    monkeypatch.setattr(database, "DB_PATH", path)
    conn = database.get_connection()
    with pytest.raises(sqlite3.Error):
        database._drop_legacy_amount_column(
            conn, "funding_rates", "id, year", "CREATE TABLE funding_rates_new (id, bad bad bad", "id, year")
    conn.close()
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM funding_rates").fetchone()[0] == 2
    conn.close()
