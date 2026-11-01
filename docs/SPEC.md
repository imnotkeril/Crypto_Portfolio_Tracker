# SPEC — Crypto Portfolio Tracker

Status: reverse-engineered by agent 2026-10-25, pending owner approval
Written by `analyst` in ADOPTION mode: this document describes what the product really does today (read from code, tests, README, audit), not aspirations. No idea file exists; the owner could not be questioned, so every unknown is a default in section 9. Family: finance / portfolio-risk (tracker variant, no optimizer). Sources read: `README.md`, `CLAUDE.md`, `docs/AUDIT_2026-10-24.md`, `docs/plan.md`, `docs/STATE.md`, `main.py`, `pages/*.py`, `utils/*.py`, `scripts/*.py`, `populate_funding.py`, `tests/*.py`, `requirements.txt`, `.streamlit/config.toml`, `.gitignore`.

AC legend: `[x]` covered by an existing test in `tests/` (21 tests, `python -m pytest -q`); `[~]` partially covered (what is asserted is stated); `[ ]` not covered by any committed test (checked by a stated pytest to be written or by a Streamlit page step).

Disclaimer (required by the finance family; NOT present in the app or README today, see F15): "Research and educational tool. Not investment advice. Simulated and historical results do not guarantee future results; trading can lose all capital."

## 1. Idea restated
A local, single-owner Streamlit app that records the owner's crypto buys and sells (priced from Binance public daily candles), tracks Coin-M funding income and USDT pool yield as monthly percentage inputs, rebuilds the portfolio value history in USDT, and shows return/risk metrics and charts. A secondary Backtest page runs two exploratory strategies (funding-rate arbitrage, alt market-neutral) on Binance or explicitly flagged synthetic data. Source: reverse-engineered from the repository (no `idea.md`); the README is the owner's own description.

## 2. Users and jobs
| User | Job to be done | Frequency / context |
|---|---|---|
| Owner (single person, personal funds only) | Log every buy/sell with the historical price filled automatically | Whenever a trade happens, or in bulk when reconstructing history from 2022 |
| Owner | See current holdings and total value in USDT | Ad hoc, main page |
| Owner | Record monthly Coin-M funding % and USDT pool APY so passive income is included in performance | Monthly, or once via auto-populate estimates |
| Owner | Read performance metrics (total/annual/avg monthly return, volatility, Sharpe, Sortino, drawdowns) and charts | Ad hoc, Analytics page |
| Owner | Find the dates when a price level was touched, to reconstruct an unlogged transaction | Rare, Transactions page |
| Owner | Try funding-arb and alt market-neutral ideas on historical or synthetic data | Rare, research only |

## 3. Scope
- **MVP (must; exists today):** F1 transaction ledger, F2 holdings and dashboard, F3 market-data access, F5 funding inputs, F6 pool inputs, F7 portfolio history, F8 metrics, F9 analytics page, F12 database init and safe migration, F13 local-only runtime.
- **Next (should; exists today but secondary, or a known gap):** F4 price discovery, F10 backtests, F11 backtest guide page, F14 helper scripts, F15 disclaimer (gap, not implemented). Open items from `docs/plan.md` stay as tech debt: `width='stretch'` replacement for 24 deprecated `use_container_width` uses, mypy (8) and ruff style cleanup, duplicate `populate_funding.py`, tests for backtest engines and `price_fetcher`, one real-data backtest run.
- **Non-goals (will not do):**
  - Authentication, multi-user, hosting, Docker, external database (local-only, loopback bind; hosting would need auth, Dockerfile and a server database, owner decision pending).
  - Portfolio optimizer, weights/rebalance orders, risk limits, VaR/CVaR, stress tests, volatility target, benchmark comparison: none exist in code and none are promised. Router defaults for these (max weight 20-25 percent, 5-point drift rebalance, 95/99 percent CVaR, 60/40 benchmark) are therefore not adopted.
  - Order placement, exchange API keys, private endpoints, any trading (public market data only).
  - Multi-currency or FX: base currency is USDT only; every value is a USDT amount.
  - Tax, accounting or investment advice; managing other people's money.
  - A validated research process for the backtests (walk-forward, hold-out, deflated Sharpe, trial counting): not implemented; backtest output is exploratory only.
  - Mobile layout, i18n, accessibility work.
- Platform / locale / scale / deadline: Python 3.11+ (pandas 3 requirement) on the owner's machine (Windows), `streamlit run main.py` on `127.0.0.1`; UI text is English except `pages/backtest.py` and `pages/guide.py`, which are Russian; one user, hundreds to low thousands of rows; no deadline. Base currency USDT; benchmark: none; risk-free rate default 0 percent; annualization uses 252 periods.

## 4. Features and acceptance criteria
Priority P1 = MVP, P2 = next. Test paths refer to files in `tests/`; "to write" means no committed test exists. Any new test must monkeypatch `utils.database.DB_PATH` to a temp file (fixture `db` in `tests/conftest.py`) and mock `utils.price_fetcher` network calls; never touch `data/portfolio.db`.

### F1 Transaction ledger (P1)
Behaviour: page `pages/transactions.py`. Add a buy/sell for any Binance USDT asset or USDT itself on a chosen date (default today). Three input methods: Asset Quantity, Position Percentage (percent of the position held at that date), USDT Amount. Price is fetched from Binance daily close for the date, or entered manually; USDT transactions always use price 1.0. Stored fields: date, asset, type, quantity, price, value (USDT). Errors stop the save: quantity or amount <= 0, percentage <= 0, position 0 for percentage mode, price fetch failure with auto price on (user must enter a manual price). Transaction history is shown sorted by date, then by price within a day (buys high-to-low, sells low-to-high), with a per-asset summary (bought, sold, net, spent, received, simple mean buy/sell price). One transaction can be deleted by selecting it. There is no edit and no confirmation prompt on delete.
Acceptance (Given / When / Then):
- [~] AC1.1 Given an empty database When `add_transaction("2024-01-02","BTC","buy",0.1,40000,4000)` is called Then `get_transactions()` returns that row with the same values (partly covered: `test_database.py::test_buy_sell_flow` asserts only the resulting `get_current_portfolio()` quantities, not the stored row; `test_delete_transaction` reads the row id).
- [x] AC1.2 Given one stored transaction When `delete_transaction(id)` is called Then `get_transactions()` is empty (`test_database.py::test_delete_transaction`).
- [ ] AC1.3 Given the Transactions page, method Asset Quantity, quantity 0.1 BTC, automatic price on, Binance reachable When "Add Transaction" is clicked Then a row is stored with price equal to the Binance daily close of the chosen date, value = 0.1 x price, and the new row appears in Transaction History (the success message is cleared by `st.rerun()`, `pages/transactions.py:361-362`) (page step; or pytest with mocked `get_price`).
- [ ] AC1.4 Given method USDT Amount, asset ETH, amount 1000, price 2000 When the transaction is added Then quantity stored is 0.5 and value is 1000 (page step).
- [ ] AC1.5 Given method Position Percentage and an asset whose position on the chosen date is 0 When "Add Transaction" is clicked Then the error "position is 0. Add a buy first." is shown and nothing is stored; for asset USDT the warning "For USDT, use USDT amount input" is shown (page step).
- [ ] AC1.6 Given automatic price on and `get_price` returns None (Binance unreachable) When "Add Transaction" is clicked Then an error "Failed to get price ... enter price manually" is shown and no row is stored; with manual price > 0 the row is stored with that price (page step with network disabled).
- [ ] AC1.7 Given quantity 0 (or amount 0) When "Add Transaction" is clicked Then "Specify quantity" (or "Specify USDT amount") is shown and nothing is stored (page step).
- [ ] AC1.8 Given two transactions on the same day, buy at 90 and buy at 100 When the history table renders Then the buy at 100 is listed first (page step).

### F2 Holdings and dashboard (P1)
Behaviour: `get_current_portfolio()` replays all transactions ordered by date: a buy adds the quantity; for a non-USDT asset it also subtracts the value from USDT only if USDT >= value (otherwise USDT is left unchanged, no error, USDT never goes negative from a buy); a sell subtracts the quantity (a sell may drive an asset negative, no validation) and, for non-USDT assets, adds the value to USDT. USDT is always present. `get_portfolio_at_date(date)` replays only transactions with date <= the given date and changes quantities only for the transaction's own asset (it does not move USDT for crypto trades, so its USDT figure differs from `get_current_portfolio`). Main page `main.py`: per-asset metric cards (USDT first, 4 per row), live price from Binance (shown as a dash if unavailable; an asset without a price is excluded from Total Value), Total Value in USD-equivalent USDT, buy/sell counts, last 5 transactions, a value-history chart (info message instead of the chart on any error).
Acceptance:
- [x] AC2.1 Given no transactions When `get_current_portfolio()` is called Then it returns `{"USDT": 0.0}` (`test_empty_portfolio`).
- [x] AC2.2 Given buy 5000 USDT, buy 0.1 BTC for 4000, sell 0.04 BTC for 2000 When `get_current_portfolio()` is called Then BTC is 0.06 and USDT is 3000 (`test_buy_sell_flow`).
- [x] AC2.3 Given only a buy of 1 BTC worth 40000 and USDT balance 0 When `get_current_portfolio()` is called Then BTC is 1 and USDT is 0.0, not negative (`test_buy_without_enough_usdt_does_not_go_negative`).
- [x] AC2.4 Given a transaction in an asset never seen before (SOL) When `get_current_portfolio()` is called Then SOL appears as a key (`test_dynamic_assets`).
- [x] AC2.5 Given buys on 2024-01-01 and 2024-03-01 When `get_portfolio_at_date("2024-02-01")` is called Then only the first counts, and a date before the first transaction returns `{"USDT": 0.0}` (`test_portfolio_at_date_ignores_future`).
- [ ] AC2.6 Given stored transactions and Binance reachable When the main page opens Then each asset has a card, "Total Value" equals USDT + sum(quantity x live price), and an asset whose price fetch fails shows a dash and adds nothing to the total (page step; or pytest with AppTest and mocked `get_current_price`).
- [ ] AC2.7 Given no transactions When the main page opens Then it renders with USDT 0.00, Total Value $0.00 and no Quick Statistics block, without an exception (page step; the audit ran an AppTest of all 7 pages without exceptions, not committed).

### F3 Market-data access (P1)
Behaviour: `utils/price_fetcher.py` and `utils/assets.py`. Source: Binance spot public endpoints through `ccxt` (no API key). `get_price(symbol, 'YYYY-MM-DD')` returns the daily close, caches it forever in `data/cache/price_cache.json` (key `SYMBOL/USDT_date`), and returns None on any error (error printed to console). If the exact day candle is missing it returns the last candle fetched. `get_current_price` returns the last ticker or None. `get_price_range` calls `get_price` once per calendar day. `get_available_assets` returns the Binance active `/USDT` bases, cached 24 h in `data/cache/binance_usdt_assets.json`, and falls back to a built-in list of 39 assets when Binance is unreachable. Data license: Binance public market-data endpoints, personal non-commercial use; no redistribution (see section 8).
Acceptance:
- [ ] AC3.1 Given a cache entry for BTC/USDT on 2024-01-01 When `get_price("BTC","2024-01-01")` is called Then the cached float is returned and ccxt is not called (pytest to write, patch `CACHE_FILE` to tmp and `_get_ccxt`).
- [ ] AC3.2 Given no cache entry and a mocked exchange returning a candle for that day When `get_price` is called Then it returns the candle close and writes the entry to the cache file (pytest to write).
- [ ] AC3.3 Given a mocked exchange that raises When `get_price` or `get_current_price` is called Then it returns None and does not raise (pytest to write).
- [ ] AC3.4 Given no network and no cache file When `get_available_assets()` is called Then it returns a list containing "BTC", "ETH" and "USDT" (the fallback list) (pytest to write).
- [ ] AC3.5 Given a symbol without "/" When any price function is called Then "/USDT" is appended and the symbol is upper-cased (pytest to write).

### F4 Price discovery by target price (P2)
Behaviour: on the Transactions page, mode "By Target Price": asset, buy or sell, target price, year (2020-2030), month. `find_dates_by_price` fetches that month's daily candles and returns days where low <= target <= high (same rule for buy and sell), with match_type `exact` when the close is within 2 percent of the target, else `high_low`, and price_diff_pct from the low/close (buy) or high/close (sell); result sorted by closeness, displayed sorted by date. The chosen date becomes the transaction date and the target price can be used as the stored price. Nothing is shown for USDT or target 0.
Acceptance:
- [ ] AC4.1 Given a mocked month of candles where only day 10 has low <= 50000 <= high When `find_dates_by_price("BTC",50000,"buy",2024,1)` is called Then the frame has exactly one row dated that day (pytest to write).
- [ ] AC4.2 Given a day whose close is within 2 percent of the target and another day that only touches it intraday When the function runs Then the first row has match_type `exact` and the second `high_low` (pytest to write).
- [ ] AC4.3 Given no day in the month touches the target When "Find Matching Dates" is clicked Then a warning "No matching dates found" is shown and no date list appears (page step).
- [ ] AC4.4 Given ccxt raises When the function runs Then it returns an empty frame with the six expected columns and does not raise (pytest to write).

### F5 Coin-M funding inputs (P1)
Behaviour: page `pages/funding.py`, table `funding_rates` (year, month, asset, percentage) with unique (year, month, asset); saving an existing key replaces it. `percentage` is an ANNUAL funding rate in percent; monthly income is computed in F7. Manual add needs percentage > 0 (year 2022-2030). The button "Auto-populate average values (2022-2025)" writes hard-coded ESTIMATES (not market data) for BTC and ETH: BTC 7.5/6.5/5.5/5.0 and ETH 8.0/7.0/6.0/5.5 percent for 2022/2023/2024/2025, months 1..12 for 2022-2024 and, for 2025, months 1..(current calendar month number) because the loop compares against today's month (quirk: run in October 2026 it fills Jan-Oct 2025 only). Also shows history, average by asset, yearly pivot, and delete by selection (no confirmation).
Acceptance:
- [x] AC5.1 Given a funding row for 2024-01 BTC at 5.0 When `add_funding_rate(2024,1,"BTC",7.0)` is called Then exactly one row exists with percentage 7.0 (`test_rates_upsert`).
- [ ] AC5.2 Given percentage 0 on the Funding page When "Add Funding" is clicked Then "Specify funding percentage" is shown and nothing is stored (page step).
- [ ] AC5.3 Given an empty funding table, clock fixed to 2025-10-15 When the auto-populate loop runs Then 2 assets x (36 + 10) = 92 rows exist and every row is an estimate from the table above (pytest to write after extracting the loop, or page step: click the button and count rows in History).
- [ ] AC5.4 Given a stored funding row When it is selected and "Delete" is clicked Then the row disappears from the history (page step; pytest on `delete_funding_rate` to write).

### F6 USDT pool inputs (P1)
Behaviour: page `pages/pools.py`, table `pool_rates` (year, month, apy) unique (year, month), replace on conflict. APY in percent, must be > 0 to save. Auto-populate writes ESTIMATES: APY 8.0/6.5/5.0/4.5 for 2022/2023/2024/2025 with the same month-limit quirk as F5. Shows history, average and range, yearly average, an APY line chart, delete by selection. Pool balance is not entered; it is derived in F7.
Acceptance:
- [x] AC6.1 Given a pool row for 2024-01 at 5.0 When `add_pool_rate(2024,1,6.0)` is called Then exactly one row exists for that month (`test_rates_upsert`).
- [ ] AC6.2 Given APY 0 When "Add Pool" is clicked Then "Specify APY" is shown and nothing is stored (page step).
- [ ] AC6.3 Given an empty pool table, clock fixed to 2025-10-15 When the auto-populate loop runs Then 46 rows exist with the APY of each year (page step: click and count; pytest to write).
- [ ] AC6.4 Given stored pool rows When the Pools page opens Then Average APY, APY Range, yearly table and the APY chart render without an exception (page step).

### F7 Portfolio value history (P1)
Behaviour: `calculate_portfolio_history(start_date="2022-01-01", end_date=today)` walks every calendar day from the start date (hard-coded 2022-01-01; transactions dated earlier are never applied, later ones than today are ignored) and returns a DataFrame indexed by date with `total_value`, `assets_value` (JSON), `pool_balance`, `funding_income`, `pool_income`, `BTC_value`, `ETH_value`, `USDT_value`. Rows are written only on days with a transaction, on the 1st of each month, and on the last day, so the series is sparse, not daily. Rules: a sell of any asset moves its USDT value into the "pool" balance (assumed to earn the pool APY); a buy first consumes pool balance, then USDT (only if USDT covers the remainder). Valuation uses `get_price` per asset per snapshot day; an asset with no price is left out of that day's total. At each month rollover: funding income = sum over assets with a funding row of (average position during the month x price on the 16th of the month x annual percentage / 100 / 12); pool income = average daily pool balance x APY / 100 / 12; both are added to USDT at the rollover. Income of the last (current) month is reported in the income columns but not added to `total_value`. Without transactions an empty frame with columns `date, total_value` is returned.
Acceptance:
- [~] AC7.1 Given no transactions When `calculate_portfolio_history` is called Then it returns a DataFrame without raising (`test_no_transactions_returns_frame` asserts only the type; emptiness and columns are not asserted).
- [x] AC7.2 Given 5000 USDT deposited then 0.1 BTC bought at a constant price of 100 for 10 USDT When the history is built to month end Then the last `total_value` is 5000 and `BTC_value` is 10 (`test_total_value_conserved_on_buy_at_market`).
- [x] AC7.3 Given 1200 USDT, a BTC buy and a sell of the same value in January 2024 and a January pool APY of 12 When the history runs into February Then the last `total_value` exceeds 1200, showing pool income was credited (`test_pool_income_added_after_month_end`; the exact amount is not asserted).
- [ ] AC7.4 Given an average BTC position of 1 during January, price 100 on 2024-01-16 and a January funding row of 12 percent When the history runs past 2024-01-31 Then `funding_income` for January equals 1 x 100 x 12 / 100 / 12 = 1.0 and USDT rises by 1.0 (pytest to write).
- [ ] AC7.5 Given pool balance 500 and a buy worth 300 When the buy is processed Then the pool balance becomes 200 and USDT is unchanged (pytest to write).
- [ ] AC7.6 Given `get_price` returns None for ETH When a snapshot is built Then ETH is absent from `assets_value` and total_value excludes it (pytest to write; documents a known understatement).
- [ ] AC7.7 Given a transaction dated 2021-12-31 and default start 2022-01-01 When the history is built Then that transaction is not applied (pytest to write; documents the hard-coded start).

### F8 Performance metrics (P1)
Behaviour: `utils/metrics.py`, input is the `total_value` series. Returns are simple period-to-period percentage changes between consecutive rows (first = 0). Volatility = std x sqrt(252) x 100; Sharpe = (mean x 252 - rf/100) / (std x sqrt(252)) with rf default 0; Sortino uses the std of negative returns only and returns the sentinel 999.0 when there are no negative returns and the mean is positive. Annual return = compound growth over (last date - first date) / 365.25 years from the first non-zero value; total return uses the first non-zero value; monthly and yearly returns resample with `ME` and `YE` (fixed for pandas 3); max drawdown returns (percent, peak date, trough date); zero, NaN, inf and short series return 0.0 and never raise.
Acceptance:
- [x] AC8.1 Given initial 100 and current 150 When `calculate_total_return` runs Then 50; initial 0 or NaN gives 0.0 (`test_total_return`).
- [x] AC8.2 Given values 100, 110, 99 When `calculate_returns` runs Then the first return is 0 and the second 0.1 (`test_returns_first_is_zero`).
- [x] AC8.3 Given values 100, 200, 100, 150 When `calculate_max_drawdown` runs Then 50 percent, peak 2024-01-02, trough 2024-01-03; a single value returns `(0.0, "", "")` (`test_max_drawdown`, `test_max_drawdown_short_series`).
- [x] AC8.4 Given a constant or one-element return series When `calculate_volatility` runs Then 0.0; annualized equals non-annualized x sqrt(252) (`test_volatility_constant_is_zero_and_short_safe`, `test_volatility_annualization`).
- [x] AC8.5 Given zero-variance returns When `calculate_sharpe_ratio` runs Then 0.0; given positive drift with variance Then > 0 (`test_sharpe_zero_std`, `test_sharpe_positive_for_positive_drift`).
- [x] AC8.6 Given values 0, 0, 100, 110, 121, 90, 130 then flat for 30 days When `calculate_all_metrics` runs Then every headline metric is finite, total_return is 30 (first non-zero is 100) and max_drawdown is (121-90)/121 x 100 (`test_all_metrics_keys_and_values`; also exercises the `ME`/`YE` resample).
- [ ] AC8.7 Given returns with no negative element and a positive mean When `calculate_sortino_ratio` runs Then 999.0 (pytest to write).
- [ ] AC8.8 Given values doubling over exactly 365.25 days When `calculate_annual_return` runs Then about 100.0 (pytest to write).
- [ ] AC8.9 Given fewer than two months with positive values When `calculate_monthly_returns` runs Then an empty float series (pytest to write).

### F9 Analytics page (P1)
Behaviour: `pages/analytics.py` calls F7 then F8 and shows: key metrics (total return, average annual, average monthly, volatility, max drawdown, average drawdown, Sharpe, Sortino; Sharpe/Sortino display "N/A" when they equal 0.00), monthly-return heatmap, yearly-return bars, cumulative return + drawdown chart, portfolio value chart, per-asset price chart with buy/sell markers (one price lookup per day of the asset's transaction range, cached), composition bar and pie (latest snapshot, positive values only), and a funding/pool income block (totals, percent of current value, monthly and cumulative charts, monthly table). With no history it shows a warning and stops. Chart labels contain one Russian string (`цена`).
Acceptance:
- [ ] AC9.1 Given no transactions When the Analytics page opens Then the warning "No data for analysis. Add transactions on the 'Transactions' page." is shown and nothing else renders (page step).
- [ ] AC9.2 Given a few transactions When the page opens Then eight metric tiles render without an exception and Sharpe/Sortino show "N/A" if they are 0.00 (page step; Streamlit `AppTest` run to write).
- [ ] AC9.3 Given funding and pool rows plus a BTC position and a sale When the page opens Then the "Funding and Pool Income" block shows non-zero totals and the total equals the sum of the monthly values in the breakdown table (page step).
- [ ] AC9.4 Given only USDT transactions When the asset chart section renders Then the selector offers BTC and ETH as placeholders and no exception occurs (page step; observed in code, not run).

### F10 Backtests: funding arb and alt market-neutral (P2)
Behaviour: `pages/backtest.py`, `utils/backtest_data.py`, `utils/backtest_funding_arb.py`, `utils/backtest_alt_mn.py`; exploratory, results are not validated research. Data origin is always declared in `DataFrame.attrs['synthetic']` (bool) and `attrs['notes']` (list of reasons): user-requested synthetic data (fixed seeds 42 and 43, reproducible); spot or perp prices unavailable from Binance means the ENTIRE dataset is synthetic; funding history unavailable means constant funding_8h = 0.0001 assumed and the frame is flagged synthetic. The page shows a warning "SYNTHETIC / ASSUMED DATA - results are NOT a real backtest." when flagged, otherwise the caption "Data source: Binance (real historical data)." Funding arb: daily bars, long spot and short perp, opens when funding_8h > threshold with notional = equity x target percent (margin = notional / leverage must fit equity), closes when |basis| > stop-loss percent or funding_8h < stay-minimum, funding paid once per day as notional x rate x 3, fees and slippage on both legs, liquidation when equity / margin < 5 percent. Alt market-neutral: needs BTC and at least 10 symbols with momentum; long top quantile and short bottom quantile of cross-sectional momentum z-score, weights 0.5 long / -0.5 short normalized with a BTC hedge from rolling OLS beta, rebalance every N days, cost = gross weight x (fee + slippage) charged at each rebalance. Metrics: total return, annualized return, volatility (sqrt 252), Sharpe (annual return / volatility, rf 0), max drawdown, final equity; funding arb also PnL split (funding, basis, commissions). No walk-forward, hold-out, trial count or sensitivity table is produced.
Acceptance:
- [ ] AC10.1 Given `use_synthetic=True` When `load_funding_arb_data("BTC","2024-01-01","2024-06-30",True)` is called Then the frame has columns `date, spot, perp, funding_8h, is_funding_time` and `attrs['synthetic']` is True with a non-empty `attrs['notes']` (pytest to write; no network).
- [ ] AC10.2 Given a mocked `get_price_range` returning an empty frame When `load_funding_arb_data(..., use_synthetic=False)` is called Then the result is synthetic data with `attrs['synthetic']` True and a note containing "ENTIRE dataset is synthetic" (pytest to write).
- [ ] AC10.3 Given mocked spot and perp data but a failing funding request When the loader runs Then `attrs['synthetic']` is True and the note contains "constant funding_8h=0.0001" (pytest to write).
- [ ] AC10.4 Given start date >= end date When either loader runs Then an empty DataFrame is returned (pytest to write).
- [ ] AC10.5 Given the synthetic funding-arb frame and default parameters When `run_funding_arb_backtest` runs twice Then both runs return identical equity curves and the metric keys include `total_return_pct, sharpe_ratio, max_drawdown_pct, pnl_funding, pnl_basis, pnl_commissions` (pytest to write).
- [ ] AC10.6 Given a funding frame with constant funding_8h 0.0003, spot = perp, zero fees and slippage When the backtest runs Then pnl_funding is positive and pnl_basis is 0 (pytest to write).
- [ ] AC10.7 Given prices without a BTC column, or fewer rows than max(lookback, beta window) + 10 When `run_alt_mn_backtest` runs Then it returns an empty series and `{}` (pytest to write).
- [ ] AC10.8 Given the Backtest page, Funding Arb tab, the synthetic checkbox ticked When "Запустить бэктест (Funding Arb)" is clicked Then "Бэктест выполнен." and the SYNTHETIC / ASSUMED DATA warning appear together with an equity chart (page step; the audit ran this once on synthetic data).
- [ ] AC10.9 Given the Alt MN tab with the default 10 symbols, the synthetic box ticked and a 2024-01-01..2024-06-30 range When the run button is clicked Then metrics and an equity chart render and the warning is shown (page step; the 182-day synthetic range gives more than 100 rows).

### F11 Backtest guide page (P2)
Behaviour: `pages/guide.py` is static Russian text (a production-oriented guide to the two strategies) with reference links; no data access, no external image (the external logo was removed in the audit).
Acceptance:
- [ ] AC11.1 Given the app is running When the "guide" page opens Then it renders without an exception and without network access (page step or `AppTest.from_file("pages/guide.py").run()` to write).
- [ ] AC11.2 Given the repository When `grep -n "st.image\|perplexity" pages/guide.py` is run Then there is no output (command; checked by reading the file on 2026-10-25: no `st.image`, only two documentation links).

### F12 Database initialization and safe migration (P1)
Behaviour: `utils/database.py`, SQLite file `data/portfolio.db` (created with its folder on first use; every function opens its own connection). Tables: `transactions`, `funding_rates`, `pool_rates`, `portfolio_snapshots` (the last is created and has writer/reader functions but nothing in the pages uses it). Legacy `funding_rates`/`pool_rates` tables that still have an `amount` column are migrated on `init_database()`: file backup `portfolio.db.pre-migration-<timestamp>.bak` first, one transaction, row-count check, rollback and raised error on any failure. `scripts/migrate_database.py` is an older, unsafe duplicate (no backup, swallows errors); not used by the app.
Acceptance:
- [~] AC12.1 Given a fresh path When `init_database()` runs Then the four tables exist and all CRUD tests pass on them; running it twice changes nothing (partly covered: the `db` fixture runs `init_database()` once and CRUD tests pass; no test lists the four tables or runs it twice - pytest to write).
- [x] AC12.2 Given a legacy `funding_rates` table with an `amount` column and one NULL percentage When `init_database()` runs Then both rows survive, `amount` is gone, the NULL becomes 0.0, and a `.pre-migration-*.bak` file exists (`test_legacy_migration_keeps_rows_and_makes_backup`).
- [x] AC12.3 Given invalid replacement-table SQL When `_drop_legacy_amount_column` runs Then a `sqlite3.Error` is raised and the old table still has 2 rows (`test_migration_failure_is_raised_and_old_table_kept`).
- [ ] AC12.4 Given a legacy table whose copy would lose rows (duplicate unique keys) When migration runs Then `RuntimeError("... would lose rows ...")` is raised and the old table is kept (pytest to write).
- [ ] AC12.5 Given a legacy `pool_rates` table with `amount` When `init_database()` runs Then it is migrated the same way (pytest to write).

### F13 Local-only, no-auth runtime (P1)
Behaviour: the app has no login and exposes read/write access to financial data, so it must listen on loopback only. `.streamlit/config.toml` (tracked) sets `server.address = "127.0.0.1"`, `gatherUsageStats = false`. No API keys or secrets are used or required; only public Binance endpoints are called. `data/` (database and caches) is git-ignored and never committed.
Acceptance:
- [ ] AC13.1 Given the repository When `grep -n "address" .streamlit/config.toml` is run Then it prints `address = "127.0.0.1"` (command; verified by reading the file 2026-10-25).
- [ ] AC13.2 Given `streamlit run main.py` is running When `netstat -ano | findstr LISTENING` is filtered by the Streamlit port Then the local address is `127.0.0.1:<port>`, not `0.0.0.0` (command; confirmed once in the audit).
- [ ] AC13.3 Given the repository When `git ls-files data` and `git check-ignore data/portfolio.db` are run Then the first prints nothing and the second prints the path (command).
- [ ] AC13.4 Given the source tree When `grep -rnE "apiKey|API_KEY|getenv|os.environ" --include=*.py .` is run Then there is no output (command; 0 matches on 2026-10-25).

### F14 Helper scripts (P2)
Behaviour: `scripts/auto_populate_funding.py` and the near-identical root `populate_funding.py` write the same estimated funding rows as F5 into the REAL database (`DB_PATH`); `scripts/populate_funding_data.py` offers an interactive choice, but its "API" option only probes Binance and then falls back to the same estimates (no real funding data is ever stored); `scripts/migrate_database.py` is the legacy migrator (F12). None is called by the app.
Acceptance:
- [ ] AC14.1 Given an empty temporary database (DB_PATH patched) When `auto_populate_funding()` is called Then funding rows exist for BTC and ETH from 2022-01 with the estimate table of F5 (pytest to write; never run the script against `data/portfolio.db` in tests).
- [ ] AC14.2 Given the two populate scripts When their rate tables are compared Then they are identical (command: `diff` of the `funding_rates` dict; today true, duplicated code is listed as debt in `docs/plan.md`).

### F15 Disclaimer (P2, gap: not implemented today)
Behaviour: the finance family requires the disclaimer line (top of this document) in the README and on the first screen or footer of the UI. `grep -ri "not investment advice"` over the project finds 0 matches, so this requirement is currently unmet. Implementing it touches `README.md` and `main.py`/pages and is outside this step.
Acceptance:
- [x] AC15.1 Given the repository When `grep -il "not investment advice" README.md utils/disclaimer.py` is run Then both are listed and `main.py` and `pages/backtest.py` import and render `DISCLAIMER` (`tests/test_disclaimer.py`, commit dc627dd).
- [~] AC15.2 Given the Backtest page with synthetic data When the results render Then the disclaimer text is visible on the page (code path covered by `tests/test_disclaimer.py`; visual page step done in QA).

## 5. Data
Entities (SQLite `data/portfolio.db`, JSON caches in `data/cache/`):
- `transactions`: id, date (TEXT `YYYY-MM-DD`), asset (Binance base symbol or `USDT`), type (`buy`|`sell`), quantity, price (USDT), value (USDT), created_at. No foreign keys; no uniqueness; no check constraints (negative or zero values are not rejected by the database).
- `funding_rates`: id, year, month, asset, percentage (annual percent), created_at; UNIQUE(year, month, asset).
- `pool_rates`: id, year, month, apy (percent), created_at; UNIQUE(year, month).
- `portfolio_snapshots`: id, date UNIQUE, btc/eth/usdt quantity and value, total_value, created_at (unused by the UI).
- Caches: `price_cache.json` (key `SYMBOL/USDT_date` to close price, never expires), `binance_usdt_assets.json` (asset list, 24 h TTL). Both git-ignored.
- Derived, not stored: portfolio history frame (F7), metrics (F8), backtest equity curves and `attrs` flags (F10).
Ownership: one owner, single machine. Retention: indefinite, no deletion policy beyond manual row delete. Backup: manual copy of `data/portfolio.db` (the audit copy lives in `../_backups_crypto_portfolio/`); the app creates `.pre-migration-*.bak` next to the DB on legacy migration.
Sensitive fields: `transactions` (the owner's personal trade history, quantities, prices, dates) is personal financial data; the DB file and any `.bak` copy must never be committed or shared. No PII fields, no credentials, no exchange keys.
Data sources and licence: Binance public REST market data through `ccxt` (spot daily OHLCV and ticker; USDT-M futures daily OHLCV and `fapi/v1/fundingRate` for the backtest). Free public endpoints, not a data licence: personal use only, no redistribution or commercial use without Binance's written terms. Granularity: daily candles, timestamps UTC at the exchange but converted with the local timezone on read (see section 8). Survivorship and point-in-time rules do not apply: only the owner's own assets are priced.

## 6. Modules (from `modules/`)
| Module | Depth (minimal/full) | Why / service rule | Requires |
|---|---|---|---|
| none | n/a | The product is a local single-user tool; no module is wired in. | n/a |

Modules not chosen (all "no" so nobody adds them silently):
| Module | Chosen | Reason |
|---|---|---|
| auth | no | Local-only, loopback bind; hosting is a non-goal (owner decision pending). |
| payments | no | No money movement, no billing. |
| database-server (external DB) | no | SQLite file is enough for one user. |
| notifications | no | No alerts; risk-limit alerts do not exist. |
| background-jobs | no | No scheduler; data is refreshed on page load. |
| legal-compliance | no | Personal use only; becomes mandatory if the tool is ever shared or used for others' funds. |
| ai-feature | no | No LLM calls. |
| analytics / telemetry | no | `gatherUsageStats = false`. |
| i18n | no | English UI, two Russian pages, no translation layer. |

## 7. Design direction
n/a for a design step: the UI is stock Streamlit (wide layout, sidebar page navigation, Plotly charts with green for gains, red for losses, blue/orange/teal accents for assets and income). Reports are on-screen only. No design references were given; no `docs/design.md` is required.

## 8. Constraints and risks
| Risk / constraint | Impact | Mitigation |
|---|---|---|
| Sensitive data: the personal transactions DB (`data/portfolio.db`, `.bak` files, caches) | Privacy loss if committed or shared | `data/` and `*.db` git-ignored; AC13.3 checks tracking; backups outside the repo; never read `data/` in agent runs |
| No authentication; app reads and deletes financial data | Anyone with network access could read or erase the ledger | Loopback bind in tracked `.streamlit/config.toml` (AC13.1, AC13.2); hosting is a non-goal until auth is built |
| Data-loss path: delete buttons without confirmation, no edit, no undo; legacy migration | Lost rows | Manual DB copy before schema change (CLAUDE.md); migration is backed up and row-checked (AC12.2-12.4); QA tier A for F1, F2, F12 |
| Money math without validation: sells can drive a position negative; `get_current_portfolio` silently skips the USDT deduction when USDT is short; `get_portfolio_at_date` does not move USDT | Holdings and percent-of-position inputs can disagree with reality | Behaviour documented in F2; covered by AC2.2, AC2.3; any change to ledger math is tier A, test first |
| Estimated, not real, passive income: funding and pool values are annual percentages entered by hand or auto-filled with hard-coded estimates; auto-populate for 2025 stops at today's month number | Total value and passive income are approximate; Nov-Dec 2025 missing when run in October 2026 | Behaviour documented (F5, F6, F14); estimates never labelled as market data; AC5.3, AC6.3 |
| Sparse history (rows only on transaction days, month starts, last day) with metrics annualized as if daily (sqrt 252, 252 periods; crypto trades 365 days) | Volatility, Sharpe and Sortino are not comparable with standard values and can mislead | Documented in F7, F8 and section 9; known family trap (annualization); fix is a later decision, not silent |
| Price cache never expires and `get_price` caches the in-progress daily candle close for today; fallback returns the last candle when the exact day is absent; day boundaries use local time | Stale or wrong prices stick in the cache | Documented; AC3.1-AC3.3 to write; deleting `data/cache/price_cache.json` rebuilds it |
| Asset missing a price on a snapshot day is left out of total value | Understated value on that day, distorted drawdown and returns | AC7.6 documents it; user sees no warning today |
| Backtests: synthetic or assumed data replaced silently in the past (audit finding 4) | Fabricated results mistaken for real | Fixed: `attrs['synthetic']` and notes, warning banner (AC10.1-AC10.3, AC10.8). Remaining gap: `show_data_source` prints notes only when synthetic, so "No data for: X" notes on a non-synthetic Alt MN frame are not shown |
| Backtest validity limits: signal and fill on the same bar's close, cost charged on gross weight at every rebalance, no hold-out, no walk-forward, no trial count, single run | Results are indicative only; not evidence of future results | Declared a non-goal (section 3); results must not be quoted as performance claims |
| Binance public API: rate limits, outages, regional blocking (ccxt `enableRateLimit` is on); history lookups issue one request per uncached day | Slow first load (the audit saw Backtest cold start above 60 s), partial data | Local cache; errors return None; offline asset fallback list |
| Licence: Binance public data is personal use only; the project is "open source for personal use" with no LICENSE file | Redistribution or commercial reuse is not covered | Personal use only; add a LICENSE and re-check terms before any sharing |
| Dependencies pinned (streamlit 1.66.1, pandas 3.1.0, numpy 2.4.6, plotly 7.1.0, ccxt 4.5.90, python-dateutil 3.0.0, requests 2.34.2, statsmodels 0.15.0); `use_container_width` deprecated (24 uses) | Future Streamlit release can break pages | Pins in `requirements.txt`; cleanup listed in `docs/plan.md` |
| Tests cover 21 cases (database, metrics, portfolio history); price fetcher, backtests and all pages are untested | Regressions in uncovered areas go unnoticed | Section 4 marks every uncovered AC as "to write"; audit AppTest runs were ad hoc and are not committed |
| Mixed locale: Backtest and Guide pages Russian, rest English; one Russian chart label in Analytics | Inconsistent UI | Recorded as an assumption; no change without owner decision |
| Legal: tool is not investment advice and the disclaimer is absent today (F15) | Misreading outputs as advice | Add the disclaimer line (AC15.1, AC15.2); personal use only |
| Known-traps file (`known-traps.md`) not opened in this run | Possible missed item | Re-check at architecture step |

## 9. Assumptions (defaults taken instead of asking)
- The owner is the only user; the data is the owner's own funds; the app is never exposed to a network (consistent with `CLAUDE.md`: local only, no auth). Hosting stays out of scope until the owner says otherwise.
- Base currency is USDT and every figure is a USDT amount, shown with `$` in some places; no FX, no fiat conversion. Benchmark: none exists; none will be added by this spec.
- Annualization: 252 periods per year in metrics and backtests (code behaviour), although crypto trades 365 days and the history rows are sparse; this is documented, not corrected.
- Risk-free rate: 0 percent unless a caller passes one (the UI passes none).
- No numeric portfolio constraints, risk limits, VaR/CVaR, rebalance rule or optimizer exist; the router defaults for portfolio-risk were reviewed and rejected as not part of the product.
- Funding percentages are annual rates and monthly income is annual / 12 on the average position valued at the 16th of the month; pool APY income is annual / 12 on the average pool balance. Both are simplifications accepted by the owner's design (README note: "income calculations are done monthly based on average positions/balances").
- Sell proceeds (any asset) are assumed to sit in a USDT pool earning the monthly pool APY; buys consume the pool first (README: "USDT from sales goes into pools").
- Auto-populated funding and pool values are estimates, not data from Binance or any pool provider; the owner can overwrite them manually.
- `Version: 1.0.0` and "Period: from 2022" in the sidebar are static labels; the 2022-01-01 history start is intentional.
- Priorities: features that feed total value and metrics (F1-F3, F5-F9, F12, F13) are P1; price discovery, backtests, guide, scripts and disclaimer are P2.
- The backtest page being Russian and the README promising a "red warning" (the code uses `st.warning`) are cosmetic; no change implied.
- Tests must use a temp database and mocked prices (per `CLAUDE.md`); backtests must always flag synthetic data via `df.attrs['synthetic']` (per `CLAUDE.md`). Both are standing rules for any future change.
- Scale: single user, under about 10,000 transactions; performance work is out of scope (history calculation loops over every calendar day since 2022 and calls pandas per day, which is acceptable at this size).
- Deadline: none; the open items in `docs/plan.md` are optional.
- The owner's decisions still pending (merge `chore/audit` to `main`, push, local vs hosted) do not change this spec; nothing is pushed.

## 10. Open questions
None.

## 11. Definition of done
Project-level and measurable for the product as it exists, and for any change made against this spec:
- `python -m pytest -q` passes with at least 21 passed, 0 failed, 0 skipped (current baseline), with output pasted; every `[x]` AC maps to a passing test named in the AC.
- Before any change in an area, the `[ ]` ACs of that feature are first turned into pytest tests (or a recorded Streamlit page step with evidence) and pass; tier A areas (F1, F2, F7 ledger and income math, F12 migration) are test-first.
- No test touches `data/portfolio.db` or the network: `git status` shows no change under `data/`, and `grep -rn "portfolio.db" tests` returns only monkeypatched paths.
- `streamlit run main.py` starts, `GET /_stcore/health` returns 200, all seven pages load without an exception (AppTest or browser), and the listening address is `127.0.0.1` (AC13.2).
- Every backtest result built on fabricated or assumed data shows the SYNTHETIC / ASSUMED DATA warning (AC10.1-AC10.3, AC10.8).
- The spec has no unresolved-clarification markers (the template's marker grep prints 0) and `node E:/Main/Dev/coding-brain/scripts/doc-check.mjs --project . --step spec` shows no FAIL other than the owner-approval line.
- The disclaimer line is present in `README.md` and the UI (AC15.1) before the project is shown to anyone else.
- Owner approval is recorded by changing the Status line to `approved by owner on <date>`.
