# ARCHITECTURE — Crypto Portfolio Tracker

Status: draft, **reverse-engineered** 2026-10-25 by `architect` (ADOPTION mode) from the code on branch `chore/audit` (HEAD dc3cb00), `docs/SPEC.md` (15 features, audited in `docs/checks/spec.md`), `docs/AUDIT_2026-10-24.md`, README, CLAUDE.md. It describes the system that exists; it proposes no rewrite and no new feature. Router: `finance/portfolio-risk` (tracker variant, no optimizer). Deviations from the router default stack are ADR-001..ADR-003, each awaiting the owner's ok in `docs/STATE.md`.

## 1. Stack and versions
Versions are the exact pins in `requirements.txt` / `requirements-dev.txt`. context7 MCP was not available in this agent run, so APIs were **not verified via context7**; release existence and `requires_python` were checked on PyPI on 2026-10-25 where noted. The global interpreter on this machine does NOT match the pins (see ADR-002); the pins were last installed and run in a clean venv by the audit on 2026-10-24.

| Layer | Choice | Version (pinned; PyPI checked 2026-10-25, not verified via context7) | Source: router / ADR-n |
|---|---|---|---|
| Language | Python | 3.11+ (local 3.11.9; router default 3.12) | ADR-002 |
| Env / packaging | pip + `requirements.txt` pins (no uv, no lockfile) | n/a | ADR-002 (deviation) |
| UI | streamlit | 1.66.1 (PyPI latest on 2026-10-25, requires_python >=3.11) | ADR-004 |
| Data frames | pandas | 3.1.0 (PyPI latest on 2026-10-25, requires_python >=3.11) | router |
| Numeric | numpy | 2.4.6 (PyPI release page checked, requires_python >=3.11) | router |
| Charts | plotly | 7.1.0 (not checked) | router family (`skill:data-visualization`) |
| Exchange access | ccxt (Binance public spot + USDT-M futures) | 4.5.90 (PyPI release page exists) | router family `stack:ccxt` |
| HTTP | requests (Binance `fapi/v1/fundingRate`) | 2.34.2 (not checked) | own |
| Stats | statsmodels (rolling OLS beta, Alt MN backtest) | 0.15.0 (not checked) | own |
| Dates | python-dateutil | 3.0.0 (not checked) | own |
| Storage | SQLite (stdlib `sqlite3`) + JSON file cache | stdlib | ADR-001 (deviation: no duckdb/parquet) |
| Optimizer | none (no skfolio / riskfolio-lib) | n/a | ADR-001 (deviation) |
| Tests | pytest | 9.1.1 | router |
| Typing / validation | partial annotations; no mypy-strict, pyright, beartype, pydantic, pandera, hypothesis | n/a | ADR-003 (deviation) |
| Lint | ruff (not pinned; 0.15.12 on this machine) | n/a | own |

## 2. System overview
Single process: `streamlit run main.py` serves the dashboard and the 6 pages in `pages/`; every page imports functions from `utils/` directly (no service layer, no API). Components:
- **UI** (`main.py`, `pages/*.py`): forms, tables, Plotly charts; calls `init_database()` on load.
- **Ledger and rates store** (`utils/database.py`): SQLite CRUD, holdings replay (`get_current_portfolio`, `get_portfolio_at_date`), safe legacy migration.
- **Market data** (`utils/price_fetcher.py`, `utils/assets.py`): Binance public endpoints via ccxt, file cache, offline asset list.
- **Portfolio engine** (`utils/portfolio_calculator.py`): day-by-day replay since 2022-01-01 with pool and income logic, sparse snapshots.
- **Metrics** (`utils/metrics.py`): returns, volatility, Sharpe, Sortino, drawdowns, monthly/yearly returns.
- **Backtests** (`utils/backtest_data.py`, `backtest_funding_arb.py`, `backtest_alt_mn.py`): loaders with explicit synthetic flag, two exploratory engines.
- **Scripts** (`scripts/*.py`, root `populate_funding.py`): manual helpers, not called by the app.

Data flow: Binance -> `price_fetcher` (cache) -> `database` (ledger rows) -> `portfolio_calculator` (history frame) -> `metrics` -> pages.

End-to-end trace (main user action: add a buy and see it valued):
1. Transactions page, method Asset Quantity, BTC 0.1, date D, automatic price on.
2. `get_price("BTC", D)`: key `BTC/USDT_D` in `data/cache/price_cache.json`? return it; else ccxt `fetch_ohlcv('BTC/USDT','1d', since=D-1d, limit=2)`, take the candle whose local date is D (else the last candle), write cache, return close; any error -> None and the page asks for a manual price.
3. `add_transaction(D,"BTC","buy",0.1,price,0.1*price)` -> one INSERT; `st.rerun()`.
4. Main page: `get_current_portfolio()` replays all rows (buy subtracts value from USDT only if USDT covers it); `get_current_price` per asset (ticker); Total Value = USDT + sum(qty x live price) over assets with a price.
5. `calculate_portfolio_history()` replays every day from 2022-01-01 to today, writes a row on transaction days, month starts and the last day, credits funding/pool income at month rollover; chart of `total_value`. Analytics runs the same history, then `calculate_all_metrics`.

## 3. Folder layout
One service, code at the project root (`rules/folders.md`). The finance blueprint layout (`src/<pkg>/`, `config/`, `runs/`, `reports/`) is NOT applied (ADR-001/002).
```
Crypto_portfolio/
  main.py              dashboard page (holdings cards, total value, history chart)
  pages/               Streamlit pages: transactions, funding, pools, analytics, backtest, guide
  utils/               domain + data: database, price_fetcher, assets, portfolio_calculator, metrics, backtest_*
  scripts/             manual helpers: auto_populate_funding, populate_funding_data, migrate_database (legacy, unsafe)
  populate_funding.py  root duplicate of scripts/auto_populate_funding.py (debt, plan T31)
  tests/               pytest: conftest (tmp DB fixture), test_database, test_metrics, test_portfolio_calculator
  .streamlit/          config.toml (tracked): loopback bind, no telemetry; secrets.toml ignored
  data/                gitignored: portfolio.db, *.bak, cache/*.json (personal data, never read by agents)
  docs/                SPEC, ARCHITECTURE, adr/, plan, STATE, checks/, AUDIT_2026-10-24
  .claude/skills/      linked skills (test-driven-development, data-visualization)
```

## 4. Data model
SQLite file `data/portfolio.db` (`utils.database.DB_PATH`), created with its folder on first `get_connection()`. Every function opens and closes its own connection; no pooling, no WAL setting, default isolation. All SQL is parameterized except table names inside the migration helper (constants, not user input).

| Table | Columns (type) | Keys / constraints | Used by |
|---|---|---|---|
| `transactions` | id INTEGER PK AUTOINCREMENT, date TEXT `YYYY-MM-DD` NOT NULL, asset TEXT NOT NULL, type TEXT NOT NULL (`buy`/`sell`), quantity REAL NOT NULL, price REAL NOT NULL, value REAL NOT NULL (USDT), created_at TEXT default CURRENT_TIMESTAMP | PK only; no CHECK (negative/zero not rejected), no uniqueness | F1, F2, F4, F7 |
| `funding_rates` | id PK, year INTEGER, month INTEGER, asset TEXT, percentage REAL (annual %), created_at | UNIQUE(year, month, asset); upsert = `INSERT OR REPLACE` (new id) | F5, F7, F14 |
| `pool_rates` | id PK, year INTEGER, month INTEGER, apy REAL (%), created_at | UNIQUE(year, month); `INSERT OR REPLACE` | F6, F7 |
| `portfolio_snapshots` | id PK, date TEXT, btc/eth/usdt quantity and value REAL, total_value REAL, created_at | UNIQUE(date) | writer/reader exist, unused by UI |

Relations: none (no foreign keys; `funding_rates.asset` matches `transactions.asset` by symbol text). Indexes: only PK and the UNIQUE autoindexes; `ORDER BY date` scans are fine at < 10k rows.
Migrations: no tool. `init_database()` is idempotent (`CREATE TABLE IF NOT EXISTS`) and runs `_drop_legacy_amount_column` for `funding_rates` / `pool_rates`: file backup `portfolio.db.pre-migration-<ts>.bak` via `sqlite3.backup`, one transaction, row-count check, rollback + re-raise on any error (commit ead29a9). `scripts/migrate_database.py` is the older unsafe migrator (no backup, swallows errors), not called. Before any future schema change: copy the DB file (CLAUDE.md), tier A, test-first.
Seed data: none in code paths of the app except the auto-populate buttons/scripts, which write hard-coded ESTIMATES (F5, F6, F14). Extensions: none.
Sensitive: `transactions` (personal trade history) and every `.bak`; whole `data/` gitignored (AC13.3).
Caches (files, not tables): `data/cache/price_cache.json` (`SYMBOL/USDT_YYYY-MM-DD` -> close, never expires), `data/cache/binance_usdt_assets.json` (24 h TTL). Derived, not stored: history frame, metrics, backtest equity and `attrs`.

## 5. Interfaces
No HTTP API of its own (so no `/llms.txt`), no auth. Interfaces are Streamlit pages and Python functions:
- Pages: `/` (main.py), `transactions`, `funding`, `pools`, `analytics`, `backtest`, `guide` (Streamlit multipage, sidebar).
- `utils.database`: `init_database()`, `add_transaction(date, asset, type, qty, price, value)`, `get_transactions() -> DataFrame`, `delete_transaction(id)`, `add_funding_rate`, `get_funding_rates`, `delete_funding_rate`, `add_pool_rate`, `get_pool_rates`, `delete_pool_rate`, `save_portfolio_snapshot`, `get_portfolio_snapshots`, `get_current_portfolio() -> dict`, `get_portfolio_at_date(date) -> dict`.
- `utils.price_fetcher`: `get_price(symbol, date) -> float | None`, `get_price_range(symbol, start, end) -> DataFrame[date, price]`, `get_current_price(symbol) -> float | None`, `find_dates_by_price(symbol, target, type, year, month, tolerance=0.02) -> DataFrame` (6 columns, empty on error).
- `utils.portfolio_calculator.calculate_portfolio_history(start_date="2022-01-01", end_date=None) -> DataFrame` indexed by date.
- `utils.metrics.calculate_all_metrics(values, risk_free_rate=0.0) -> dict` plus single-metric functions.
- `utils.backtest_data.load_funding_arb_data / load_alt_mn_data` (frames carry `attrs['synthetic']`, `attrs['notes']`); `run_funding_arb_backtest`, `run_alt_mn_backtest` -> (equity series, metrics dict).
- CLI: `python scripts/auto_populate_funding.py`, `python scripts/populate_funding_data.py` (both write to the REAL DB).
Errors: data functions return None / empty frames and `print()` to console; pages show `st.error`/`st.warning`/`st.info`.
Outbound calls: Binance public REST only (ccxt `enableRateLimit`), `requests` to `fapi.binance.com/fapi/v1/fundingRate` (timeout 10 s). No user-supplied URL is ever fetched (no SSRF surface).

## 6. Modules wiring
| Module | Depth | `requires` satisfied by | Touches (folders/tables/routes) | Env vars |
|---|---|---|---|---|
| none | n/a | n/a | n/a | none |
SPEC section 6 selects no module, so there is no `requires` chain and no `conflicts` pair: ok.

## 7. Cross-cutting
- Auth/authz: none; trust boundary = the loopback interface (ADR-004). Anyone with a local session can read and delete every row; delete buttons have no confirmation.
- Error handling and logging: errors become None/empty plus `print()`; `calculate_portfolio_history` wraps each snapshot in `except Exception: pass` (a failing snapshot day silently disappears, known debt D9); no log file, no structured logging.
- Config and secrets: no secrets, no API keys, no `.env` (none needed; `.env*` gitignored anyway). Config is `.streamlit/config.toml` (tracked) and module constants (`DB_PATH`, `CACHE_FILE`, `ASSETS_CACHE_FILE`, `CACHE_MAX_AGE_SECONDS`).
- Security: loopback bind; Streamlit XSRF/CORS defaults not overridden (verify current defaults via context7 in review); residual DNS-rebinding risk (ADR-004); no uploads; no URL fetch from user input; `unsafe_allow_html` not used in main.py or pages (grep 2026-10-25).
- Performance: no budget. History replays every day since 2022 with per-day pandas filtering and one `get_price` per asset per snapshot day; a cold price cache means one Binance request per uncached day (audit: Backtest cold start > 60 s). Acceptable at SPEC scale (one user, < 10k rows).
- i18n: none; Backtest and Guide pages in Russian, rest English.
- Observability: none; `gatherUsageStats = false`.

### 7.1 Finance data rules status (family `_family.md`)
| Rule | Status | Evidence / gap |
|---|---|---|
| Point-in-time | Done for the ledger: snapshot at day t uses prices of day t and transactions dated <= t; income is credited only after month end. Not done for backtests: signal and fill use the same daily close | portfolio_calculator.py day loop; SPEC section 8 "signal and fill on the same bar's close" |
| Survivorship | N/A for holdings (only the owner's assets). Alt MN backtest universe = today's symbol list, so delisted coins are missing (optimistic bias, not stated in the UI) | backtest page default symbols; known debt D10 |
| Corporate actions | N/A (spot crypto, no splits/dividends). Ticker migrations (for example a renamed token) are not handled: old symbol prices simply fail -> asset dropped from totals | price_fetcher symbol normalization only |
| Timestamps / timezones | NOT done: `get_price` builds `since` from a naive local midnight and matches candles by `datetime.fromtimestamp` (local time), while Binance daily candles open at 00:00 UTC; backtest loaders use UTC (`pd.to_datetime(unit="ms")`). Dates are stored as naive `YYYY-MM-DD` text | price_fetcher.py `get_price`, `find_dates_by_price`; debt D7 |
| Quality gates | NOT done: no monotonic/duplicate/zero-price/OHLC checks; `get_price` falls back to the last candle when the day is missing; today's in-progress candle close is cached forever; backtest funding gaps are forward-filled (`ffill().fillna(0.0001)`) without a note unless the whole request failed | price_fetcher.py, backtest_data.py; debts D6, D8 |
| Vendor terms | Recorded in SPEC section 5: Binance public data, personal use, no redistribution | SPEC |
| Raw immutable / data hash | NOT done: JSON cache is mutable, no manifest/hash (ADR-001) | data/cache |
| Seeds / reproducibility | Partial: synthetic data uses fixed seeds 42/43 via legacy global `np.random.seed`; no run folders, no config files | backtest_data.py |
| Annualization | Not correct for this data: sqrt(252)/252 on a sparse, 365-day series (debt D1) | metrics.py, backtest_*.py |

### 7.2 Known debt (recorded, NOT fixed; any fix is an owner decision and tier A test-first)
| id | Debt | Where | SPEC ref |
|---|---|---|---|
| D1 | Metrics annualize with 252 periods on a sparse series (rows only on transaction days, month starts, last day); crypto trades 365 days; volatility/Sharpe/Sortino are not standard figures | metrics.py | F8, section 8, audit note N-01 |
| D2 | History start hard-coded to 2022-01-01; earlier transactions are never applied | portfolio_calculator.py signature | F7, AC7.7 |
| D3 | Disclaimer missing in README and UI | README.md, main.py, pages | F15 |
| D4 | `get_current_portfolio` moves USDT on crypto trades, `get_portfolio_at_date` does not: the two disagree on USDT, and Position Percentage input uses the latter | database.py | F2, section 8 |
| D5 | Income of the last (current) month is shown in the income columns but not added to `total_value` | portfolio_calculator.py tail block | F7 |
| D6 | Price cache never expires and stores today's in-progress candle; missing day falls back to the last candle | price_fetcher.py | F3 |
| D7 | Local-time vs UTC day mapping for Binance candles | price_fetcher.py | F3, F4 |
| D8 | Backtest funding gaps forward-filled silently; `show_data_source` hides notes on non-synthetic frames | backtest_data.py, pages/backtest.py | F10 |
| D9 | Snapshot errors swallowed; asset without a price excluded from the day's total without warning | portfolio_calculator.py | F7, AC7.6 |
| D10 | Backtests: same-bar signal/fill, no hold-out, walk-forward, trial count or cost sensitivity; survivorship in Alt MN universe | utils/backtest_*.py | F10, non-goals |
| D11 | Sells may drive a position negative; no DB CHECK constraints; delete without confirmation | database.py, pages | F1, F2 |
| D12 | Transitive dependencies unpinned (observed starlette break in the global env) | requirements.txt | ADR-002 |
| D13 | 24 deprecated `use_container_width` uses; 6 mypy errors; duplicate `populate_funding.py`; unsafe `scripts/migrate_database.py` | main.py, pages, utils, scripts | section 3 |

### 7.3 Trace: SPEC features -> components
| Feature | Components | Tables / files |
|---|---|---|
| F1 Transaction ledger | pages/transactions.py, utils/database.py, utils/price_fetcher.py | transactions |
| F2 Holdings and dashboard | main.py, utils/database.py (`get_current_portfolio`, `get_portfolio_at_date`), price_fetcher | transactions |
| F3 Market-data access | utils/price_fetcher.py, utils/assets.py | data/cache/*.json |
| F4 Price discovery | pages/transactions.py, `find_dates_by_price` | none |
| F5 Coin-M funding inputs | pages/funding.py, utils/database.py | funding_rates |
| F6 USDT pool inputs | pages/pools.py, utils/database.py | pool_rates |
| F7 Portfolio value history | utils/portfolio_calculator.py | transactions, funding_rates, pool_rates, price cache |
| F8 Performance metrics | utils/metrics.py | none (derived) |
| F9 Analytics page | pages/analytics.py | via F7, F8 |
| F10 Backtests | pages/backtest.py, utils/backtest_data.py, backtest_funding_arb.py, backtest_alt_mn.py | none (Binance or synthetic) |
| F11 Backtest guide page | pages/guide.py | none |
| F12 DB init and safe migration | utils/database.py (`init_database`, `_drop_legacy_amount_column`) | all four tables, *.bak |
| F13 Local-only runtime | .streamlit/config.toml, .gitignore | data/ ignored |
| F14 Helper scripts | scripts/*.py, populate_funding.py | funding_rates (REAL DB) |
| F15 Disclaimer | README.md, main.py, pages/backtest.py (gap) | none |

## 8. Environments and ports
- Only `local` (owner's Windows machine); no staging, no prod, no Docker, no deploy.
- App: Streamlit on `127.0.0.1:8501` (default port; `server.port` not set; `server.address = "127.0.0.1"` in `.streamlit/config.toml`). Do not set `STREAMLIT_SERVER_ADDRESS` or pass `--server.address 0.0.0.0`; `STREAMLIT_SERVER_PORT` may be used to move the port. No database server, so no DB port (no 5432/5433 clash).
- Dev DB: `data/portfolio.db` (personal, never opened by agents or tests).
- Test DB: pytest fixture `db` in `tests/conftest.py` monkeypatches `utils.database.DB_PATH` to `tmp_path/test.db` and runs `init_database()`; migration tests build their own tmp files. Network is never called: `get_price` is monkeypatched in calculator tests.
- Secrets / env var names: none required (no API keys; `.env.example` not needed). Reserved names if ever introduced: none today; any future exchange key would follow the family rule (read-only key, `.env` gitignored, names only in `.env.example`).
- Environment setup: project `.venv` from `requirements-dev.txt` (plan T18); the global interpreter is not a valid test environment (ADR-002).

## 9. Testing strategy
Run: `python -m pytest -q` (21 passed on 2026-10-25, 1.03 s).
| Area | Tier | Tests today | Gap (plan) |
|---|---|---|---|
| Ledger replay, holdings (F1, F2) | A | 6 in test_database.py | stored-row check AC1.1, D4 characterization (T19) |
| Migration (F12) | A | 2 | AC12.1 idempotence, AC12.4, AC12.5 (T19) |
| History, pool/funding income (F7) | A | 3 in test_portfolio_calculator.py | AC7.4-AC7.7, D5 characterization (T20) |
| Metrics (F8) | B | 9 in test_metrics.py | AC8.7-AC8.9, D1 characterization (T21) |
| Market data (F3, F4) | B | none | mocked ccxt + tmp cache (T22) |
| Backtests (F10) | B | none | synthetic, mocked loaders (T23) |
| Rate inputs, scripts (F5, F6, F14) | B | upsert only | auto-populate counts with tmp DB (T24) |
| Pages (F1-F11, F15) | C | none committed | Streamlit `AppTest` with tmp DB and mocked prices (T25, T26) |
| Runtime/security (F13) | B | none | config/ignore/no-secret checks (T27); netstat in QA |
Rules: tests never touch `data/portfolio.db` or the network; Binance responses only as recorded/mocked fixtures; one read-only real-data smoke (Binance prices, not the personal DB) in QA because fixtures simpler than real data hide bugs (known-traps, Process).

## 10. Risks and applied traps
| Trap / risk | Where it applies | Decision |
|---|---|---|
| known-traps Environment: Postgres port 5432 clash, DB ports on loopback | no DB server (SQLite file) | not applicable; nothing listens except Streamlit on 127.0.0.1:8501 |
| known-traps Environment: Compose `.env` vs `.env.local`, stale volume password | no Docker, no env files | not applicable |
| known-traps Environment: PowerShell `>` corrupts binary output | DB backups | back up `portfolio.db` by file copy or `sqlite3.backup` (as the migration does), never by shell redirection |
| known-traps Data/ORM (drizzle, zod, ILIKE, extensions) | no ORM, no Postgres, no LIKE on user input | not applicable; keep parameterized `?` SQL |
| known-traps Security: localhost apps reachable cross-origin (CSRF, DNS rebinding) | Streamlit on loopback with destructive buttons | loopback bind (ADR-004); Streamlit XSRF/CORS defaults kept; no Host allow-list available: residual risk listed for security review |
| known-traps Security: SSRF, `javascript:` URLs, SVG uploads | no user URL fetch, no uploads, no user links | not applicable |
| known-traps Process: rate-limit cuts, STATE per step | all tasks | every task ends with check -> plan tick -> STATE line -> local commit |
| known-traps Process: parallel agents on the same files | test backlog | plan group g1 uses one new test file per task; `tests/conftest.py` owned by T18 only |
| known-traps Process: run the production build early | Streamlit has no build | "build" = `compileall` + pytest (T01, every phase gate); page smoke via AppTest in T25/T26 |
| known-traps Process: fixtures simpler than real data | ccxt mocks | QA runs one read-only real Binance smoke |
| known-traps Process: `.env.example` real values | no env file | not applicable |
| Family: annualization (sqrt 252 vs 365) | metrics, backtests | documented as D1; no silent change |
| Family: free-vendor data gaps forward-filled; timezone shifts | price_fetcher, backtest_data | documented D6-D8; owner decides on fixes |
| Family: same-close signal and fill, no hold-out, best-of-N | backtests | declared exploratory (SPEC non-goal); synthetic flag mandatory (CLAUDE.md) |
| Family: secrets and exchange keys | none used | AC13.4 check: no `getenv`/API key in code |
| Family: disclaimer in README and UI | F15 | gap D3; plan T29 |
| Router: raw sample covariance, corner solutions, VaR confidence, rebalancing costs | no optimizer/VaR/rebalance | not applicable (ADR-001); estimator choice (shrinkage) becomes mandatory only if an allocation feature is added |
| Windows: Python Store stub, `encoding="utf-8"` | file IO | JSON caches already read/written with `encoding='utf-8'`; keep it for any new file IO |

## 11. ADRs
- ADR-001 SQLite + pandas, no DuckDB/parquet, no skfolio/riskfolio -> `docs/adr/001-sqlite-pandas-no-duckdb-no-optimizer.md` (proposed, router deviation, awaiting owner ok)
- ADR-002 pip + requirements pins instead of uv -> `docs/adr/002-pip-requirements-pins-instead-of-uv.md` (proposed, router deviation, awaiting owner ok)
- ADR-003 No strict typing / validation tooling -> `docs/adr/003-typing-and-validation-tooling-not-strict.md` (proposed, router deviation, awaiting owner ok)
- ADR-004 Streamlit local-only, no auth -> `docs/adr/004-streamlit-local-only-no-auth.md` (accepted)
