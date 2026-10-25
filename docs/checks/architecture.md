# Audit: architecture (docs/ARCHITECTURE.md + docs/adr/)
mode: shadow
author-model: opus · auditor-model: sonnet (fallback; fable out of credits, so this OK carries less weight and the user's gate matters more)

## Verdict
OK
No P0/P1 findings and no checklist FAIL; concrete claims (tables, constraints, D1/D2/D4/D9/D13, trace, test run) match the code; the 3 open ADR owner gates are expected.

## Checklist
| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Every SPEC feature (F-id) appears in a component/table/route (trace) | PASS | docs/ARCHITECTURE.md:137 "F1 Transaction ledger" ... :151 "F15 Disclaimer" (15 of 15) [script] |
| 2 | Versions recorded with verification date | PASS | docs/ARCHITECTURE.md:6 "release existence and `requires_python` were checked on PyPI on 2026-10-25" [script] |
| 3 | requires/conflicts of modules checked (ok) | PASS | docs/ARCHITECTURE.md:93 "SPEC section 6 selects no module, so there is no `requires` chain and no `conflicts` pair: ok." [script] |
| 4 | Each applicable known-trap has a recorded decision | PASS | docs/ARCHITECTURE.md:183 "loopback bind (ADR-004); Streamlit XSRF/CORS defaults kept" (18 rows; judged: Environment, Data, Security, Process, Windows all covered) |
| 5 | Stack deviations have ADR and user answer | PASS | docs/ARCHITECTURE.md:199 "awaiting owner ok" (expected owner gate, doc-check items 13-15, not a defect) |
| 6 | Test DB/ports/secrets names defined | PASS | docs/ARCHITECTURE.md:157 "monkeypatches `utils.database.DB_PATH` to `tmp_path/test.db`" [script] |
| 7 | Audit done per rules/audit.md | PASS | this file exists; Disposition/STATE line are the orchestrator's step |
| 8 | (JUDGE) design covers SPEC without over-design; trace plausible | PASS | docs/ARCHITECTURE.md:38 "End-to-end trace (main user action: add a buy and see it valued)"; steps match utils/database.py get_current_portfolio and portfolio_calculator.py |
| 9 | (JUDGE) security surface addressed | PASS | docs/ARCHITECTURE.md:99 "no uploads; no URL fetch from user input"; requests timeout=10 confirmed in backtest_data.py:102; no unsafe_allow_html in main.py/pages |

## Findings
none

## Notes (non-blocking)
- N-01 | opinion | at: docs/ARCHITECTURE.md:6 | Riskiest assumption: library versions and APIs were not verified via context7 (only PyPI existence); pins are trusted because the audit ran a clean venv on 2026-10-24. The 21 tests pass here (checked), which supports it.
- N-02 | opinion | at: docs/ARCHITECTURE.md:168 | Test counts: the doc says 10 tests in test_metrics.py, the file has 9 test functions (9+9+3 = 21 total matches). Cosmetic.
- N-03 | opinion | at: docs/ARCHITECTURE.md:3 | Header names ADR-001..003 as deviations while section 1 cites ADR-004 (accepted) for Streamlit; consistent, just easy to misread.

## Disposition
| id | verdict | by | note |
|---|---|---|---|
| (none) | n/a | lead 2026-10-25 | 0 findings, 3 notes; note on 10 vs 9 tests verified and ARCHITECTURE.md:168 fixed; others accepted as is |

Read: E:/Main/Dev/coding-brain/agents/auditor.md, E:/Main/Dev/coding-brain/rules/audit.md, E:/Main/Dev/coding-brain/process/architecture.md, docs/ARCHITECTURE.md, .streamlit/config.toml, utils/database.py, utils/portfolio_calculator.py, utils/metrics.py, utils/price_fetcher.py, utils/backtest_data.py, tests/*.py (grep), pages/backtest.py (grep), docs/SPEC.md (grep)
