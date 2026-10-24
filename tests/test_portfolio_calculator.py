import pandas as pd
import pytest

from utils import portfolio_calculator as pc


@pytest.fixture
def const_price(monkeypatch):
    monkeypatch.setattr(pc, "get_price", lambda asset, date: 100.0)

    def fake_range(symbol, start, end):
        d = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")
        return pd.DataFrame({"date": d, "price": 100.0})

    monkeypatch.setattr(pc, "get_price_range", fake_range)


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
