import numpy as np
import pandas as pd
import pytest

from utils import metrics


def series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D").strftime("%Y-%m-%d"))


def test_total_return():
    assert metrics.calculate_total_return(100, 150) == pytest.approx(50)
    assert metrics.calculate_total_return(0, 150) == 0.0
    assert metrics.calculate_total_return(float("nan"), 150) == 0.0


def test_returns_first_is_zero():
    r = metrics.calculate_returns(series([100, 110, 99]))
    assert r.iloc[0] == 0
    assert r.iloc[1] == pytest.approx(0.1)


def test_max_drawdown():
    dd, peak, trough = metrics.calculate_max_drawdown(series([100, 200, 100, 150]))
    assert dd == pytest.approx(50)
    assert peak == "2024-01-02" and trough == "2024-01-03"


def test_max_drawdown_short_series():
    assert metrics.calculate_max_drawdown(series([100])) == (0.0, "", "")


def test_volatility_constant_is_zero_and_short_safe():
    assert metrics.calculate_volatility(pd.Series([0.0, 0.0, 0.0])) == 0.0
    assert metrics.calculate_volatility(pd.Series([0.01])) == 0.0


def test_volatility_annualization():
    r = pd.Series([0.01, -0.01, 0.01, -0.01])
    assert metrics.calculate_volatility(r, annualized=True) == pytest.approx(
        metrics.calculate_volatility(r, annualized=False) * np.sqrt(252))


def test_sharpe_zero_std():
    assert metrics.calculate_sharpe_ratio(pd.Series([0.01, 0.01, 0.01])) == 0.0


def test_sharpe_positive_for_positive_drift():
    r = pd.Series([0.02, 0.01, 0.03, -0.005, 0.02])
    assert metrics.calculate_sharpe_ratio(r) > 0


def test_all_metrics_keys_and_values():
    vals = series([0, 0, 100, 110, 121, 90, 130] + [130] * 30)
    m = metrics.calculate_all_metrics(vals)
    for k in ("total_return", "annual_return", "volatility", "max_drawdown", "sharpe_ratio", "sortino_ratio"):
        assert k in m and np.isfinite(m[k])
    assert m["total_return"] == pytest.approx(30)  # initial = first non-zero (100)
    assert m["max_drawdown"] == pytest.approx((121 - 90) / 121 * 100)
