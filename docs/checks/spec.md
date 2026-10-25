# Audit: spec (docs/SPEC.md)
mode: shadow
author-model: sonnet · auditor-model: opus

## Verdict
OK
No P0/P1 finding and no checklist FAIL; three P2 findings where the SPEC's claims disagree with the code and tests (test-coverage marks and one AC wording).

## Checklist
| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Every template heading present; no `[NEEDS CLARIFICATION]` left; open questions empty | PASS | spec.1 "11 headings found", spec.2 "0 markers", spec.3 docs/SPEC.md:247 "None." [script] |
| 2 | Every P1 feature has >=2 acceptance criteria, each testable by a stated command/step | PASS | spec.4 "15 features, 76 ACs", spec.5 "76 ACs have Given + Then" [script]; spec.6 (judged): every AC names a test, a pytest to write, a command or a page step, e.g. docs/SPEC.md:158 "When `grep -n "address" .streamlit/config.toml` is run" |
| 3 | Non-goals and "modules: no" lists exist | PASS | spec.7 docs/SPEC.md:26 "Non-goals (will not do):", spec.8 docs/SPEC.md:192 [script] |
| 4 | `grep -c "NEEDS CLARIFICATION" docs/SPEC.md` prints 0 | PASS | spec.2 "0 markers" [script] |
| 5 | Status line says approved by user | PASS | spec.9 "not required without --require-approved (not approved docs/SPEC.md:3)" [script]; docs/SPEC.md:3 "pending owner approval" (expected for this run; architecture must not start until approved) |
| 6 | Audit done per rules/audit.md | n/a (this run) | this file is the audit; Disposition and the STATE line `audit/spec` are orchestrator steps after this run |
| 6a | spec.10 no invented requirements; gaps are questions or marked assumptions | PASS | behaviour sections match the code read (database.py, portfolio_calculator.py, metrics.py, transactions.py, funding.py, pools.py, main.py, backtest_data.py); the only non-code requirement, the disclaimer, comes from the finance family rule and is marked as a gap: docs/SPEC.md:169 "### F15 Disclaimer (P2, gap: not implemented today)" |
| 6b | spec.11 Definition of done is measurable | PASS | docs/SPEC.md:251 "passes with at least 21 passed, 0 failed, 0 skipped (current baseline)"; pytest run today: 21 passed |

## Findings
- A-01 | P2 | source: AC1.1 | at: docs/SPEC.md:42 | quote: "returns that row with the same values (`test_database.py::test_buy_sell_flow`)" | scenario: tests/test_database.py::test_buy_sell_flow never calls get_transactions() and asserts only get_current_portfolio() quantities, so AC1.1 is marked [x] without a test; the DoD rule 'every [x] AC maps to a passing test' (line 251) would pass while a regression in stored row values goes unnoticed | fix: mark AC1.1 [~] (state what is asserted) or name a test that checks the get_transactions() row
- A-02 | P2 | source: AC12.1 | at: docs/SPEC.md:149 | quote: "Then the four tables exist and all CRUD tests pass on them; running it twice changes nothing" | scenario: no committed test checks that the four tables exist (portfolio_snapshots is never touched by any test) or that a second init_database() run changes nothing; QA would treat idempotence as covered while it is not | fix: mark AC12.1 [~] with what is asserted, or add the table-list and double-run check to the to-write list
- A-03 | P2 | source: AC1.3 | at: docs/SPEC.md:44 | quote: "value = 0.1 x price, and a green" | scenario: pages/transactions.py:361-362 calls st.success and then st.rerun() immediately, so the success message is cleared by the rerun; a page step or AppTest written from AC1.3 waits for a message that does not stay on screen and fails against correct current behaviour | fix: replace the message clause with 'the new row appears in Transaction History' or state that the message is not persisted

## Notes (non-blocking)
- N-01 | opinion | at: docs/SPEC.md:232 | Riskiest assumption: metrics annualize with 252 periods on a sparse series (rows only on transaction days, month starts, last day), so volatility/Sharpe/Sortino shown on the Analytics page are not standard figures. The SPEC documents this rather than correcting it; the architecture step should decide whether it stays.
- N-02 | opinion | at: docs/SPEC.md:96 | F7 describes buys consuming the pool first; the code also reduces the pool on a USDT buy (portfolio_calculator.py:163-167) while adding the quantity to USDT. The SPEC does not mention this USDT-buy case; worth one sentence if F7 math is ever changed (tier A).
- N-03 | opinion | at: docs/SPEC.md:116 | AC8.8 'doubling over exactly 365.25 days' cannot be built on a daily index (days_diff is an integer in metrics.py); the 'about 100.0' tolerance makes it workable, a 365- or 366-day series with a stated tolerance would be cleaner.

## Disposition
| id | verdict | by | note |
|---|---|---|---|
| A-01 | valid | lead 2026-10-25 | verified test_buy_sell_flow never calls get_transactions; AC1.1 marked [~] |
| A-02 | valid | lead | no test lists tables or double-runs init; AC12.1 marked [~] |
| A-03 | valid | lead | transactions.py:361-362 st.success then st.rerun; AC1.3 reworded |

Read: E:/Main/Dev/coding-brain/agents/auditor.md, E:/Main/Dev/coding-brain/rules/audit.md, E:/Main/Dev/coding-brain/process/spec.md, E:/Main/Dev/coding-brain/routers/projects/finance/ (grep disclaimer), docs/SPEC.md, README.md, tests/conftest.py, tests/test_database.py, tests/test_metrics.py, tests/test_portfolio_calculator.py, utils/database.py, utils/portfolio_calculator.py, utils/metrics.py, utils/backtest_data.py (grep), main.py, pages/transactions.py, pages/funding.py, pages/pools.py (grep), pages/backtest.py (grep), pages/guide.py (grep), .streamlit/config.toml (grep)
