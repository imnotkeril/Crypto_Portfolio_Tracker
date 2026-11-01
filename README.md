# Crypto Portfolio Tracker

> Research and educational tool. Not investment advice. Simulated and historical results do not guarantee future results; trading can lose all capital.

A local, single-user Streamlit app. You record crypto buys/sells, Coin-M funding and USDT-pool yields by hand; the app prices them with Binance public daily candles, rebuilds the portfolio value history in USDT and computes return/risk metrics. It also contains two research backtests (funding arbitrage, alt market-neutral). It places no orders and needs no API keys.

## Requirements

- Python 3.11+ (pandas 3.x)
- Internet access for prices (Binance public REST via `ccxt`, read-only, no keys)

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Direct dependencies are pinned in `requirements.txt` (streamlit 1.66.1, pandas 3.1.0, numpy 2.4.6, plotly 7.1.0, ccxt 4.5.90, python-dateutil 3.0.0, requests 2.34.2, statsmodels 0.15.0); transitive ones are not.

## Run

```bash
streamlit run main.py
```

Opens on http://localhost:8501. `.streamlit/config.toml` binds the server to `127.0.0.1` and sets `allowedHosts = ["localhost", "127.0.0.1"]`. There is no authentication: do not expose the app to a network or put it on a public host.

## Pages

| Page | What it does |
|---|---|
| Main (`main.py`) | Current holdings, prices, total value, quick stats, recent transactions, portfolio value history chart. Shows the disclaimer. |
| Transactions | Add/delete buys and sells (by asset quantity, position percentage or USDT amount; USDT deposits/withdrawals). Prices fetched from Binance. Price discovery ("By Target Price"): finds historical dates when an asset traded near a target price. |
| Funding | Monthly Coin-M funding % for BTC/ETH; amounts are computed from your average position. Auto-populate with estimated yearly averages. |
| Pools | Monthly USDT-pool APY; pool balance is fed by sales and USDT deposits. Auto-populate with estimates. |
| Analytics | Total/annual/monthly return, volatility, Sharpe, Sortino, drawdowns, income tiles, monthly and yearly return heatmaps, composition charts. |
| Backtest | Funding-arb and Alt market-neutral research backtests on Binance data or synthetic data. Any result built on synthetic or assumed data (including forward-filled funding) is flagged with a red SYNTHETIC / ASSUMED DATA warning; unflagged results use real Binance data. Shows the disclaimer. |
| Guide | Static text guide to the backtests. |

Typical flow: add transactions, then funding and pool rates, then read Analytics.

## Data and database

- SQLite file `data/portfolio.db`, created on first run (tables: `transactions`, `funding_rates`, `pool_rates`, `portfolio_snapshots`). Price and asset caches live in `data/cache/`.
- The whole `data/` directory is gitignored: it is not in the repository and not backed up. Back it up by copying the file while the app is stopped.
- A legacy schema (funding/pool tables with an `amount` column) is migrated automatically on start, after a file copy `data/portfolio.db.pre-migration-<timestamp>.bak`; the migration aborts and keeps the old table if it would lose rows.

## Environment variables

None. The app reads no environment variables and needs no `.env` file (there is no `.env.example`).

## Assumptions

| Assumption | Effect |
|---|---|
| Base currency is USDT; history is built from 2022-01-01 (earlier transactions are ignored) | Debt D2 |
| Metrics annualize with 252 periods per year on a sparse series (rows on transaction days, month starts and the last day) | Volatility, Sharpe and Sortino are not standard figures (D1, R-11) |
| Income is computed monthly from average positions/balances; the current month's income is shown but not added to total value | D5 |
| Prices are Binance daily candles; the price cache never expires | D6 |

Full list of known debt D1-D13: `docs/ARCHITECTURE.md` section 7.2.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

76 tests. They use throwaway SQLite files and mocked prices; they never touch `data/portfolio.db`. `requirements-dev.txt` also pins mypy and pandas-stubs.

## Helper scripts

These write to the real `data/portfolio.db` (resolved from the repo path). Back it up first; none of them has a dry-run flag or `--help`.

| Script | What it does |
|---|---|
| `scripts/auto_populate_funding.py` | Upserts estimated yearly Coin-M funding % (BTC/ETH, 2022 to current month). `populate_funding.py` in the repo root is a duplicate of it. |
| `scripts/populate_funding_data.py` | Interactive (asks 1 or 2). Writes the same estimated rates as above; option 2 tries Binance but always falls back to the estimates, so no real funding data is stored. |
| `scripts/migrate_database.py` | Legacy manual migration. Unsafe: drops/recreates tables without a backup (finding S-03). The app already migrates safely on start; do not run this script. |

Run from the repo root, e.g. `python scripts/auto_populate_funding.py`.

## Project structure

```
main.py                     Dashboard (entry point)
pages/                      transactions, funding, pools, analytics, backtest, guide
utils/
  database.py               SQLite access, schema init and migration
  price_fetcher.py          Binance prices via ccxt, JSON cache
  assets.py                 Binance USDT asset list (cached 24 h)
  portfolio_calculator.py   Portfolio value history and income
  metrics.py                Return/risk metrics
  backtest_data.py          Backtest data loaders (Binance or synthetic)
  backtest_funding_arb.py   Funding-arb strategy
  backtest_alt_mn.py        Alt market-neutral strategy
  disclaimer.py             Single source of the disclaimer text
scripts/                    Helper scripts (see above)
populate_funding.py         Duplicate of scripts/auto_populate_funding.py
tests/                      pytest suite
docs/                       SPEC, ARCHITECTURE (+ adr/), plan, REVIEW, QA, STATE, audit
.streamlit/config.toml      Loopback bind, allowedHosts, no usage stats
requirements.txt            Runtime pins
requirements-dev.txt        Test/typing pins (includes runtime)
data/                       Created at runtime, gitignored
```

## Known limitations

Status as of the QA verdict YELLOW (`docs/QA.md`); full findings in `docs/REVIEW.md`.

- **R-01 (open, owner decision):** external deposits/withdrawals are counted as performance, so returns and drawdowns are distorted when you add or remove USDT. Metrics are not time-weighted.
- **Sparse-history annualization (D1/R-11, open):** each return is a monthly or irregular step annualized as if daily; volatility, Sharpe and Sortino are indicative only.
- Other open items: "Average Annual" dilutes the first year (R-09), Sortino sentinel with one negative return (R-10), backtest annualization mixes 365 and 252 and has same-bar fills and no hold-out (R-12, R-13, D10), dashboard total value excludes funding/pool income (R-16), sells can drive a position negative and deletion has no confirmation (D11), a price error drops a whole history row silently (D9/R-17).
- Price fetcher and backtest engines are largely untested; no real-browser QA pass (layout, accessibility) was done.
- Tested on Windows and Python 3.11 only.

## Documentation

`docs/SPEC.md` (what the product does, reverse-engineered, pending owner approval), `docs/ARCHITECTURE.md`, `docs/QA.md`, `docs/REVIEW.md`, `CHANGELOG.md`.

## License

No license file; personal use.
