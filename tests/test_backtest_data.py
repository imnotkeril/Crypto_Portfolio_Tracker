from datetime import datetime, timezone

import pandas as pd

from utils import backtest_data as bd

DAY = 86_400_000
T0 = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _fake_get(total_points, calls):
    """Serves funding points every 8h from T0, honouring startTime and limit."""
    pts = [{"fundingTime": T0 + i * DAY // 3, "fundingRate": "0.0001"} for i in range(total_points)]

    def get(url, params=None, timeout=None):
        calls.append(dict(params))
        sel = [p for p in pts if p["fundingTime"] >= params["startTime"]
               and p["fundingTime"] <= params["endTime"]]
        return _Resp(sel[: params["limit"]])

    return get


def test_funding_history_is_paginated(monkeypatch):
    import requests
    calls = []
    monkeypatch.setattr(requests, "get", _fake_get(2500, calls))
    out = bd._fetch_funding_history("BTCUSDT", T0, T0 + 900 * DAY)
    assert len(out) == 2500
    assert len(calls) == 3
    assert calls[1]["startTime"] > calls[0]["startTime"]


def _setup_loader(monkeypatch, n_days, funding_points):
    import requests
    from utils import price_fetcher
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    spot = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "price": 100.0})
    monkeypatch.setattr(price_fetcher, "get_price_range", lambda *a, **k: spot)

    class Ex:
        def fetch_ohlcv(self, sym, tf, since=None, limit=None):
            rows = [[T0 + i * DAY, 0, 0, 0, 100.0, 0] for i in range(n_days)]
            return [r for r in rows if r[0] >= since]

    monkeypatch.setattr(bd, "_binance_futures", lambda: Ex())
    monkeypatch.setattr(requests, "get", _fake_get(funding_points, []))


def test_full_funding_coverage_not_synthetic(monkeypatch):
    _setup_loader(monkeypatch, 25, 3 * 40)  # spot ends before the request window does
    df = bd.load_funding_arb_data("BTC", "2024-01-01", "2024-01-30")
    assert df.attrs["synthetic"] is False
    assert df.attrs["notes"] == []


def test_forward_filled_funding_is_flagged(monkeypatch):
    # funding covers only the first 10 days of a 30-day window
    _setup_loader(monkeypatch, 30, 3 * 10)
    df = bd.load_funding_arb_data("BTC", "2024-01-01", "2024-01-30")
    assert df.attrs["synthetic"] is True
    assert any("forward-filled" in n for n in df.attrs["notes"])
