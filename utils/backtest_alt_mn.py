"""
Alt Market-Neutral backtest: long/short by momentum, hedged with BTC.
"""
# flake8: noqa: E501
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

try:
    import statsmodels.api as sm
except ImportError:
    sm = None


def rolling_beta(series: pd.Series, benchmark: pd.Series, window: int = 60) -> pd.Series:
    """Rolling OLS beta of series on benchmark."""
    if sm is None:
        return pd.Series(np.zeros(len(series)), index=series.index)
    betas = []
    for i in range(len(series)):
        if i < window:
            betas.append(np.nan)
            continue
        y = series.iloc[i - window:i].replace([np.inf, -np.inf], np.nan).dropna()
        x = benchmark.iloc[i - window:i].loc[y.index]
        if len(y) < window // 2:
            betas.append(np.nan)
            continue
        X = sm.add_constant(x)
        try:
            model = sm.OLS(y, X).fit()
            betas.append(model.params.iloc[1])
        except Exception:
            betas.append(np.nan)
    return pd.Series(betas, index=series.index)


def build_long_short_buckets(
    mom_z: pd.Series, universe: pd.Series, q: float = 0.2
) -> Tuple[List[str], List[str]]:
    """Return (longs, shorts) symbol lists: long top q, short bottom q."""
    valid = mom_z[universe.fillna(False)].dropna()
    if len(valid) < 10:
        return [], []
    s = valid.sort_values()
    k = max(1, int(len(s) * q))
    shorts = s.index[:k].tolist()
    longs = s.index[-k:].tolist()
    return longs, shorts


def run_alt_mn_backtest(
    prices: pd.DataFrame,
    initial_capital: float = 100_000,
    lookback_days: int = 30,
    quantile: float = 0.2,
    rebalance_days: int = 7,
    fee: float = 0.001,
    slippage_pct: float = 0.001,
    beta_window: int = 60,
) -> Tuple[pd.Series, Dict]:
    """
    prices: DataFrame index=date, columns=symbols (must include 'BTC').
    Long top quantile momentum, short bottom quantile, hedge with BTC.
    Returns (equity_curve, metrics_dict).
    """
    if "BTC" not in prices.columns or len(prices) < max(lookback_days, beta_window) + 10:
        return pd.Series(dtype=float), {}

    ret = prices.pct_change()
    # Momentum: past lookback_days return
    mom = prices / prices.shift(lookback_days) - 1
    mom_z = mom.sub(mom.mean(axis=1), axis=0).div(mom.std(axis=1), axis=0)

    # Rolling betas to BTC
    btc_ret = ret["BTC"]
    betas = {}
    for col in prices.columns:
        if col == "BTC":
            betas[col] = pd.Series(1.0, index=prices.index)
        else:
            betas[col] = rolling_beta(ret[col], btc_ret, window=beta_window)
    betas_df = pd.DataFrame(betas)

    # Backtest loop: at each bar apply PnL from previous weights, then rebalance if due
    equity = initial_capital
    equity_curve = []
    dates_list = []
    position_weights = {}  # symbol -> weight (signed), in effect for next period
    n_days = 0

    for i in range(lookback_days + beta_window, len(prices)):
        t = prices.index[i]
        prev_t = prices.index[i - 1]
        dates_list.append(t)

        # 1) PnL from price move (weights held during prev_t -> t)
        if position_weights and i > 0:
            period_ret = 0.0
            for sym, w in position_weights.items():
                if sym not in prices.columns:
                    continue
                p_prev = prices.loc[prev_t, sym]
                p_curr = prices.loc[t, sym]
                if p_prev and p_prev > 0 and pd.notna(p_curr):
                    ret_sym = (p_curr - p_prev) / p_prev
                    period_ret += w * ret_sym
            equity = equity * (1 + period_ret)

        # 2) Rebalance if due
        if n_days % rebalance_days == 0:
            universe_t = mom_z.loc[t].notna()
            longs, shorts = build_long_short_buckets(mom_z.loc[t], universe_t, q=quantile)
            if longs or shorts:
                target = {}
                for s in longs:
                    target[s] = 0.5 / len(longs)
                for s in shorts:
                    target[s] = -0.5 / len(shorts)
                beta_long = sum(
                    target.get(s, 0) * betas_df.loc[t, s] for s in longs
                    if s in betas_df.columns and pd.notna(betas_df.loc[t, s])
                )
                beta_short = sum(
                    target.get(s, 0) * betas_df.loc[t, s] for s in shorts
                    if s in betas_df.columns and pd.notna(betas_df.loc[t, s])
                )
                net_beta = (beta_long or 0) - (beta_short or 0)
                target["BTC"] = -net_beta
                pos_sum = sum(abs(v) for v in target.values())
                if pos_sum > 0:
                    for k in target:
                        target[k] = target[k] / pos_sum
                position_weights = target
                turnover = sum(abs(v) for v in target.values())
                equity -= equity * turnover * (fee + slippage_pct)

        equity_curve.append(equity)
        n_days += 1

    equity_series = pd.Series(equity_curve, index=pd.to_datetime(dates_list))
    total_return_pct = (equity / initial_capital - 1) * 100
    returns = equity_series.pct_change().fillna(0)
    n_days_cal = max(1, (equity_series.index[-1] - equity_series.index[0]).days)
    annual_return = (equity / initial_capital) ** (365 / n_days_cal) - 1 if n_days_cal else 0
    vol = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0
    sharpe = (annual_return / (vol / 100)) if vol else 0
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    metrics = {
        "initial_capital": initial_capital,
        "final_equity": equity,
        "total_return_pct": total_return_pct,
        "annual_return_pct": annual_return * 100,
        "volatility_annual_pct": vol,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd,
    }
    return equity_series, metrics
