"""
Backtest data: load spot/perp/funding for Funding Arb and multi-asset prices for Alt MN.
Uses Binance via ccxt; fallback to synthetic data if API fails.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys

# Add parent for price_fetcher
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import ccxt
except ImportError:
    ccxt = None


def _binance_futures():
    """Binance USDT-M futures exchange."""
    if ccxt is None:
        return None
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })


def _flag(df: pd.DataFrame, synthetic: bool, notes: Optional[List[str]] = None) -> pd.DataFrame:
    """Mark a loaded frame: attrs['synthetic'] (any made-up data) and attrs['notes'] (why)."""
    df.attrs['synthetic'] = bool(synthetic)
    df.attrs['notes'] = list(notes or [])
    return df


def load_funding_arb_data(
    symbol: str = "BTC",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    use_synthetic: bool = False,
) -> pd.DataFrame:
    """
    Load daily timeline: spot, perp, funding_rate, is_funding_time.
    Dates in YYYY-MM-DD. is_funding_time = True at end of each day (1 funding event per day for simplicity).
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if start >= end:
        return pd.DataFrame()

    if use_synthetic:
        return _flag(_synthetic_funding_arb_data(start, end), True, ["Synthetic data requested by user."])

    spot_symbol = f"{symbol}/USDT"
    perp_symbol = f"{symbol}/USDT:USDT"  # ccxt futures

    # 1) Spot daily from existing price_fetcher
    from utils.price_fetcher import get_price_range
    spot_df = get_price_range(spot_symbol, start_date, end_date)
    if spot_df is None or len(spot_df) == 0:
        return _flag(_synthetic_funding_arb_data(start, end), True,
                     ["Spot prices unavailable (Binance) - ENTIRE dataset is synthetic."])
    spot_df = spot_df.rename(columns={"date": "date", "price": "spot"})
    spot_df["date"] = pd.to_datetime(spot_df["date"]).dt.strftime("%Y-%m-%d")

    # 2) Perp daily from Binance futures
    try:
        ex = _binance_futures()
        if ex is None:
            raise RuntimeError("ccxt not available")
        since_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        all_ohlcv = []
        while since_ms < end_ms:
            ohlcv = ex.fetch_ohlcv(perp_symbol, "1d", since=since_ms, limit=500)
            if not ohlcv:
                break
            for c in ohlcv:
                all_ohlcv.append({"ts": c[0], "close": c[4]})
            since_ms = ohlcv[-1][0] + 86400_000
        if not all_ohlcv:
            return _flag(_synthetic_funding_arb_data(start, end), True,
                         ["Perp prices unavailable (Binance futures) - ENTIRE dataset is synthetic."])
        perp_df = pd.DataFrame(all_ohlcv)
        perp_df["date"] = pd.to_datetime(perp_df["ts"], unit="ms").dt.strftime("%Y-%m-%d")
        perp_df = perp_df.groupby("date", as_index=False)["close"].last()
        perp_df = perp_df.rename(columns={"close": "perp"})
    except Exception as exc:
        return _flag(_synthetic_funding_arb_data(start, end), True,
                     [f"Perp prices failed ({type(exc).__name__}) - ENTIRE dataset is synthetic."])

    # 3) Funding rate history from Binance
    notes: List[str] = []
    try:
        # Binance: GET /fapi/v1/fundingRate
        import requests
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": f"{symbol}USDT", "startTime": int(start.timestamp() * 1000),
                  "endTime": int(end.timestamp() * 1000), "limit": 1000}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError("No funding data")
        fund_df = pd.DataFrame(data)
        fund_df["date"] = pd.to_datetime(fund_df["fundingTime"], unit="ms").dt.strftime("%Y-%m-%d")
        fund_df["fundingRate"] = fund_df["fundingRate"].astype(float)
        # Daily average funding rate (3 points per day for 8h)
        fund_daily = fund_df.groupby("date")["fundingRate"].mean().reset_index()
        fund_daily = fund_daily.rename(columns={"fundingRate": "funding_8h"})
    except Exception as exc:
        # Constant funding assumption - flagged, never silent
        notes.append(f"Funding history unavailable ({type(exc).__name__}): constant funding_8h=0.0001 assumed.")
        fund_daily = spot_df[["date"]].copy()
        fund_daily["funding_8h"] = 0.0001

    # Merge (inner so we have both spot and perp)
    df = spot_df.merge(perp_df, on="date", how="inner").sort_values("date")
    df = df.merge(fund_daily, on="date", how="left")
    df["funding_8h"] = df["funding_8h"].ffill().fillna(0.0001)
    df["is_funding_time"] = True  # apply once per day
    df = df.dropna(subset=["spot", "perp"])
    return _flag(df, bool(notes), notes)


def _synthetic_funding_arb_data(start: datetime, end: datetime) -> pd.DataFrame:
    """Generate synthetic spot, perp, funding for demo."""
    dates = pd.date_range(start=start, end=end, freq="D")
    n = len(dates)
    np.random.seed(42)
    ret = np.random.randn(n).cumsum() * 0.002 + 0.0002
    spot = 40000 * np.exp(ret)
    basis = np.random.randn(n).cumsum() * 0.0005
    perp = spot * (1 + basis)
    funding = np.maximum(0.00005 + np.random.randn(n) * 0.00003, 0.00001)
    df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "spot": spot,
        "perp": perp,
        "funding_8h": funding,
        "is_funding_time": True,
    })
    return df


def load_alt_mn_data(
    symbols: List[str],
    start_date: str,
    end_date: str,
    use_synthetic: bool = False,
) -> pd.DataFrame:
    """
    Load daily close prices for multiple symbols (e.g. BTC, ETH, BNB). Index = date, columns = symbols.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if start >= end or not symbols:
        return pd.DataFrame()

    if use_synthetic:
        return _flag(_synthetic_alt_mn_data(symbols, start, end), True, ["Synthetic data requested by user."])

    from utils.price_fetcher import get_price_range
    all_dfs = []
    for sym in symbols:
        pair = f"{sym}/USDT" if "/" not in sym else sym
        df = get_price_range(pair, start_date, end_date)
        if df is not None and len(df) > 0:
            df = df.rename(columns={"date": "date", "price": sym})
            all_dfs.append(df)
    if not all_dfs:
        return _flag(_synthetic_alt_mn_data(symbols, start, end), True,
                     ["No prices from Binance - ENTIRE dataset is synthetic."])

    out = all_dfs[0]
    for df in all_dfs[1:]:
        out = out.merge(df, on="date", how="outer")
    out = out.sort_values("date").dropna(how="all", subset=[c for c in out.columns if c != "date"])
    out = out.set_index("date")
    missing = [x for x in symbols if x not in out.columns]
    return _flag(out, False, [f"No data for: {', '.join(missing)}"] if missing else [])


def _synthetic_alt_mn_data(symbols: List[str], start: datetime, end: datetime) -> pd.DataFrame:
    """Synthetic correlated prices for alts + BTC."""
    dates = pd.date_range(start=start, end=end, freq="D")
    n = len(dates)
    np.random.seed(43)
    btc_ret = np.random.randn(n).cumsum() * 0.01 + 0.0003
    btc = 40000 * np.exp(btc_ret)
    data = {"BTC": btc}
    for i, sym in enumerate(symbols):
        if sym == "BTC":
            continue
        beta = 0.5 + np.random.rand()
        idio = np.random.randn(n).cumsum() * 0.005
        ret = (btc_ret * beta + idio) * 0.5
        data[sym] = 2000 * np.exp(ret)
    df = pd.DataFrame(data, index=[d.strftime("%Y-%m-%d") for d in dates])
    df.index.name = "date"
    return df
