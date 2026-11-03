# Review - chore/audit - 4dd8172..7bf1a5f (+fix commits) - 2026-11-01

## Summary
| reviewer | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| reviewer (opus) | 0 | 6 | 14 | 6 |
| security-reviewer (opus) | 0 | 1 | 2 | 1 |

Skipped: design-reviewer (no designed UI in scope; Streamlit default widgets; browser pass belongs to QA). Conflicts between reviewers: none.

Fix loop round 1 (backend-dev/sonnet, commits above, 34 passed): all P1 fixed except R-01 (owner decision: change of return methodology). P1 open: R-01. Auditor on REVIEW not required by rules/audit.md.

## Findings
| id | sev | where | problem | status |
|---|---|---|---|---|
| R-01 | P1 | utils/metrics.py:18 | External cash flows are counted as performance | OWNER DECISION (time-weighted returns change metric semantics) |
| R-02 | P1 | utils/portfolio_calculator.py:164-167 | A USDT deposit made while the pool holds sale proceeds is partly erased: the code subtracts `min(value, pool)` from the pool AND adds the fu | fixed (b7af675) |
| R-03 | P1 | utils/backtest_alt_mn.py:128 | BTC hedge has the wrong sign: `beta_short` is already a sum of negative weights x beta, so the portfolio beta is `beta_long + beta_short`, b | fixed (6111817) |
| R-04 | P1 | utils/backtest_data.py:101 | Funding history is one request with `limit=1000` (about 333 days at 3 points/day) and no pagination; later days are filled by `ffill()` at l | fixed (0d6ed00) |
| R-05 | P1 | utils/assets.py:66-71 | When Binance is reachable the asset list is built from `*/USDT` market bases, which never contains `USDT` itself; it is then cached 24 h | fixed (71c65e6) |
| R-06 | P1 | main.py:1 | AC15.1/AC15.2 fail: `grep -ril "not investment advice" README.md main.py pages` prints nothing (confirms D3) | fixed (dc627dd) |
| S-01 | P1 | .streamlit/config.toml:1-3 | OWASP A01 Broken Access Control / CWE-350, CWE-1385 (DNS rebinding, missing Host validation on WebSocket) + STRIDE S, I, T / Source: any web | fixed (139c9ab) |
| R-07 | P2 | pages/transactions.py:303-305 | Two independent "Automatically fetch price" checkboxes: per-method (`auto_price*`, lines 179/209/232) and final (`auto_price_final`, line 26 | open (logged in plan) |
| R-08 | P2 | utils/metrics.py:203-204 | `calculate_max_drawdown` raises `ValueError: Encountered all NA values` when every value is 0 (running max 0 -> drawdown all NaN -> `idxmin` | fixed (fe477d3) |
| R-09 | P2 | utils/metrics.py:149 | "Average Annual" on Analytics (`pages/analytics.py:59`) is `avg_yearly_return`, whose first year is forced to 0 by `fillna(0)` (dilutes the  | open (logged in plan) |
| R-10 | P2 | utils/metrics.py:294-299 | With exactly one negative return, `downside_returns.std()` is NaN (ddof=1) and Sortino returns the 999.0 "no downside" sentinel although a l | open (logged in plan) |
| R-11 | P2 | utils/metrics.py:177 | D1 confirmed and quantified: on the sparse history (month-start rows) each return is a monthly return annualized as daily, so volatility and | open (logged in plan) |
| R-12 | P2 | utils/backtest_funding_arb.py:190-192 | Backtest annualization is mixed: return compounded with 365 calendar days, volatility with sqrt(252), Sharpe = CAGR / vol (same at `utils/ba | open (logged in plan) |
| R-13 | P2 | utils/backtest_funding_arb.py:166-178 | Same-bar entry plus funding: the position is opened at bar t close when `funding_8h[t]` > threshold and `apply_funding(funding_8h[t])` then  | open (logged in plan) |
| R-14 | P2 | utils/backtest_alt_mn.py:73 | BTC is part of the cross-sectional momentum universe (mean/std and buckets at line 113); if BTC lands in a bucket its weight is silently ove | open (logged in plan) |
| R-15 | P2 | utils/backtest_alt_mn.py:42-44 | With real data, symbols are outer-merged (`backtest_data.py:179`); one symbol with NaN momentum on a date (late listing, gap) drops `valid`  | open (logged in plan) |
| R-16 | P2 | main.py:44-49 | Dashboard Total Value (`get_current_portfolio`) never includes funding or pool income, while the history total (`portfolio_calculator.py:128 | open (logged in plan) |
| R-17 | P2 | utils/portfolio_calculator.py:219-220 | D9 confirmed: `except Exception: pass` drops a whole snapshot row on any error (no log), producing holes that the metrics read as flat perio | open (logged in plan) |
| R-18 | P2 | utils/price_fetcher.py:112-117 | D6 confirmed: when the exact day candle is absent (future date, listing gap, today before the candle opens) the last candle of another day i | open (logged in plan) |
| R-19 | P2 | utils/price_fetcher.py:83 | Every `get_price` call reloads and, on a miss, rewrites the whole JSON cache (`_save_cache` line 55); `get_price_range` calls it once per da | open (logged in plan) |
| R-20 | P2 | utils/portfolio_calculator.py:75-127 | The month-income block is duplicated almost verbatim at lines 223-288 (average positions, funding, pool income, history patch) | open (logged in plan) |
| S-02 | P2 | utils/database.py:35 + .gitignore:36-39 | OWASP A05 Security Misconfiguration / CWE-538 (sensitive file in an externally accessible location) + STRIDE I / The legacy-migration path w | fixed (1c8429f) |
| S-03 | P2 | scripts/migrate_database.py:41-49 (and 72-78) | CWE-669 / CWE-1284-class integrity defect (destructive migration without backup or row check) + STRIDE T / The standalone script copies rows | open (logged in plan) |
| R-21 | P3 | utils/metrics.py:55-57 | `calculate_annual_return` takes the initial value from the first non-zero row but the clock from the first row (2022-01-01 even if the first | open (logged in plan) |
| R-22 | P3 | pages/backtest.py:151-166 | If the real Alt MN load lacks BTC (BTC fetch fails but others succeed), `run_alt_mn_backtest` returns `{}` and line 166 raises `KeyError`, s | open (logged in plan) |
| R-23 | P3 | utils/backtest_funding_arb.py:195 | Backtest Max DD is negative (`drawdown.min()`), Analytics Max Drawdown is positive (`abs`, `metrics.py:210`) | open (logged in plan) |
| R-24 | P3 | utils/portfolio_calculator.py:303 | Dead exports: `get_transactions_with_prices` and `save_portfolio_snapshot` / `get_portfolio_snapshots` (`utils/database.py:238,252`) have no | open (logged in plan) |
| R-25 | P3 | utils/metrics.py:73 | AI-slop: bare `except:` at `metrics.py:73`, `price_fetcher.py:50`, `pages/analytics.py:49`; `print` debris for errors at `price_fetcher.py:1 | open (logged in plan) |
| R-26 | P3 | utils/backtest_data.py:132 | Synthetic generators call `np.random.seed(42/43)` on the global RNG (also line 190), which changes the random state of any later caller | open (logged in plan) |
| S-04 | P3 | pages/backtest.py:112, pages/backtest.py:188, pages/transactions.py:366 | CWE-209 (information exposure through error message) + STRIDE I / Full tracebacks (`st.code(traceback.format_exc())`, `st.exception(e)`) sho | open (logged in plan) |

## Correctness and quality

Reviewer: `reviewer` (opus), step `review`, adoption review of 4dd8172 (`start`)..7bf1a5f (HEAD, branch `chore/audit`), 2026-11-01. Read-only on product code. Scope: the 15 features of `docs/SPEC.md`, the finance backtest-integrity checklist on `pages/backtest.py` + `utils/backtest_*.py`, independent recomputation of key numbers, AI-slop grep. Known debt D1-D13 (`docs/ARCHITECTURE.md` 7.2) is confirmed/refined below, not repeated as new findings.

Evidence scripts (outside the repo, mocks only, no network, no `data/` access):
`D:/Temp/claude/E--Main-Dev-Python-Done-Crypto-portfolio/315988f3-d235-4ed3-b126-4e37f8c886f1/scratchpad/recompute.py`, `.../scratchpad/acs.py`, `.../scratchpad/fund.py` (run with the global Python 3.11.9; the scratchpad venv is broken: `numpy/version.py` missing, so numpy fails to import).

### Findings

R-01 | P1 | utils/metrics.py:18 | External cash flows are counted as performance. `calculate_returns` is a plain `pct_change` of `total_value`, and `total_value` jumps on every USDT deposit (USDT "buy", `utils/portfolio_calculator.py:163-167`) and on every crypto buy not covered by USDT (`portfolio_calculator.py:172`: if USDT < remaining, nothing is deducted, so value is created). Toy: values 1000 -> 1000 -> 2000 from a second deposit with zero market move gives total_return 100.0, and 50 USDT + buy 100 BTC gives total 50 -> 150 (+200 %). Every headline metric (total, monthly/yearly, volatility, Sharpe, Sortino, drawdown, cumulative chart) is therefore wrong for any owner who adds money after day one; not documented in SPEC/ARCHITECTURE. Fix: record flows per snapshot (deposit = USDT buy, uncovered part of a crypto buy) and compute time-weighted returns `r_t = (V_t - F_t) / V_{t-1} - 1`; total return from the chained TWR; test-first (tier A).
R-02 | P1 | utils/portfolio_calculator.py:164-167 | A USDT deposit made while the pool holds sale proceeds is partly erased: the code subtracts `min(value, pool)` from the pool AND adds the full quantity to USDT, so the net gain is `value - min(value, pool)`. Toy: 1000 USDT, buy+sell 1 BTC @100 (pool 100), then deposit 500 USDT: history total 1400, hand value 1500, and the dashboard (`get_current_portfolio`) says USDT 1500, so main page and Analytics disagree. Fix: decide the meaning of a USDT buy (deposit vs pool withdrawal); for a deposit, do not touch the pool; add a regression test with the toy above.
R-03 | P1 | utils/backtest_alt_mn.py:128 | BTC hedge has the wrong sign: `beta_short` is already a sum of negative weights x beta, so the portfolio beta is `beta_long + beta_short`, but the code hedges `beta_long - beta_short` (the gross beta). Toy: long A w=0.5 beta 1, short B w=-0.5 beta 1 (already neutral) -> code adds BTC -1.0 -> after normalization {A 0.25, B -0.25, BTC -0.5}, portfolio beta -0.5 instead of 0. The "market-neutral" backtest is a net BTC short. Fix: `net_beta = beta_long + beta_short`; golden test asserting post-hedge beta ~ 0.
R-04 | P1 | utils/backtest_data.py:101 | Funding history is one request with `limit=1000` (about 333 days at 3 points/day) and no pagination; later days are filled by `ffill()` at line 122 and the frame is returned with `synthetic=False` and no note (line 125), so the page shows "Data source: Binance (real historical data)". Mocked 2024-01-01..2024-12-31: 366 rows, `synthetic False`, `notes []`, funding constant from 2024-11-30 to 2024-12-31 (32 assumed days). Breaks the CLAUDE.md rule "backtests must flag synthetic data"; refines D8. Fix: paginate on `fundingTime`; after merge, count rows whose funding was filled and add a note + set the flag when > 0.
R-05 | P1 | utils/assets.py:66-71 | When Binance is reachable the asset list is built from `*/USDT` market bases, which never contains `USDT` itself; it is then cached 24 h. The Transactions page selector (`pages/transactions.py:44,50`) therefore cannot offer USDT online, so the first step of every ledger (deposit USDT, AC2.2 / F1 "or USDT itself") is only possible offline. Mocked markets {BTC/USDT, ETH/USDT, USDC/USDT} -> `['BTC','ETH','USDC']`, USDT absent. Fix: always prepend `"USDT"` in `get_available_assets` (cached and live paths); test with a mocked exchange.
R-06 | P1 | main.py:1 | AC15.1/AC15.2 fail: `grep -ril "not investment advice" README.md main.py pages` prints nothing (confirms D3). Fix: add the SPEC disclaimer line to README, main page footer and the Backtest results block.
R-07 | P2 | pages/transactions.py:303-305 | Two independent "Automatically fetch price" checkboxes: per-method (`auto_price*`, lines 179/209/232) and final (`auto_price_final`, line 263). If the owner unticks the first and types a manual price but leaves the second ticked (its default), the preview uses the manual price while the saved row uses the Binance close (and USDT-Amount quantity is recomputed from it at line 351). Stored price/quantity differ from what was shown; AC1.6 manual path depends on the wrong box. Fix: one price source per form (drop the final box or bind both to one key).
R-08 | P2 | utils/metrics.py:203-204 | `calculate_max_drawdown` raises `ValueError: Encountered all NA values` when every value is 0 (running max 0 -> drawdown all NaN -> `idxmin`). Analytics (`pages/analytics.py:40`) then crashes; reachable when history rows exist but total is 0 (for example offline, only crypto buys with no price and no USDT). Verified by toy. Fix: return `(0.0, "", "")` when `drawdown.dropna()` is empty; test.
R-09 | P2 | utils/metrics.py:149 | "Average Annual" on Analytics (`pages/analytics.py:59`) is `avg_yearly_return`, whose first year is forced to 0 by `fillna(0)` (dilutes the mean), and a year-end value of 0 gives `inf`, which turns the whole metric into 0.00 via line 133. Toy {2022: 0.0, 2023: inf, 2024: 25.0} -> displayed 0.0. Fix: drop the first (NaN) year and years with a non-positive base, as `calculate_monthly_returns` does.
R-10 | P2 | utils/metrics.py:294-299 | With exactly one negative return, `downside_returns.std()` is NaN (ddof=1) and Sortino returns the 999.0 "no downside" sentinel although a loss exists (toy [0, 0.05, -0.02, 0.03] -> 999.0); Analytics shows "999.00". Fix: use the standard downside deviation `sqrt(mean(min(r,0)^2))` over all periods; show "N/A" for the sentinel.
R-11 | P2 | utils/metrics.py:177 | D1 confirmed and quantified: on the sparse history (month-start rows) each return is a monthly return annualized as daily, so volatility and Sharpe (lines 254-255) are both inflated by about sqrt(252/12) = 4.6x for those stretches, and mixed with transaction-day gaps. Documented as accepted in SPEC section 9, so P2 not P1; owner decision. Fix: resample to a regular daily series (forward-fill value) and annualize with 365, or compute on monthly returns with sqrt(12).
R-12 | P2 | utils/backtest_funding_arb.py:190-192 | Backtest annualization is mixed: return compounded with 365 calendar days, volatility with sqrt(252), Sharpe = CAGR / vol (same at `utils/backtest_alt_mn.py:145-147`). For 365-day crypto bars the Sharpe is biased by sqrt(365/252) = 1.2x and is not the mean/std Sharpe of the metrics page. Fix: one convention (365, mean excess daily return x 365 / (std x sqrt(365))).
R-13 | P2 | utils/backtest_funding_arb.py:166-178 | Same-bar entry plus funding: the position is opened at bar t close when `funding_8h[t]` > threshold and `apply_funding(funding_8h[t])` then credits that day's full 3 funding payments on the same bar. Toy: capital 1000, notional 1000, funding 0.001 on day 1, zero thereafter -> equity 1003 although the position existed only after the day-1 close. Refines D10 (look-ahead row 1). Fix: apply funding before the entry decision (or use t+1 funding for a position opened at t).
R-14 | P2 | utils/backtest_alt_mn.py:73 | BTC is part of the cross-sectional momentum universe (mean/std and buckets at line 113); if BTC lands in a bucket its weight is silently overwritten by the hedge at line 129. Fix: exclude BTC from `mom_z` and the buckets.
R-15 | P2 | utils/backtest_alt_mn.py:42-44 | With real data, symbols are outer-merged (`backtest_data.py:179`); one symbol with NaN momentum on a date (late listing, gap) drops `valid` below 10 for the default 10-symbol list, so no positions are taken and the run reports a flat 0 % curve as a real result without a note. Fix: lower the minimum to `2 * k`, or note "no rebalance possible on N dates" in metrics.
R-16 | P2 | main.py:44-49 | Dashboard Total Value (`get_current_portfolio`) never includes funding or pool income, while the history total (`portfolio_calculator.py:128,131`) credits it every month, so the two headline values drift apart by the accrued income, on top of R-02. Not documented in F2. Fix: document on the page, or derive the dashboard total from the last history row.
R-17 | P2 | utils/portfolio_calculator.py:219-220 | D9 confirmed: `except Exception: pass` drops a whole snapshot row on any error (no log), producing holes that the metrics read as flat periods. Fix: catch only the price lookup, log the asset/date, keep the row with a `missing_prices` field.
R-18 | P2 | utils/price_fetcher.py:112-117 | D6 confirmed: when the exact day candle is absent (future date, listing gap, today before the candle opens) the last candle of another day is returned and cached forever under the requested date; today's in-progress close is also cached permanently. Fix: do not cache today; return None (not a neighbouring close) when the day is absent.
R-19 | P2 | utils/price_fetcher.py:83 | Every `get_price` call reloads and, on a miss, rewrites the whole JSON cache (`_save_cache` line 55); `get_price_range` calls it once per day, so a cold range is O(days x cache size) disk work (contributes to the >60 s Backtest cold start). The write is not atomic and `_load_cache` swallows a corrupt file (bare `except`, line 50) and returns {}, so one interrupted write wipes the whole cache on the next save. Fix: load once per range, write via temp file + `os.replace`.
R-20 | P2 | utils/portfolio_calculator.py:75-127 | The month-income block is duplicated almost verbatim at lines 223-288 (average positions, funding, pool income, history patch). Any fix to R-01/R-02/D5 must be made twice. Fix: extract `_month_income(month, ...)` used by both.
R-21 | P3 | utils/metrics.py:55-57 | `calculate_annual_return` takes the initial value from the first non-zero row but the clock from the first row (2022-01-01 even if the first deposit is later): toy 0 (2022) -> 100 (2023) -> 200 (2024) gives 41.5 % instead of 100 %. Not displayed by Analytics today (only `avg_yearly_return` is), so P3. Fix: use the date of the first non-zero value.
R-22 | P3 | pages/backtest.py:151-166 | If the real Alt MN load lacks BTC (BTC fetch fails but others succeed), `run_alt_mn_backtest` returns `{}` and line 166 raises `KeyError`, shown as a traceback. Fix: check for empty metrics and show the "Мало данных" error.
R-23 | P3 | utils/backtest_funding_arb.py:195 | Backtest Max DD is negative (`drawdown.min()`), Analytics Max Drawdown is positive (`abs`, `metrics.py:210`). Fix: one sign convention.
R-24 | P3 | utils/portfolio_calculator.py:303 | Dead exports: `get_transactions_with_prices` and `save_portfolio_snapshot` / `get_portfolio_snapshots` (`utils/database.py:238,252`) have no caller. Fix: remove or mark as unused API.
R-25 | P3 | utils/metrics.py:73 | AI-slop: bare `except:` at `metrics.py:73`, `price_fetcher.py:50`, `pages/analytics.py:49`; `print` debris for errors at `price_fetcher.py:122,177,298`; `except Exception: pass` at `assets.py:40-41,58-59,79-80`. Fix: `except (ValueError, OverflowError)` etc. and `logging`.
R-26 | P3 | utils/backtest_data.py:132 | Synthetic generators call `np.random.seed(42/43)` on the global RNG (also line 190), which changes the random state of any later caller. Fix: `rng = np.random.default_rng(42)`.

Pointers for other reviewers (not scored here): no confirmation on delete (D11, design); `st.code(traceback.format_exc())` on the Backtest page exposes paths (security, local-only so low); unpinned transitives, observed again (global env: `streamlit` import fails on `starlette.middleware.gzip.DEFAULT_EXCLUDED_CONTENT_TYPES`, D12, security/deps).

No text in the reviewed code tries to instruct a reviewer.

### Known debt D1-D13: confirmed / refined
| Debt | Verdict | Severity | Note |
|---|---|---|---|
| D1 | confirmed, quantified | P2 | R-11 (about 4.6x inflation of vol and Sharpe on month-start stretches) |
| D2 | confirmed (code line 18 default) | P3 | earlier transactions silently dropped; owner chose 2022 |
| D3 | confirmed | P1 | R-06 (AC15.1 fails) |
| D4 | confirmed, impact narrower than stated | P3 | Position Percentage refuses USDT (`pages/transactions.py:191,333`) and the crypto quantity is identical in both functions, so the USDT mismatch has no effect on the input; it only matters if a future caller reads USDT from `get_portfolio_at_date` |
| D5 | confirmed | P3 | current-month income shown in columns, not in `total_value` |
| D6 | confirmed | P2 | R-18 |
| D7 | confirmed, impact narrower | P3 | `get_price` (since = local midnight - 1 day, limit 2) and `find_dates_by_price` map days correctly for UTC+ offsets (owner's zone); off-by-one only for UTC- offsets |
| D8 | confirmed, root cause found | P1 | R-04 (no pagination -> unflagged ffill); hidden "No data for" notes remain P2 |
| D9 | confirmed | P2 | R-17 |
| D10 | confirmed, refined | P2 | R-13 (entry-bar funding), plus R-03 (hedge sign) is a separate P1 bug |
| D11 | confirmed | P2 | sells can go negative, no CHECK constraints (design pointer for delete confirm) |
| D12 | confirmed in global env | P2 | see pointer above |
| D13 | confirmed (`use_container_width` count = 24) | P3 | |

### Independent recomputation (toy cases, by hand vs code)
| Quantity | Toy | Hand | Code | Result |
|---|---|---|---|---|
| Total return | 100 -> 121 | 21.0 | 21.0 | match |
| Max drawdown | 100, 110, 99, 121 | (110-99)/110 = 10.0 %, peak 01-02, trough 01-03 | (10.0, 2024-01-02, 2024-01-03) | match |
| Volatility (ann.) | returns 0, 0.1, -0.1, 0.2222 | std(ddof=1) x sqrt(252) x 100 = 218.886 | 218.886 | match (formula as specified; R-11 for the convention) |
| Sharpe | same | mean x 252 / (std x sqrt(252)) = 6.3960 | 6.3960 | match |
| Portfolio value | 1000 USDT, buy 2 BTC @100, sell 1 @100 | 800 USDT + 100 pool + 100 BTC = 1000 | 1000 every row | match |
| Portfolio value | + deposit 500 USDT while pool 100 | 1500 | 1400 | MISMATCH -> R-02 |
| Portfolio value | 50 USDT, buy 100 BTC | 150 only if 100 is a deposit; return must be 0 | 150, return +200 % | -> R-01 |
| Funding income (AC7.4) | 1 BTC, price 100, 12 % annual | 1.0, USDT +1 on 02-01 | 1.0, USDT 1.0 | match |
| Alt MN hedge | long/short beta 1 each | post-hedge beta 0 | -0.5 | MISMATCH -> R-03 |
| Funding arb payout | notional 1000, rate 0.001 for one day | 0 (position opened after that day's funding) | 3.0 | -> R-13 |

### Backtest-integrity checklist (`_family.md`, 10 rows) on pages/backtest.py + utils/backtest_*.py
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | No look-ahead | FAIL | both engines decide and fill on bar t close (D10); funding arb also credits bar-t funding to a position opened at t close (R-13). OK parts: momentum uses `shift(lookback)`, rolling beta uses `iloc[i-window:i]` (excludes t), no `shift(-n)` |
| 2 | Label leakage / purging | n.a. | no ML, no labels, no train/test split |
| 3 | Costs and frictions | PARTIAL | FA: fees + slippage on both legs, 2x slippage on liquidation; MN: cost on gross weight (always 1.0) at every rebalance, no borrow/funding cost for shorts; no 0/1/2/3x cost sensitivity table |
| 4 | Multiple testing / DSR | FAIL (declared non-goal) | no trial count, no deflated Sharpe |
| 5 | Out-of-sample discipline | FAIL (declared non-goal) | single in-sample run, no hold-out, no walk-forward |
| 6 | Robustness | FAIL (declared non-goal) | no parameter plateau, regimes, permutation test |
| 7 | "Too good" sanity | PASS | synthetic defaults: FA -1.56 %, MN -5.01 % / Sharpe -3.18 / Max DD -6.48 %; nothing too good, no leak hunt needed |
| 8 | Data handling | PARTIAL | synthetic origin flagged on every whole-dataset fallback (AC10.1-10.3 pass); FAIL on partial funding fill (R-04); survivorship of the MN universe stated in ARCHITECTURE only, not in the UI; spot via `get_price_range` (local-day) vs perp/funding (UTC), equal for the owner's UTC+ zone |
| 9 | Implementation / golden values | FAIL | no committed backtest tests; toy recomputation found R-03 |
| 10 | Reporting | PARTIAL | net of costs, max DD, final equity, FA PnL split; no turnover, exposure, trade count, CI/bootstrap, trials; no disclaimer (R-06) |

Optimizer rows of the router (variance/CVaR recomputation, weight sanity, equal-weight baseline): n.a., the product has no optimizer, VaR/CVaR or weights (SPEC non-goals).

### ACs checked (76 total)
- Committed tests: 18 `[x]` + 3 `[~]` (AC1.1, AC7.1, AC12.1) pass, see pytest below.
- Verified now with mocked scratch probes (no committed test; behaviour matches SPEC): AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC4.1, AC4.2, AC4.4, AC7.4, AC8.7, AC8.8, AC8.9, AC10.1, AC10.2, AC10.3, AC10.4, AC10.5, AC10.6, AC10.7, AC10.9 engine path (182 rows, metrics render) = 20.
- Verified by command: AC11.2 (no output), AC13.1 (`address = "127.0.0.1"`), AC13.3 (`git ls-files data` empty, `git check-ignore` prints the path), AC13.4 (no output) = 4.
- Verified by code reading only: AC2.6 (`main.py:44-49`), AC7.5, AC7.6, AC7.7, AC12.4, AC12.5 = 6.
- Failing: AC15.1, AC15.2 (R-06); AC1.6 manual-price path conditional on the second checkbox (R-07).
- Not run (page steps for the running app; design-reviewer starts the app; the global env cannot import streamlit): AC1.3-AC1.5, AC1.7, AC1.8, AC2.7, AC4.3, AC5.2-AC5.4, AC6.2-AC6.4, AC9.1-AC9.4, AC10.8, AC11.1, AC13.2, AC14.1, AC14.2 (AC14.1 would need DB_PATH patched; skipped to stay off the real DB).
- Missing committed tests (SPEC already marks them `[ ]`): every AC in the two lists above, plus R-01..R-05 have no regression test. Tier-A areas F1/F2/F7 lack tests for R-01, R-02.

### Commands run (output tails)
```
$ python -m pytest -q -p no:cacheprovider
.....................                                                    [100%]
21 passed in 0.63s

$ python -c "import compileall,re; compileall.compile_dir('.', quiet=1, rx=re.compile(r'[\\/](data|\.git|venv|\.venv)[\\/]'))"
compileall ok

$ python scratchpad/recompute.py <repo>      (excerpt)
total_return hand 21.0 code 21.0
maxdd hand 10.0 code (10.0, '2024-01-02 00:00:00', '2024-01-03 00:00:00')
vol hand 218.88606879176 code 218.88606879176012
sharpe hand 6.396021490668313 code 6.396021490668317
annual return ... code 41.45493070645705           (R-21)
deposit-only total_return 100.0                    (R-01)
sortino with exactly one negative return 999.0     (R-10)
{2022: 0.0, 2023: inf, 2024: 25.0} avg 0.0         (R-09)
max drawdown on all-zero series RAISES ValueError Encountered all NA values  (R-08)
USDT deposit while pool > 0: 2024-01-04 total_value 1400.0, current_portfolio USDT 1500.0  (R-02)
buy larger than USDT: total 50.0 -> 150.0          (R-01)
funding income AC7.4: funding_income 1.0, USDT 1.0 on 2024-02-01
alt MN code weights {'A': 0.25, 'B': -0.25, 'BTC': -0.5} portfolio beta -0.5 (should be 0)  (R-03)
funding arb: {01-01: 1003.0, 01-02: 1003.0} pnl_funding 3.0  (R-13)

$ python scratchpad/acs.py <repo>            (excerpt)
AC3.1..AC3.5 PASS; online asset list: ['BTC', 'ETH', 'USDC'] USDT present: False  (R-05)
AC4.1/4.2 rows: [['2024-01-10', 'exact'], ['2024-01-20', 'high_low']]; AC4.4 PASS
AC8.7 PASS; AC8.8 PASS; AC8.9 PASS
AC10.1..AC10.7 PASS
AC10.9 rows 182 metrics {total_return_pct: -5.008, sharpe_ratio: -3.178, max_drawdown_pct: -6.484, ...}

$ python scratchpad/fund.py <repo>
rows 366 synthetic False notes []
distinct funding in last 40 days: 7 first ffilled date: 2024-11-29   (R-04: constant from 11-30)

$ grep (AC11.2, AC13.4, AC15.1) -> no output; AC13.1 -> 2:address = "127.0.0.1"; check-ignore -> data/portfolio.db
$ git status --short -> clean (no repo file changed by the review besides this file)
```

### Trap-worthy findings for known-traps.md
- 2026-11-01 | Data | Portfolio tracker metrics on a value series that includes deposits | symptom: total return / Sharpe jump on every deposit | cause: `pct_change` of account value without cash-flow adjustment | fix: time-weighted returns with recorded flows (R-01).
- 2026-11-01 | Data | Paged market-data endpoints called once with `limit` | symptom: last weeks of a long backtest use a forward-filled constant while flagged as real data | cause: Binance `fundingRate` limit 1000 (about 333 days), no pagination, then `ffill` | fix: paginate, count filled rows and flag them (R-04).
- 2026-11-01 | Process | Beta hedge with signed short weights | symptom: "market-neutral" book is net short the benchmark | cause: subtracting an already-negative short-leg beta | fix: portfolio beta = sum(w_i x beta_i); golden test that post-hedge beta = 0 (R-03).
- 2026-11-01 | Data | Exchange asset list built from `*/QUOTE` market bases | symptom: the quote currency itself (USDT) is missing from selectors when online | fix: always add the quote asset (R-05).

Summary: 0 P0, 6 P1 (R-01..R-06), 14 P2 (R-07..R-20), 6 P3 (R-21..R-26). Tests 21/21 pass, compileall ok.

## Security

Reviewer: `security-reviewer` (opus). Date: 2026-11-01. Read-only on product code.

### Scope
- Commit range `4dd8172..HEAD` (HEAD = `7bf1a5f`, branch `chore/audit`); 39 files, +3959/-330. Non-doc code in diff: `.streamlit/config.toml`, `.gitignore`, `requirements*.txt`, `main.py`, `pages/{analytics,backtest,funding,guide,transactions}.py`, `utils/{assets,backtest_alt_mn,backtest_data,backtest_funding_arb,database,metrics,portfolio_calculator}.py`, `tests/*`, `.claude/skills/*`.
- Whole tracked tree also checked for sinks (scripts/, populate_funding.py, pages/pools.py, utils/price_fetcher.py), since the app is small.
- Threat model (SPEC / ADR-004): local single-user Streamlit app, no auth by design, SQLite personal DB in `data/`, outbound only to Binance public endpoints. Assets worth protecting: confidentiality and integrity of the personal holdings DB. Main attacker: a web page opened in the owner's browser while the app runs (CSRF / DNS rebinding), and accidental disclosure via git.
- Streamlit facts were verified in the installed 1.66.1 source (scratchpad venv `site-packages/streamlit`), not from memory: the server is Starlette-only (`config.py:67-76`), WebSocket origin check in `web/server/starlette/starlette_websocket.py:107-189`, options `server.enableCORS` default True (`config.py:1078-1090`), `server.allowedHosts` default `[]` = any Host accepted (`config.py:1109-1127`), `server.enableXsrfProtection` default True and documented as not protecting the WebSocket (`config.py:1130-1140`), config lookup global -> `$CWD/.streamlit` -> script-dir `.streamlit` (`config.py:3050-3072`).

### Categories
| # | Category | Status | Evidence / reason |
|---|---|---|---|
| 1 | Access control | checked | No auth by design (ADR-004); the only access boundary is the network. Loopback bind is effective: `.streamlit/config.toml:2` `address = "127.0.0.1"`, and Streamlit also reads the script-level `.streamlit/config.toml` (`config.py:3063-3070`), so it applies even when launched from another cwd (a `--server.address` CLI flag would still override; user choice). Gap: Host header is not restricted -> DNS rebinding reaches the full read/write app (S-01). No admin paths, no jobs exposed. |
| 2 | Authentication / session | n.a. | No login, sessions, cookies or credentials by design (ADR-004). Streamlit's `_streamlit_xsrf` cookie only guards upload/HTTP endpoints, none used (no `file_uploader`). |
| 3 | Injection | checked | All runtime SQL with values is parameterized (`utils/database.py:155-158,175,184-187,204,213,222-225,243-247`). f-string SQL in `utils/database.py:31,45,47-50,53-54` uses only table/column names passed as literals from `init_database` (`database.py:81,107`); not attacker-controlled. `scripts/migrate_database.py` has only static SQL. No `LIKE`, no shell (`subprocess`/`os.system` absent), no `eval/exec/pickle/yaml.load`, no LLM. The one free-text input `pages/backtest.py:121` (symbols) flows into ccxt symbol strings and a `requests` query param (`utils/backtest_data.py:100-102`, URL-encoded by requests, fixed host) - no injection sink. |
| 4 | XSS / CSRF / open redirect / CORS | checked | No `unsafe_allow_html`, `st.html` or `components` anywhere (grep). DB/exchange-derived strings (asset tickers, dates) go to `st.info/success/metric/dataframe` f-strings; Streamlit markdown does not render raw HTML without `unsafe_allow_html`, and tickers come from selectboxes fed by Binance markets/fallback list (`utils/assets.py`). No redirects, no stored URLs. CORS: `enableCORS` left at default True, so cross-origin WebSocket from a foreign Origin is refused (`server_util.py:58-90`). CSRF via rebinding is not covered -> S-01. |
| 5 | SSRF / outbound | checked | No user-supplied URL is fetched. Hosts contacted: Binance via ccxt public spot/futures (`utils/price_fetcher.py:22-27`, `utils/backtest_data.py:25-28`, no API keys) and `https://fapi.binance.com/fapi/v1/fundingRate` (`utils/backtest_data.py:99-102`, `timeout=10`). Links in `pages/guide.py:409-410` are static markdown. Telemetry off (`config.toml:6`). |
| 6 | Uploads / deserialization / path traversal | checked | No uploads. File I/O only on constant paths under `data/cache/` (`utils/assets.py:17-18`, `utils/price_fetcher.py:40-41`) with `json.load` (safe parser); user input never forms a path (cache keys are JSON keys, `price_fetcher.py:62-64`). |
| 7 | Money and credits (tier A) | checked, traced fully | No order placement or account access anywhere: grep for `create_order|cancel_order|withdraw|fetch_balance|apiKey|secret` over all `*.py` = 0 hits; both ccxt clients are constructed without credentials. Backtests are simulations only. Integrity of recorded money data: S-03 (legacy script can lose rows), S-02 (backup leak). |
| 8 | Secrets and data exposure (tier A) | checked, traced fully | No secrets in tree or history (tool output below). Personal DB `data/portfolio.db` never committed (history path scan). Gap: automatic migration backups `data/portfolio.db.pre-migration-*.bak` are not gitignored (S-02). Error leakage: tracebacks shown in UI (S-04, P3, local only). |
| 9 | Abuse / DoS | checked | Single local user, no costly paid APIs; ccxt `enableRateLimit: True`. Symbols list at `pages/backtest.py:121-122` is unbounded (many Binance calls) but only self-inflicted by the owner; not recorded. |
| 10 | Dependencies and config | checked | All runtime deps pinned (`requirements.txt`); `pip-audit -r requirements.txt`: no known vulnerabilities (below). Config: loopback bind, `headless=false`, telemetry off, CORS/XSRF at secure defaults; `allowedHosts` unset (S-01). No debug flags. |

### Tool output
1. `pip-audit -r requirements.txt` (pip-audit 2.10.1, system Python 3.11; the scratchpad venv's pip_audit install is broken - its `__init__.py` files are missing - so the system install was used, no installs made):
```
WARNING:pip_audit._cache:Failed to write to cache directory, performance may be degraded: [WinError 17] ...
No known vulnerabilities found
exit=0
```
2. Framework secret scanner `node E:/Main/Dev/coding-brain/scripts/secrets-scan.mjs --project . --history`:
```
secrets-scan: 47 tracked files, 0 env values from 0 untracked env file(s) [] (+history), 0 hit(s)
exit=0
```
3. Pattern scan, tree (`git grep -i -E 'api[_-]?key|secret|passw(or)?d|token|private[_-]?key|BEGIN .*PRIVATE|AKIA...|sk-...|ghp_...|xox[bp]-|apiKey|Authorization:'`, excluding docs): only `.gitignore:61-62` (comment + `secrets.toml` ignore rule) and `AGENTS.md:10` (policy text). No values.
4. Pattern scan, history (`git log -p --all`, added lines, 18 commits): 16 hits, all prose in `docs/*.md`, `AGENTS.md`, `.gitignore` (commits `7bf1a5f`, `ca2c077`, `aa0da1c`). No key material.
5. History path scan (`git log --all --name-only`, grep `data/|\.db|\.env|secret|\.sqlite|\.bak`): 0 hits - DB and env files were never committed.
6. AC13.4 grep `grep -rnE "apiKey|API_KEY|getenv|os.environ" --include=*.py .`: no output.
7. Ignore check `git check-ignore -v data/portfolio.db.pre-migration-20261101000000.bak`: not ignored (exit 1). Also not ignored: `data/portfolio.db.bak`, `data/backup.sqlite`, `data/x.csv`. Ignored: `data/*.db`, `data/cache/`, `*.json`.
8. Reviewer-steering text scan (`ignore previous|already reviewed|false positive|automated review|do not report|security review`) over tracked non-doc files incl. `.claude/skills/*`: 0 hits.
9. Built-in `security-review` skill: failed to start (`git diff --name-only origin/HEAD...` - repo has no `origin` remote). Replaced by the manual sink-by-sink pass above; no candidates from it.
10. App not started (design-reviewer owns the port); bind check is static. `netstat` evidence belongs to QA (plan T27).

### Findings
- S-01 | P1 | .streamlit/config.toml:1-3 | OWASP A01 Broken Access Control / CWE-350, CWE-1385 (DNS rebinding, missing Host validation on WebSocket) + STRIDE S, I, T | Source: any web page the owner opens while the app runs. Path: attacker page at `http://rb.attacker.tld:8501` rebinds its DNS to `127.0.0.1`, then opens `ws://rb.attacker.tld:8501/_stcore/stream`; Host = Origin host, so `starlette_websocket.py:184-185` treats it as same-origin, and `_is_host_allowed` returns True because `server.allowedHosts` is empty (`starlette_websocket.py:109-111`, default `config.py:1125`). The loopback bind does not help, because the browser itself connects to 127.0.0.1, and XSRF protection explicitly does not cover the WebSocket (`config.py:1135-1137`). Exploit: the page drives the Streamlit protocol and reads the full holdings/transaction history (rendered tables, metrics) and clicks the Delete buttons (`pages/funding.py:127-130`, same for transactions and pools), silently wiping or altering the personal DB. Newer Chrome may show a Local Network Access prompt; Firefox/Safari do not. Fix: add `allowedHosts = ["localhost", "127.0.0.1"]` under `[server]` in `.streamlit/config.toml`, and extend the T27 config test to assert it.
- S-02 | P2 | utils/database.py:35 + .gitignore:36-39 | OWASP A05 Security Misconfiguration / CWE-538 (sensitive file in an externally accessible location) + STRIDE I | The legacy-migration path writes a full copy of the personal DB to `data/portfolio.db.pre-migration-<ts>.bak`, but `.gitignore` covers only `data/*.db*`-style names (`*.db`, `-journal`, `-shm`, `-wal`); `git check-ignore` confirms the `.bak` is not ignored. Exploit: after a migration, a routine `git add -A && git commit` (by the owner or an agent) commits the full financial history, which then leaks on the first push and stays in history. Same risk for manual copy-backups the project rules ask for (`*.bak`, `*.sqlite`, CSV exports). Fix: ignore the whole directory (`data/` with `!data/.gitkeep` if needed) instead of per-extension patterns; add a test that `git check-ignore` matches `data/portfolio.db.pre-migration-x.bak`.
- S-03 | P2 | scripts/migrate_database.py:41-49 (and 72-78) | CWE-669 / CWE-1284-class integrity defect (destructive migration without backup or row check) + STRIDE T | The standalone script copies rows with `INSERT OR IGNORE` into a table with `UNIQUE(year, month, asset)` and then `DROP TABLE funding_rates` unconditionally, with no backup and with errors only printed (`:88-90`). Duplicate legacy rows are silently discarded and the original table is gone. It duplicates the already-safe in-app path (`utils/database.py:21-58`: backup, row count check, raise). Exploit scenario is accidental, not adversarial: owner runs the old script on a legacy DB and loses funding records without noticing. Fix: delete the script (in-app `init_database` already migrates) or make it call `utils.database._drop_legacy_amount_column`. Owner: reviewer/backend may take it as a correctness item; kept here because it is a data-integrity path.
- S-04 | P3 | pages/backtest.py:112, pages/backtest.py:188, pages/transactions.py:366 | CWE-209 (information exposure through error message) + STRIDE I | Full tracebacks (`st.code(traceback.format_exc())`, `st.exception(e)`) show absolute file paths and library internals in the UI. Only the local owner sees them (or a rebinding attacker who already has full access via S-01), so impact is minimal. Fix (optional): show `type(e).__name__` + message and log the traceback to the console; or leave as an intentional debug aid for a local tool.

Counts: P0 0, P1 1, P2 2, P3 1.

### Dropped candidates
- f-string SQL in `utils/database.py:31-54`: table/column names are code literals (`database.py:81,107`), never user input.
- XSS through asset names in `st.info(f"...{asset}")`: no `unsafe_allow_html`; values come from selectboxes over Binance tickers/fallback list; Streamlit markdown escapes raw HTML.
- SSRF via backtest symbols (`pages/backtest.py:121`): fixed hosts; symbol only becomes a ccxt market id / URL-encoded query param.
- Cross-origin WebSocket CSRF from a foreign Origin: blocked by default `enableCORS=True` (`server_util.py:58-90`); only the rebinding variant (S-01) works.
- Loopback bind ineffective when started from another cwd: disproved, script-level config is read (`config.py:3063-3070`).
- Real order placement / exchange keys: none in code (tier-A grep, 0 hits).
- Unbounded symbols list as DoS: self-inflicted only, single local user.
- Cache JSON tampering (`data/cache/*.json`): only writable by the local user, parsed with `json.load`; worst case wrong cached prices, no code execution.

### Tier-A paths traced
- Network entry: `.streamlit/config.toml` -> Streamlit Starlette WebSocket handler (origin + host checks read in source) -> every page's write actions (add/delete in `pages/transactions.py`, `pages/funding.py`, `pages/pools.py` -> `utils/database.py` parameterized calls).
- Outbound: every `ccxt.binance(...)` and `requests.get` call (3 sites), no credentials, fixed hosts.
- Secrets: tree, full history (18 commits), env-file scan, ignore rules for `data/`.
- Money: no trading/order/withdraw code; DB migration paths (in-app safe, script unsafe -> S-03).

### Trap-worthy (for known-traps.md)
- 2026-11-01 Streamlit (1.66) on 127.0.0.1 is still reachable by DNS rebinding: `server.allowedHosts` defaults to `[]` (any Host), a rebinding page is "same-origin" for the WebSocket, and XSRF does not cover the WebSocket. Fix: `allowedHosts = ["localhost", "127.0.0.1"]` in `.streamlit/config.toml`.
- 2026-11-01 Per-extension ignores for a personal-data dir (`data/*.db`) miss automatic backups (`*.bak`) written by migration code; ignore the directory, not extensions.
- 2026-11-01 Built-in `security-review` skill needs an `origin` remote (`git diff origin/HEAD...`); in local-only repos it fails to start - do the manual pass.

Read: E:/Main/Dev/coding-brain/agents/security-reviewer.md, E:/Main/Dev/coding-brain/process/review.md, E:/Main/Dev/coding-brain/routers/projects/finance/_family.md, E:/Main/Dev/coding-brain/routers/projects/finance/portfolio-risk.md, E:/Main/Dev/coding-brain/known-traps.md, E:/Main/Dev/coding-brain/knowledge/guides/engineering/19-security.md (headings), project: .streamlit/config.toml, .gitignore, requirements.txt, utils/database.py, scripts/migrate_database.py, utils/assets.py, utils/price_fetcher.py, utils/backtest_data.py, pages/backtest.py, pages/funding.py, main.py (parts), Streamlit 1.66.1 source (config.py, web/server/server_util.py, web/server/starlette/starlette_websocket.py)

## Final verification
See docs/QA.md (full suite and compileall pasted after the fix loop; 34 passed).
