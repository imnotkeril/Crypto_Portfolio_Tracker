import json
import pandas as pd
import pytest

from utils import portfolio_calculator as pc


@pytest.fixture
def const_price(monkeypatch):
    monkeypatch.setattr(pc, "get_price", lambda asset, date: 100.0)


@pytest.fixture
def calc(db, monkeypatch):
    for name in ("get_transactions", "get_funding_rates", "get_pool_rates"):
        monkeypatch.setattr(pc, name, getattr(db, name))
    return pc


def test_no_transactions_returns_frame(calc, const_price):
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-10")
    assert isinstance(h, pd.DataFrame)


def test_total_value_conserved_on_buy_at_market(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 5000, 1, 5000)
    db.add_transaction("2024-01-05", "BTC", "buy", 0.1, 100, 10)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-31")
    assert len(h) > 0
    assert h["total_value"].iloc[-1] == pytest.approx(5000.0)
    assert h["BTC_value"].iloc[-1] == pytest.approx(10.0)


def test_pool_income_added_after_month_end(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 1200, 1, 1200)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-03", "BTC", "sell", 1, 100, 100)  # sale proceeds go to pool
    db.add_pool_rate(2024, 1, 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-02-10")
    assert h["total_value"].iloc[-1] > 1200.0


def test_usdt_deposit_does_not_erase_pool_balance(db, calc, const_price):
    # R-02: 1000 USDT, BTC round trip @100 (proceeds sit in the pool), then +500 deposit.
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-03", "BTC", "sell", 1, 100, 100)
    db.add_transaction("2024-01-04", "USDT", "buy", 500, 1, 500)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-10")
    assert h["total_value"].iloc[-1] == pytest.approx(1500.0)


# ---- T20: history income math and edge cases ---------------------------------------------------------

def _row(h, day):
    return h.loc[pd.Timestamp(day)]


def test_no_transactions_returns_empty_frame_with_total_value_column(calc, const_price):
    # AC7.1
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-10")
    assert len(h) == 0
    assert list(h.columns) == ["date", "total_value"]


def test_history_columns_and_index(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-05")
    assert h.index.name == "date" and isinstance(h.index, pd.DatetimeIndex)
    for col in ("assets_value", "pool_balance", "total_value", "funding_income", "pool_income",
                "BTC_value", "ETH_value", "USDT_value"):
        assert col in h.columns
    assert h["total_value"].iloc[0] == pytest.approx(1000.0)


def test_funding_income_for_average_position(db, calc, const_price):
    # AC7.4: avg BTC position 1 in January, price 100, 12 % -> 1 * 100 * 0.12 / 12 = 1.0, credited to USDT
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_funding_rate(2024, 1, "BTC", 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-02-10")
    assert _row(h, "2024-01-01")["funding_income"] == pytest.approx(1.0)
    assert _row(h, "2024-02-01")["USDT_value"] == pytest.approx(1.0)
    assert _row(h, "2024-02-10")["USDT_value"] == pytest.approx(1.0)


def test_funding_income_uses_time_weighted_average_position(db, calc, const_price):
    # 1 BTC held days 1-16 of January (16 days), 3 BTC from day 17 (15 days): avg = (16 + 45) / 31
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-17", "BTC", "buy", 2, 100, 200)
    db.add_funding_rate(2024, 1, "BTC", 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-02-01")
    expected = (16 * 1 + 15 * 3) / 31 * 100 * 0.12 / 12
    assert _row(h, "2024-01-01")["funding_income"] == pytest.approx(expected)


def test_funding_rate_without_position_pays_nothing(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_funding_rate(2024, 1, "BTC", 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-02-10")
    assert (h["funding_income"] == 0).all()
    assert _row(h, "2024-02-10")["total_value"] == pytest.approx(1000.0)


def test_buy_draws_from_pool_first_and_leaves_usdt_untouched(db, calc, const_price):
    # AC7.5: pool 500 (sale proceeds), buy worth 300 -> pool 200, USDT unchanged
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 5, 100, 500)    # USDT 1000 -> 500
    db.add_transaction("2024-01-03", "BTC", "sell", 5, 100, 500)   # pool 0 -> 500
    h3 = calc.calculate_portfolio_history("2024-01-01", "2024-01-03")
    assert _row(h3, "2024-01-03")["pool_balance"] == pytest.approx(500.0)
    db.add_transaction("2024-01-04", "ETH", "buy", 3, 100, 300)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-04")
    last = _row(h, "2024-01-04")
    assert last["pool_balance"] == pytest.approx(200.0)
    assert last["USDT_value"] == pytest.approx(500.0)
    assert last["total_value"] == pytest.approx(1000.0)  # 500 USDT + 200 pool + 300 ETH


def test_buy_larger_than_pool_takes_the_rest_from_usdt(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)    # USDT 900
    db.add_transaction("2024-01-03", "BTC", "sell", 1, 100, 100)   # pool 100
    db.add_transaction("2024-01-04", "ETH", "buy", 4, 100, 400)    # pool 100 + USDT 300
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-04")
    last = _row(h, "2024-01-04")
    assert last["pool_balance"] == pytest.approx(0.0)
    assert last["USDT_value"] == pytest.approx(600.0)


def test_usdt_deposit_while_pool_holds_proceeds_keeps_pool_and_adds_full_deposit(db, calc, const_price):
    # R-02 toy, component view
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-03", "BTC", "sell", 1, 100, 100)
    db.add_transaction("2024-01-04", "USDT", "buy", 500, 1, 500)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-10")
    last = h.iloc[-1]
    assert last["pool_balance"] == pytest.approx(100.0)
    assert last["USDT_value"] == pytest.approx(1400.0)
    assert last["total_value"] == pytest.approx(1500.0)


def test_asset_without_price_is_excluded_from_total_characterizes_known_debt_D9(db, monkeypatch, calc):
    # AC7.6
    monkeypatch.setattr(pc, "get_price", lambda asset, date: None if asset == "ETH" else 100.0)
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-02", "ETH", "buy", 2, 100, 200)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-05")
    last = h.iloc[-1]
    assets = json.loads(last["assets_value"])
    assert "ETH" not in assets and assets["BTC"] == pytest.approx(100.0)
    assert last["ETH_value"] == 0.0
    # 1000 USDT - 100 - 200 = 700 USDT + 100 BTC; the 200 of ETH silently vanishes (true value 1000)
    assert last["total_value"] == pytest.approx(800.0)


def test_price_lookup_error_drops_the_whole_snapshot_row_characterizes_known_debt_D9(db, monkeypatch, calc):
    def boom(asset, date):
        raise RuntimeError("exchange down")
    monkeypatch.setattr(pc, "get_price", boom)
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-05")
    assert len(h) == 0  # every snapshot swallowed by `except Exception: pass`


def test_transaction_before_default_start_is_ignored_characterizes_known_debt_D2(db, calc, const_price):
    # AC7.7
    db.add_transaction("2021-12-31", "USDT", "buy", 1000, 1, 1000)
    h = calc.calculate_portfolio_history(end_date="2022-01-10")
    assert h.index.min() == pd.Timestamp("2022-01-01")
    assert (h["total_value"] == 0).all()


def test_transaction_on_default_start_is_applied(db, calc, const_price):
    db.add_transaction("2022-01-01", "USDT", "buy", 1000, 1, 1000)
    h = calc.calculate_portfolio_history(end_date="2022-01-10")
    assert h["total_value"].iloc[-1] == pytest.approx(1000.0)


def test_last_month_income_is_in_columns_but_not_in_total_value_characterizes_known_debt_D5(db, calc, const_price):
    db.add_transaction("2024-01-01", "BTC", "buy", 1, 100, 100)
    db.add_funding_rate(2024, 1, "BTC", 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-01-31")  # January is the last month
    last = h.iloc[-1]
    assert last["funding_income"] == pytest.approx(1.0)
    assert last["USDT_value"] == pytest.approx(0.0)            # income not credited yet
    assert last["total_value"] == pytest.approx(100.0)         # BTC only, income missing
    h2 = calc.calculate_portfolio_history("2024-01-01", "2024-02-01")  # once February starts it is credited
    assert h2.iloc[-1]["total_value"] == pytest.approx(101.0)


def test_pool_income_for_average_pool_balance(db, calc, const_price):
    # pool 100 from Jan 3 on; average over 31 days = 100 * 29 / 31; income = avg * 12 % / 12
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    db.add_transaction("2024-01-02", "BTC", "buy", 1, 100, 100)
    db.add_transaction("2024-01-03", "BTC", "sell", 1, 100, 100)
    db.add_pool_rate(2024, 1, 12.0)
    h = calc.calculate_portfolio_history("2024-01-01", "2024-02-01")
    expected = 100 * 29 / 31 * 0.12 / 12
    assert _row(h, "2024-01-01")["pool_income"] == pytest.approx(expected)
    assert _row(h, "2024-02-01")["USDT_value"] == pytest.approx(900.0 + expected)


def test_end_date_before_start_gives_empty_frame(db, calc, const_price):
    db.add_transaction("2024-01-01", "USDT", "buy", 1000, 1, 1000)
    assert len(calc.calculate_portfolio_history("2024-02-01", "2024-01-01")) == 0
