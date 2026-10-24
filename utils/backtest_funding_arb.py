"""
Funding Rate Arbitrage backtest: delta-neutral long spot / short perp, collect funding.
"""
# flake8: noqa: E501
import pandas as pd
import numpy as np
from typing import Dict, Tuple


class FundingArbPortfolio:
    """
    Tracks equity, positions, applies funding and commissions.
    Long spot, short perp (delta-neutral). Funding received when short perp (funding > 0).
    """

    def __init__(
        self,
        capital: float,
        leverage: float,
        fee_spot: float,
        fee_perp: float,
        mmr: float = 0.05,
    ):
        self.initial_capital = capital
        self.equity = capital
        self.leverage = leverage
        self.fee_spot = fee_spot
        self.fee_perp = fee_perp
        self.mmr = mmr  # maintenance margin ratio
        self.positions = {"qty_spot": 0.0, "qty_perp": 0.0, "notional": 0.0,
                          "perp_entry": 0.0, "spot_entry": 0.0}
        self.pnl_funding = 0.0
        self.pnl_basis = 0.0
        self.pnl_commissions = 0.0

    def has_position(self) -> bool:
        return self.positions["notional"] > 0

    def open_delta_neutral(
        self, notional: float, spot_price: float, perp_price: float,
        slippage_pct: float = 0.0,
    ) -> bool:
        """Open long spot, short perp. Returns True if opened."""
        if spot_price <= 0 or perp_price <= 0 or notional <= 0:
            return False
        # Margin required on perp side
        margin_perp = notional / self.leverage
        if margin_perp > self.equity:
            return False
        buy_slippage = 1 + slippage_pct
        sell_slippage = 1 - slippage_pct
        spot_fill = spot_price * buy_slippage
        perp_fill = perp_price * sell_slippage
        qty = notional / spot_fill
        fee_spot = notional * self.fee_spot
        fee_perp = notional * self.fee_perp
        self.equity -= fee_spot + fee_perp
        self.pnl_commissions -= fee_spot + fee_perp
        self.positions["qty_spot"] = qty
        self.positions["qty_perp"] = -qty
        self.positions["notional"] = notional
        self.positions["perp_entry"] = perp_fill
        self.positions["spot_entry"] = spot_fill
        return True

    def close_all(
        self, spot_price: float, perp_price: float,
        slippage_pct: float = 0.0,
    ) -> float:
        """Close position, realize PnL. Returns realized PnL."""
        if not self.has_position():
            return 0.0
        qty = self.positions["qty_spot"]
        sell_spot = spot_price * (1 - slippage_pct)
        buy_perp = perp_price * (1 + slippage_pct)
        spot_pnl = qty * (sell_spot - self.positions["spot_entry"])
        perp_pnl = (-qty) * (buy_perp - self.positions["perp_entry"])
        basis_pnl = spot_pnl + perp_pnl
        fee_spot = qty * sell_spot * self.fee_spot
        fee_perp = qty * buy_perp * self.fee_perp
        self.equity += basis_pnl - fee_spot - fee_perp
        self.pnl_basis += basis_pnl
        self.pnl_commissions -= fee_spot + fee_perp
        self.positions = {"qty_spot": 0.0, "qty_perp": 0.0, "notional": 0.0,
                          "perp_entry": 0.0, "spot_entry": 0.0}
        return basis_pnl

    def update_mark_to_market(self, spot_price: float, perp_price: float) -> None:
        """Update equity with unrealized PnL."""
        if not self.has_position():
            return
        qty = self.positions["qty_spot"]
        perp_unrealized = (-qty) * (perp_price - self.positions["perp_entry"])
        spot_unrealized = qty * (spot_price - self.positions["spot_entry"])
        self.equity = (
            self.initial_capital + self.pnl_funding + self.pnl_basis
            + self.pnl_commissions + perp_unrealized + spot_unrealized
        )

    def apply_funding(self, funding_rate_8h: float) -> None:
        """Apply funding payment (we are short perp: we receive when rate > 0)."""
        if not self.has_position():
            return
        notional = self.positions["notional"]
        # 3 funding events per day (8h each) -> daily funding ≈ 3 * rate * notional
        payment = notional * funding_rate_8h * 3
        self.equity += payment
        self.pnl_funding += payment

    def check_liquidation(self, perp_price: float) -> bool:
        """True if margin ratio < mmr."""
        if not self.has_position():
            return False
        notional = self.positions["notional"]
        margin_used = notional / self.leverage
        equity_for_margin = self.equity
        if margin_used <= 0:
            return False
        ratio = equity_for_margin / margin_used
        return ratio < self.mmr


def run_funding_arb_backtest(
    data: pd.DataFrame,
    initial_capital: float = 100_000,
    leverage: float = 3.0,
    funding_threshold: float = 0.0001,
    min_funding_to_stay: float = 0.00005,
    basis_sl_pct: float = 3.0,
    target_notional_pct: float = 50.0,
    fee_spot: float = 0.001,
    fee_perp: float = 0.0005,
    slippage_pct: float = 0.0002,
    mmr: float = 0.05,
) -> Tuple[pd.Series, Dict]:
    """
    Run funding arb backtest. data must have: date, spot, perp, funding_8h, is_funding_time.
    target_notional_pct = % of equity to use as notional when opening.
    Returns (equity_curve, metrics_dict).
    """
    portfolio = FundingArbPortfolio(
        capital=initial_capital,
        leverage=leverage,
        fee_spot=fee_spot,
        fee_perp=fee_perp,
        mmr=mmr,
    )
    equity_log = []
    dates_log = []

    for _, row in data.iterrows():
        date = row["date"]
        spot = float(row["spot"])
        perp = float(row["perp"])
        funding_8h = float(row["funding_8h"])
        is_funding = row.get("is_funding_time", True)

        portfolio.update_mark_to_market(spot, perp)

        if portfolio.check_liquidation(perp):
            portfolio.close_all(spot, perp, slippage_pct=slippage_pct * 2)
            equity_log.append(portfolio.equity)
            dates_log.append(date)
            continue

        if not portfolio.has_position():
            if funding_8h > funding_threshold:
                notional = portfolio.equity * (target_notional_pct / 100.0)
                portfolio.open_delta_neutral(notional, spot, perp, slippage_pct)
        else:
            basis_pct = (perp - spot) / spot * 100
            if abs(basis_pct) > basis_sl_pct:
                portfolio.close_all(spot, perp, slippage_pct)
            elif funding_8h < min_funding_to_stay:
                portfolio.close_all(spot, perp, slippage_pct)

        if is_funding and portfolio.has_position():
            portfolio.apply_funding(funding_8h)

        equity_log.append(portfolio.equity)
        dates_log.append(date)

    equity_curve = pd.Series(equity_log, index=dates_log)
    equity_curve.index = pd.to_datetime(equity_curve.index)

    # Metrics
    total_return_pct = (portfolio.equity / initial_capital - 1) * 100
    returns = equity_curve.pct_change().fillna(0)
    n_days = max(1, (equity_curve.index[-1] - equity_curve.index[0]).days)
    annual_return = (portfolio.equity / initial_capital) ** (365 / n_days) - 1 if n_days else 0
    vol = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0
    sharpe = (annual_return / (vol / 100)) if vol else 0
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max * 100
    max_dd = drawdown.min()

    metrics = {
        "initial_capital": initial_capital,
        "final_equity": portfolio.equity,
        "total_return_pct": total_return_pct,
        "annual_return_pct": annual_return * 100,
        "volatility_annual_pct": vol,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd,
        "pnl_funding": portfolio.pnl_funding,
        "pnl_basis": portfolio.pnl_basis,
        "pnl_commissions": portfolio.pnl_commissions,
    }
    return equity_curve, metrics
