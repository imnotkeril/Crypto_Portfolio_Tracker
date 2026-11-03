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


# ---- T19: stored rows, schema, holdings inconsistency, migration edge cases ----------------------

def test_stored_row_has_exactly_the_added_values(db):
    # AC1.1
    db.add_transaction("2024-01-02", "BTC", "buy", 0.1, 40000, 4000)
    df = db.get_transactions()
    assert len(df) == 1
    row = df.iloc[0]
    assert row["date"] == "2024-01-02" and row["asset"] == "BTC" and row["type"] == "buy"
    assert row["quantity"] == pytest.approx(0.1)
    assert row["price"] == pytest.approx(40000)
    assert row["value"] == pytest.approx(4000)
    assert int(row["id"]) == 1 and row["created_at"]


def test_transactions_are_ordered_by_date_then_id(db):
    db.add_transaction("2024-01-03", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-01", "ETH", "buy", 1, 10, 10)
    db.add_transaction("2024-01-01", "SOL", "buy", 1, 5, 5)
    assert db.get_transactions()["asset"].tolist() == ["ETH", "SOL", "BTC"]


def test_injection_shaped_asset_is_stored_verbatim_and_tables_survive(db):
    evil = "BTC'); DROP TABLE transactions;--"
    db.add_transaction("2024-01-01", evil, "buy", 1, 1, 1)
    assert db.get_transactions().iloc[0]["asset"] == evil
    assert len(db.get_transactions()) == 1


def _schema(path):
    conn = sqlite3.connect(path)
    try:
        tables = sorted(r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        sql = sorted(conn.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        return tables, sql
    finally:
        conn.close()


def test_init_creates_four_tables_and_second_init_changes_nothing(db):
    # AC12.1
    path = db.DB_PATH
    tables, sql = _schema(path)
    assert tables == ["funding_rates", "pool_rates", "portfolio_snapshots", "transactions"]
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_funding_rate(2024, 1, "BTC", 5.0)
    db.add_pool_rate(2024, 1, 5.0)
    before = (db.get_transactions().to_dict("records"), db.get_funding_rates().to_dict("records"),
              db.get_pool_rates().to_dict("records"))
    db.init_database()
    assert _schema(path) == (tables, sql)
    after = (db.get_transactions().to_dict("records"), db.get_funding_rates().to_dict("records"),
             db.get_pool_rates().to_dict("records"))
    assert after == before


def test_delete_unknown_ids_is_a_noop(db):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_funding_rate(2024, 1, "BTC", 5.0)
    db.add_pool_rate(2024, 1, 5.0)
    db.delete_transaction(999)
    db.delete_funding_rate(999)
    db.delete_pool_rate(999)
    assert len(db.get_transactions()) == 1 and len(db.get_funding_rates()) == 1 and len(db.get_pool_rates()) == 1


def test_delete_funding_and_pool_rate_remove_only_that_row(db):
    # AC5.4 (db layer)
    db.add_funding_rate(2024, 1, "BTC", 5.0)
    db.add_funding_rate(2024, 1, "ETH", 6.0)
    db.add_pool_rate(2024, 1, 5.0)
    db.add_pool_rate(2024, 2, 6.0)
    db.delete_funding_rate(int(db.get_funding_rates().iloc[0]["id"]))
    db.delete_pool_rate(int(db.get_pool_rates().iloc[0]["id"]))
    assert db.get_funding_rates()["asset"].tolist() == ["ETH"]
    assert db.get_pool_rates()["month"].tolist() == [2]


def test_sell_more_than_held_goes_negative_characterizes_known_debt_D11(db):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-02", "BTC", "sell", 3, 100, 300)
    assert db.get_current_portfolio()["BTC"] == pytest.approx(-2.0)


def test_current_and_at_date_usdt_differ_after_crypto_buy_characterizes_known_debt_D4(db):
    db.add_transaction("2024-01-01", "USDT", "buy", 5000, 1, 5000)
    db.add_transaction("2024-01-02", "BTC", "buy", 0.1, 40000, 4000)
    current = db.get_current_portfolio()
    at_date = db.get_portfolio_at_date("2024-01-31")
    assert current["BTC"] == pytest.approx(at_date["BTC"]) == pytest.approx(0.1)
    assert current["USDT"] == pytest.approx(1000.0)   # buy deducts value from USDT
    assert at_date["USDT"] == pytest.approx(5000.0)   # at-date ignores the USDT leg of crypto trades


def _legacy_pool_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE pool_rates (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, month INTEGER, "
                 "amount REAL, apy REAL, created_at TEXT, UNIQUE(year, month))")
    conn.executemany("INSERT INTO pool_rates (year, month, amount, apy, created_at) VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def _columns(path, table):
    conn = sqlite3.connect(path)
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


def test_legacy_pool_rates_with_amount_are_migrated(tmp_path, monkeypatch):
    # AC12.5
    from utils import database
    path = str(tmp_path / "legacy_pool.db")
    _legacy_pool_db(path, [(2024, 1, 100, 5.0, "2024-01-01"), (2024, 2, 200, 6.5, "2024-02-01")])
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_database()
    df = database.get_pool_rates()
    assert "amount" not in df.columns
    assert df[["year", "month", "apy"]].values.tolist() == [[2024, 1, 5.0], [2024, 2, 6.5]]
    assert len(list(tmp_path.glob("legacy_pool.db.pre-migration-*.bak"))) >= 1
    # migrated table still enforces UNIQUE(year, month) via upsert
    database.add_pool_rate(2024, 1, 9.0)
    assert len(database.get_pool_rates()) == 2


def test_migration_is_idempotent_second_init_makes_no_new_backup(tmp_path, monkeypatch):
    from utils import database
    path = str(tmp_path / "legacy.db")
    _legacy_db(path)
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_database()
    backups = sorted(p.name for p in tmp_path.glob("legacy.db.pre-migration-*.bak"))
    database.init_database()
    assert sorted(p.name for p in tmp_path.glob("legacy.db.pre-migration-*.bak")) == backups
    assert len(database.get_funding_rates()) == 2


def test_migration_that_would_lose_rows_raises_and_keeps_old_table(tmp_path, monkeypatch):
    # AC12.4: legacy table without a UNIQUE constraint holds two rows with the same (year, month, asset)
    from utils import database
    path = str(tmp_path / "dup.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE funding_rates (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, month INTEGER, "
                 "asset TEXT, amount REAL, percentage REAL, created_at TEXT)")
    conn.execute("INSERT INTO funding_rates (year, month, asset, amount, percentage, created_at) "
                 "VALUES (2024, 1, 'BTC', 10, 5, '2024-01-01')")
    conn.execute("INSERT INTO funding_rates (year, month, asset, amount, percentage, created_at) "
                 "VALUES (2024, 1, 'BTC', 11, 6, '2024-01-02')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", path)
    with pytest.raises(RuntimeError, match="would lose rows"):
        database.init_database()
    assert "amount" in _columns(path, "funding_rates")
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM funding_rates").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='funding_rates_new'").fetchone()[0] == 0
    conn.close()
    assert list(tmp_path.glob("dup.db.pre-migration-*.bak"))  # backup was made before the attempt


def test_legacy_pool_with_null_apy_is_caught_by_row_count_guard(tmp_path, monkeypatch):
    from utils import database
    path = str(tmp_path / "nullapy.db")
    _legacy_pool_db(path, [(2024, 1, 100, 5.0, "2024-01-01"), (2024, 2, 200, None, "2024-02-01")])
    monkeypatch.setattr(database, "DB_PATH", path)
    # INSERT OR IGNORE silently skips the NOT NULL violation; the row-count guard must catch it
    with pytest.raises(RuntimeError, match="would lose rows"):
        database.init_database()
    assert "amount" in _columns(path, "pool_rates")
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM pool_rates").fetchone()[0] == 2
    conn.close()
