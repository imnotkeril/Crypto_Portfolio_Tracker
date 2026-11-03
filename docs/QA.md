# QA report — Crypto Portfolio Tracker

Date: 2026-11-01 · Build: `d6febe1` (branch `chore/audit`, local) + this file · Env: no production build exists for a Streamlit app, so the app was run from a clean copy in `D:/Temp/claude/qa_run_crypto/` (own empty throwaway `data/` dir and DB; the repo `data/` was never read or opened by the app) · Author: qa-tester
Verdict: **YELLOW** (not GREEN). All 76 tests pass, 0 failed, 0 skipped, compileall clean, no exception on any of the 7 pages. Not green because: R-01 (P1, tier A, owner decision) is open; the open P2 findings R-09/R-10/R-11 (tier B metrics) are only characterized, not fixed; and 25 of 76 ACs have neither a committed test nor a browser step (list in section 3), including all price-fetcher and backtest-engine ACs (plan T22-T24 still open). The real-browser part (Playwright/browser MCP, 375/768/1440 px, console errors) was NOT done, see section 4.

## 1. Risk map
| Area / feature | Tier | Why | Tests | Result (pass/fail/skip) |
|---|---|---|---|---|
| F1 Ledger: add/get/delete transactions (`utils/database.py`) | A | personal financial data, delete path | `test_database.py`: stored row values, ordering, injection-shaped asset, delete unknown id, delete funding/pool, D11 negative sell | pass |
| F2 Holdings (`get_current_portfolio`, `get_portfolio_at_date`) | A | money state | `test_database.py`: AC2.1-2.5, D4 characterization (USDT 1000 vs 5000), D11 | pass |
| F12 Schema + legacy migration (`init_database`, `_drop_legacy_amount_column`) | A | data migration, can lose rows | `test_database.py`: 4 tables + idempotent 2nd init, legacy funding (rows kept, backup), legacy pool (AC12.5), duplicate keys raise "would lose rows" and old table kept (AC12.4), NULL apy caught by row-count guard, failure keeps old table, 2nd init no new backup | pass |
| F5/F6 Funding and pool rate storage | A | update logic (upsert/delete) | `test_database.py`: upsert, delete only that row | pass |
| F7 History income math (`portfolio_calculator.py`) | A | money math | `test_portfolio_calculator.py`: AC7.1-7.7, time-weighted average position, pool first then USDT, pool income average, R-02 toy (1500, USDT 1400, pool 100), D2, D5, D9 (missing price, exception drops row) | pass |
| F8 Metrics (`metrics.py`) | B | business logic | `test_metrics.py`: AC8.1-8.9, annual return 365/366 days, D1 pinned, R-01/R-09/R-10 characterized | pass |
| F3/F4 Prices, assets, price discovery (`price_fetcher.py`, `assets.py`) | B | external data | `test_assets.py` (USDT offered, 2 tests); price fetcher: none (plan T22 open) | pass; gap |
| F10 Backtests (`backtest_*.py`) | B | research output | `test_backtest_alt_mn.py` (hedge neutrality, 2), `test_backtest_data.py` (pagination, forward-fill flag, 3); engines and loaders otherwise untested (T23 open) | pass; gap |
| F13 Local-only config | B | exposure | `test_config.py` (address, allowedHosts); netstat check | pass |
| F15 Disclaimer | C | legal text | `test_disclaimer.py` (3) + AppTest | pass |
| F2/F9/F10/F11 Streamlit pages | C | UI | AppTest drive of all 7 pages on a throwaway DB (section 4) | pass, 0 exceptions |

Tier-A coverage was not measured (no `pytest-cov` in the venv, none added). Tier-A areas F1, F2, F5/F6 storage, F7 and F12 each have error/idempotency paths listed above. Not tier-A tested: the standalone `scripts/migrate_database.py` (S-03, open) and the populate scripts (T24).

## 2. Commands run
All from the repo root with `./.venv/Scripts/python.exe` (3.11.9), `PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8`. Tests use `tmp_path` DBs via the `db` fixture (`monkeypatch` of `database.DB_PATH`), prices are mocked, so `data/portfolio.db` is not touched.

| Command | Result | Counts |
|---|---|---|
| `python -m pytest -q -p no:cacheprovider -rs` | pass | `76 passed in 5.66s` (0 failed, 0 skipped, no `-rs` skip lines; `grep skip\|xfail tests/` finds only a code comment) |
| per file | pass | assets 2, backtest_alt_mn 2, backtest_data 3, config 1, database 21, disclaimer 3, metrics 25 (24 defs, 1 parametrized x2), portfolio_calculator 19 = 76 |
| `python -m compileall -q main.py pages utils scripts` | pass | exit 0, no output |
| `python -m mypy --ignore-missing-imports utils main.py` (informational) | 8 errors | `Found 8 errors in 4 files (checked 11 source files)`: metrics.py:210, backtest_alt_mn.py:108, backtest_data.py:46 and :109, portfolio_calculator.py:18/45/46/76. Same count as plan T30 baseline; not a gate yet |
| `streamlit run main.py --server.port 28417 --server.headless true` (clean copy) | pass | `netstat`: `TCP 127.0.0.1:28417 LISTENING` only (no 0.0.0.0); `curl /_stcore/health` -> `200` |

Task checks run this session: `tests/test_metrics.py` 25 passed (T21), `tests/test_database.py` 21 passed (T19), `tests/test_portfolio_calculator.py` 19 passed (T20). Commits: `a262879` (T21), `5beec9c` (T19), `d6febe1` (T20). Plan check commands were correct; no plan line changed except the ticks.

Test count before QA: 34 (21 original + 13 review-fix tests); QA added 42.

## 3. Acceptance criteria (76)
Legend: T = committed pytest, B = browser-equivalent step (Streamlit `AppTest` against the running app's code on the throwaway DB, plus the live server for port/health), C = shell command, `-` = not covered.

| AC | How verified | Result |
|---|---|---|
| 1.1 | T `test_stored_row_has_exactly_the_added_values` | pass |
| 1.2 | T `test_delete_transaction` | pass |
| 1.3 | B: BTC 0.01 on 2024-01-03, auto price, Binance reachable: page showed "Price on 2024-01-03: 42845.23", stored row price 42845.23 value 428.4523. Not cross-checked against an independent Binance quote | pass (partial) |
| 1.4 | - (USDT Amount path driven only for asset USDT, deposit 1000 stored as qty 1000 value 1000; ETH quantity 0.5 not driven) | not covered |
| 1.5 | B: ETH on a day with position 0, Position Percentage: "On 2024-01-03, ETH position is 0. Add a buy first." shown, row count unchanged. It is a `st.warning`, SPEC says "error" (SPEC drift, text matches). USDT warning variant not driven | pass (partial) |
| 1.6 | B: auto-price off reveals manual price input; Binance was reachable so the "Failed to get price" branch and the manual-price save were not driven. R-07 (two price checkboxes) open | not covered |
| 1.7 | B: click with quantity 0 -> "Specify quantity"; USDT Amount 0 -> "Specify USDT amount"; rows unchanged both times | pass |
| 1.8 | - | not covered |
| 2.1-2.5 | T `test_empty_portfolio`, `test_buy_sell_flow`, `test_buy_without_enough_usdt_does_not_go_negative`, `test_dynamic_assets`, `test_portfolio_at_date_ignores_future` | pass |
| 2.6 | B: ledger USDT 1000 + BTC 0.01 @ 42845.23: dashboard USDT 571.55, BTC 0.0100, BTC Value $777.77, Total $1,349.32 = 571.55 + 777.77. Price-fetch-failure branch not driven | pass (partial) |
| 2.7 | B: empty DB: main renders USDT 0.00, Total $0.00, 0 exceptions | pass |
| 3.1, 3.2, 3.3, 3.5 | - no committed test (plan T22). Review scratch probes passed (REVIEW.md) but are not in the repo | not covered |
| 3.4 | T `test_usdt_offered_on_fallback_path` asserts USDT only; BTC/ETH membership of the fallback list is not asserted. B: live asset list contained USDT first | partial |
| 4.1, 4.2, 4.4 | - no committed test (T22); review scratch probe passed | not covered |
| 4.3 | - | not covered |
| 5.1 | T `test_rates_upsert` | pass |
| 5.2 | B: Add Funding with 0 -> "Specify funding percentage", nothing stored | pass |
| 5.3 | - auto-populate not run (T24) | not covered |
| 5.4 | T `test_delete_funding_and_pool_rate_remove_only_that_row`; B: Delete on the Funding page emptied the table | pass |
| 6.1 | T `test_rates_upsert` | pass |
| 6.2 | B: Add Pool with 0 -> "Specify APY", nothing stored | pass |
| 6.3 | - | not covered |
| 6.4 | B: Pools page with one row loads, 0 exceptions; chart/table content not inspected | pass (partial) |
| 7.1 | T `test_no_transactions_returns_empty_frame_with_total_value_column` (empty, columns `date,total_value`) | pass |
| 7.2, 7.3 | T `test_total_value_conserved_on_buy_at_market`, `test_pool_income_added_after_month_end` | pass |
| 7.4 | T `test_funding_income_for_average_position` (1.0, USDT +1.0), plus time-weighted variant | pass |
| 7.5 | T `test_buy_draws_from_pool_first_and_leaves_usdt_untouched` (pool 500 -> 200, USDT 500 unchanged, total 1000) | pass |
| 7.6 | T `test_asset_without_price_is_excluded_from_total_characterizes_known_debt_D9` | pass (documents debt) |
| 7.7 | T `test_transaction_before_default_start_is_ignored_characterizes_known_debt_D2` | pass (documents debt) |
| 8.1-8.6 | T existing metrics tests (`test_total_return`, `test_returns_first_is_zero`, `test_max_drawdown*`, `test_volatility*`, `test_sharpe*`, `test_all_metrics_keys_and_values`) | pass |
| 8.7 | T `test_sortino_no_negative_returns_with_positive_mean_is_999` | pass |
| 8.8 | T `test_annual_return_of_doubling_over_about_one_year` (365 and 366 days, exact formula and abs 0.5 pp around 100) | pass |
| 8.9 | T `test_monthly_returns_empty_when_fewer_than_two_positive_months` | pass |
| 9.1 | - Analytics with an empty DB not driven | not covered |
| 9.2 | B: Analytics with 2 transactions: 8 metric tiles + 3 income tiles, 0 exceptions (Sharpe 1.77, Sortino 2.93, so the "N/A" branch not seen) | pass (partial) |
| 9.3 | - income block stayed at $0.00 ("No income data for selected period") because the only funding/pool rows were for the current month (D5: last-month income is not credited), so non-zero totals were not seen | not covered |
| 9.4 | - | not covered |
| 10.1-10.7 | - no committed test (T23). Review scratch probes passed; only the R-03/R-04 regression tests exist | not covered |
| 10.8 | B: Funding Arb tab, synthetic ticked, run: "Бэктест выполнен." + "SYNTHETIC / ASSUMED DATA — results are NOT a real backtest. Synthetic data requested by user." + disclaimer warning; 5 metrics (return -1.56 %) | pass |
| 10.9 | B: Alt MN tab, synthetic ticked, default symbols and default dates, run: success + same SYNTHETIC banner + disclaimer; metrics return -5.30 %, Sharpe -5.49. Not the exact 2024-01-01..2024-06-30 range of the AC | pass (partial) |
| 11.1 | B: guide page loads, 0 exceptions (network was available, offline not tested) | pass (partial) |
| 11.2 | C `grep -n "st.image\|perplexity" pages/guide.py` -> no output | pass |
| 12.1 | T `test_init_creates_four_tables_and_second_init_changes_nothing` | pass |
| 12.2, 12.3 | T `test_legacy_migration_keeps_rows_and_makes_backup`, `test_migration_failure_is_raised_and_old_table_kept` | pass |
| 12.4 | T `test_migration_that_would_lose_rows_raises_and_keeps_old_table` (+ NULL-apy variant) | pass |
| 12.5 | T `test_legacy_pool_rates_with_amount_are_migrated` | pass |
| 13.1 | T `test_streamlit_server_is_local_only`; C `grep address .streamlit/config.toml` -> `2:address = "127.0.0.1"` | pass |
| 13.2 | C `netstat -ano` while running: `127.0.0.1:28417 LISTENING`, no 0.0.0.0 entry | pass |
| 13.3 | C `git ls-files data` -> empty; `git check-ignore data/portfolio.db` -> `data/portfolio.db` | pass |
| 13.4 | C `grep -rnE "apiKey\|API_KEY\|getenv\|os.environ" --include=*.py .` (excl. .venv) -> no output | pass |
| 14.1, 14.2 | - (plan T24) | not covered |
| 15.1 | T `test_disclaimer.py` (3 tests); C `grep -il "not investment advice" README.md utils/disclaimer.py` lists both | pass |
| 15.2 | T + B: disclaimer text visible on Backtest at load and after both synthetic runs; also on main | pass |

Totals: 76 ACs. Pass (full) 43, pass-partial 8 (1.3, 1.5, 2.6, 3.4, 6.4, 9.2, 10.9, 11.1), not covered 25 (1.4, 1.6, 1.8, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 6.3, 9.1, 9.3, 9.4, 10.1-10.7, 14.1, 14.2). No AC failed. Every `[x]` AC in SPEC maps to a passing test.

## 4. Browser pass
The browser MCP / Playwright was not available to this agent run, so no real-browser pass at 375/768/1440, no screenshots in `docs/qa/` and no browser console capture. Substitute: the real server was started from the clean copy (port 28417, 127.0.0.1 only, health 200), and every page was executed through Streamlit `AppTest` against that copy's code with a fresh throwaway DB. This catches Python exceptions and wrong messages but not layout, JS console errors or failed requests.

Flows driven (live Binance was reachable, so prices were real):
1. Main (empty) -> Transactions: asset list offers USDT (R-05 fix confirmed online); USDT Amount deposit 1000 on 2024-01-02; BTC 0.01 buy on 2024-01-03 with auto price (42845.23); DB rows verified; zero-quantity and zero-amount errors; ETH Position Percentage on empty position.
2. Main with data: cards and Total Value reconcile (571.55 + 777.77 = 1349.32).
3. Funding: add with 0 (error), add 5 %, delete. Pools: add with 0 (error), add 6 %.
4. Analytics with data: 8 metric tiles + 3 income tiles render.
5. Backtest: Funding Arb and Alt MN with the synthetic checkbox: SYNTHETIC / ASSUMED DATA warning and disclaimer visible together with metrics.
6. Guide: renders.

Exceptions on any page: 0. Server log (`server.log`): only the startup lines, no errors. Console errors / failed browser requests: not observed because not measurable here. Streamlit prints the `use_container_width` deprecation notice (D13, plan T32) once per call in the AppTest stderr.
Cleanup: the Streamlit process (PID listening on 28417) was killed by PID; `netstat` afterwards shows only a TIME_WAIT entry, no listener. `git status` clean apart from the files listed below; the repo `data/` was not touched.

## 5. Non-functional basics
Accessibility (keyboard, focus, contrast, axe) and performance (load times, Backtest cold start >60 s noted in review R-19): not measured. Error/empty states verified: empty DB main page, empty funding/pool tables, zero-input errors. Data safety: all pytest DBs in `tmp_path`; the app run used `D:/Temp/claude/qa_run_crypto/data/portfolio.db`; the repo DB was never opened.

## 6. Bugs
No new product bug was found by QA. Open items observed or characterized by tests (all owned by others, no product code was changed):

| # | Severity | Repro | Status | Regression / characterization test |
|---|---|---|---|---|
| R-01 | P1 (tier A, owner decision) | values 1000, 1000, 2000 from a deposit -> total_return 100 | open | `test_external_deposit_counts_as_return_characterizes_open_finding_R01` |
| R-09 | P2 | yearly {0, inf, 25} -> average 0.0; Analytics "Average Annual" showed 0.00 % in the browser pass | open | `..._characterizes_open_finding_R09` |
| R-10 | P2 | one negative return -> Sortino 999 | open | `..._characterizes_open_finding_R10` |
| D1 / R-11 | P2 | same returns on daily or monthly rows give identical "annualized" vol and Sharpe (sqrt(252)) | open | `test_volatility_uses_sqrt_252_regardless_of_row_spacing_characterizes_known_debt_D1` |
| D2 | P3 | tx before 2022-01-01 dropped | open | `..._D2` |
| D4 | P3 | `get_current_portfolio` USDT 1000 vs `get_portfolio_at_date` USDT 5000 after a crypto buy | open | `..._D4` |
| D5 | P3 | last-month funding/pool income in columns, not in `total_value`; seen in browser pass (income $0.00 for current-month rows) | open | `..._D5` |
| D9 / R-17 | P2 | missing price excludes asset; price error drops the whole snapshot row | open | two `..._D9` tests |
| D11 | P2 | sell larger than holding gives negative quantity | open | `..._D11` |
| R-07 | P2 | two "auto price" checkboxes | open, no test | - |
| S-03 | P2 | `scripts/migrate_database.py` drops tables without backup | open, no test | - |
| NEW observation | P3 | `INSERT OR IGNORE` in migration also swallows NOT NULL violations; the row-count guard turns this into a loud `RuntimeError` (good behaviour, pinned) | informational | `test_legacy_pool_with_null_apy_is_caught_by_row_count_guard` |

Characterization tests pin CURRENT behaviour; when a debt item is fixed the matching test must be updated deliberately.

SPEC drift to report (SPEC not edited by QA): AC1.5 says "error", the UI uses a warning; SPEC header still says 21 tests (now 76); AC lists `[ ]` for AC1.1, 7.1, 7.4-7.7, 8.7-8.9, 12.1, 12.4, 12.5, 5.4 (db layer), which now have committed tests; AC15.2 visual step now done in AppTest.

## 7. Not tested / residual risk
Real browser rendering and console (375/768/1440), accessibility, performance; price fetcher, asset-cache and price-discovery logic; both backtest engines and loaders beyond the R-03/R-04 regressions (survivorship, look-ahead D10/R-13, costs); auto-populate buttons and scripts; delete confirmation (none exists, D11/design); offline behaviour of pages; live-network failure branches (Binance down) of Transactions; tier-A branch coverage percentage; Python 3.11 only (no other versions); Windows only.
