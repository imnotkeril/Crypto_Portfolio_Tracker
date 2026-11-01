import pandas as pd
import pytest

from utils.backtest_alt_mn import add_btc_hedge


def _portfolio_beta(w, betas):
    return sum(w[k] * betas[k] for k in w)


def test_hedge_is_beta_neutral_already_neutral_book():
    # R-03: long A 0.5 beta 1, short B -0.5 beta 1 is already neutral -> BTC leg 0.
    betas = pd.Series({"A": 1.0, "B": 1.0, "BTC": 1.0})
    w = add_btc_hedge({"A": 0.5, "B": -0.5}, ["A"], ["B"], betas)
    assert w["BTC"] == pytest.approx(0.0)
    assert _portfolio_beta(w, betas) == pytest.approx(0.0)


def test_hedge_is_beta_neutral_unbalanced_betas():
    betas = pd.Series({"A": 1.5, "B": 0.5, "BTC": 1.0})
    w = add_btc_hedge({"A": 0.5, "B": -0.5}, ["A"], ["B"], betas)
    assert _portfolio_beta(w, betas) == pytest.approx(0.0)
