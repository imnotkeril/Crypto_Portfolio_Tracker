# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [1.0.0] - 2026-11-01

First documented release (audit baseline on branch `chore/audit`; not merged or pushed).

### Added
- Local Streamlit app: transaction ledger (buy/sell, USDT deposits), Binance daily prices via `ccxt`, price discovery by target price.
- Monthly Coin-M funding and USDT-pool yield inputs with auto-populate estimates; income computed from average positions.
- Portfolio value history in USDT, return/risk metrics (total, annual, monthly, volatility, Sharpe, Sortino, drawdowns) and charts on the Analytics page.
- Backtest page (funding arbitrage, alt market-neutral) with a red SYNTHETIC / ASSUMED DATA flag, and a static Guide page.
- Research/not-investment-advice disclaimer in README, dashboard and Backtest page (single source `utils/disclaimer.py`).
- Pinned runtime and dev requirements; test suite grown from 21 to 76 tests (database, migration, metrics, portfolio history, assets, backtest regressions, config, disclaimer); mypy and pandas-stubs pinned for dev.
- Documentation: SPEC, ARCHITECTURE with ADRs, plan, REVIEW, QA report, rewritten README.

### Changed
- README, SPEC and ARCHITECTURE describe the real behavior; known debt D1-D13 is recorded, not fixed.

### Fixed
- A USDT deposit made while the pool held sale proceeds no longer erases part of the pool balance (R-02).
- Alt market-neutral BTC hedge used the wrong sign; it now uses net beta (R-03).
- Funding history is paginated beyond 1000 points and forward-filled funding is flagged (R-04).
- USDT is always offered in the asset list (R-05).
- Max drawdown on an all-zero series no longer raises (R-08).
- Legacy database migration is safe: file backup, transaction, row-count check, no swallowed errors.
- pandas 3 resample frequencies (month/year-end) in monthly and yearly returns.
- Backtests flag synthetic or assumed data explicitly.
- Unused imports removed; guide page cleaned of chat leftovers and an external logo.

### Security
- Streamlit binds to `127.0.0.1` with `allowedHosts` limited to localhost (S-01); the app has no authentication by design.
- The whole `data/` directory is gitignored (S-02).

### Known issues
- R-01 (P1, owner decision): external deposits/withdrawals count as performance.
- Metrics annualize sparse history with 252 periods (D1/R-11); other open P2/P3 items in `docs/REVIEW.md`.
- `scripts/migrate_database.py` drops tables without a backup (S-03); do not run it.
