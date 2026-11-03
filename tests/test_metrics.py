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


def test_max_drawdown_all_zero_series_does_not_raise():
    # R-08: running max 0 -> drawdown all NaN used to raise in idxmin
    from utils.metrics import calculate_max_drawdown
    s = pd.Series([0.0, 0.0, 0.0], index=["2024-01-01", "2024-01-02", "2024-01-03"])
    assert calculate_max_drawdown(s) == (0.0, "", "")


# ---- T21: edge cases and annualization characterization -------------------------------------------

def _two_points(start, end, v0=100.0, v1=200.0):
    return pd.Series([v0, v1], index=[start, end])


def test_sortino_no_negative_returns_with_positive_mean_is_999():
    # AC8.7
    assert metrics.calculate_sortino_ratio(pd.Series([0.01, 0.02, 0.0, 0.03])) == 999.0


def test_sortino_no_negative_returns_with_zero_mean_is_zero():
    assert metrics.calculate_sortino_ratio(pd.Series([0.0, 0.0, 0.0])) == 0.0


def test_sortino_short_series_is_zero():
    assert metrics.calculate_sortino_ratio(pd.Series([0.05])) == 0.0


def test_sortino_with_several_negatives_is_finite_and_not_sentinel():
    r = pd.Series([0.03, -0.01, 0.02, -0.02, 0.01])
    s = metrics.calculate_sortino_ratio(r)
    assert np.isfinite(s) and s != 999.0 and s > 0


@pytest.mark.parametrize("start,end,days", [
    ("2024-01-01", "2024-12-31", 365),
    ("2024-01-01", "2025-01-01", 366),
])
def test_annual_return_of_doubling_over_about_one_year(start, end, days):
    # AC8.8: expected 2 ** (365.25 / days) - 1; stated tolerance 0.5 percentage points around 100 %
    out = metrics.calculate_annual_return(_two_points(start, end))
    assert out == pytest.approx((2 ** (365.25 / days) - 1) * 100)
    assert out == pytest.approx(100.0, abs=0.5)


def test_annual_return_edge_cases():
    assert metrics.calculate_annual_return(pd.Series([100.0])) == 0.0
    assert metrics.calculate_annual_return(_two_points("2024-01-01 00:00", "2024-01-01 12:00")) == 0.0  # < 1 day
    assert metrics.calculate_annual_return(_two_points("2024-01-01", "2025-01-01", 100, 0)) == -100.0
    assert metrics.calculate_annual_return(_two_points("2024-01-01", "2025-01-01", 0, 0)) == 0.0


def test_monthly_returns_empty_when_fewer_than_two_positive_months():
    # AC8.9
    one_month = series([100.0, 110.0, 120.0])
    out = metrics.calculate_monthly_returns(one_month)
    assert len(out) == 0 and out.dtype == float
    zeros_then_one = pd.Series([0.0, 100.0], index=["2024-01-31", "2024-02-29"])
    assert len(metrics.calculate_monthly_returns(zeros_then_one)) == 0
    assert len(metrics.calculate_monthly_returns(pd.Series([0.0, 0.0], index=["2024-01-01", "2024-02-01"]))) == 0


def test_monthly_returns_two_months_in_percent():
    s = pd.Series([100.0, 110.0], index=["2024-01-31", "2024-02-29"])
    assert metrics.calculate_monthly_returns(s).iloc[0] == pytest.approx(10.0)


def test_avg_monthly_and_yearly_return_empty_inputs():
    assert metrics.calculate_avg_monthly_return(pd.Series([], dtype=float)) == 0.0
    assert metrics.calculate_avg_yearly_return(pd.Series([], dtype=float)) == 0.0


def test_volatility_ignores_nan_and_inf():
    r = pd.Series([0.01, np.nan, -0.01, np.inf, 0.01, -0.01])
    clean = pd.Series([0.01, -0.01, 0.01, -0.01])
    assert metrics.calculate_volatility(r) == pytest.approx(metrics.calculate_volatility(clean))


def test_volatility_uses_sqrt_252_regardless_of_row_spacing_characterizes_known_debt_D1():
    # D1 / R-11: the same percentage moves give the same "annualized" volatility whether the
    # rows are 1 day or 1 month apart. Pinned as CURRENT behaviour, not as correct behaviour.
    values = [100.0, 110.0, 99.0, 120.0, 108.0]
    daily = series(values, "2024-01-01")
    monthly = pd.Series(values, index=pd.date_range("2024-01-01", periods=5, freq="MS").strftime("%Y-%m-%d"))
    v_daily = metrics.calculate_volatility(metrics.calculate_returns(daily))
    v_monthly = metrics.calculate_volatility(metrics.calculate_returns(monthly))
    assert v_daily == pytest.approx(v_monthly)
    r = metrics.calculate_returns(monthly)
    assert v_monthly == pytest.approx(r.std() * np.sqrt(252) * 100)
    # Sharpe annualizes the same way (mean * 252, std * sqrt(252)) for both spacings
    assert metrics.calculate_sharpe_ratio(metrics.calculate_returns(daily)) == pytest.approx(
        metrics.calculate_sharpe_ratio(metrics.calculate_returns(monthly)))


def test_external_deposit_counts_as_return_characterizes_open_finding_R01():
    # R-01 (owner decision): values 1000 -> 1000 -> 2000 caused only by a second deposit
    vals = series([1000.0, 1000.0, 2000.0])
    m = metrics.calculate_all_metrics(vals)
    assert m["total_return"] == pytest.approx(100.0)


def test_sortino_999_with_exactly_one_negative_return_characterizes_open_finding_R10():
    # R-10: ddof=1 std of a single downside element is NaN -> sentinel 999 although a loss exists
    assert metrics.calculate_sortino_ratio(pd.Series([0.0, 0.05, -0.02, 0.03])) == 999.0


def test_avg_yearly_return_zeroes_whole_metric_on_inf_year_characterizes_open_finding_R09():
    yearly = pd.Series([0.0, np.inf, 25.0])
    assert metrics.calculate_avg_yearly_return(yearly) == 0.0
