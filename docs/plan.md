# Plan — Crypto Portfolio Tracker

Source: `docs/ARCHITECTURE.md` (reverse-engineered 2026-10-25) and `docs/SPEC.md`. Written by `architect` in ADOPTION mode: Phases 0-2 are work already delivered (ticked with commit evidence from `git log --oneline` on `chore/audit`; that work was done directly by the lead in the audit finish-pass, fields recorded afterwards); Phases 3-5 are the real backlog. No rewrite and no new feature is planned. Ticked by whoever finishes a task: checkbox here + one line in `docs/STATE.md` + local commit (never push).

Legend: `[ ]` open · `[x]` done (evidence in STATE / commit) · `[!]` blocked (reason on the line).
Fields: `layer` data|backend|frontend|ai|infra|qa|docs · `tier` A|B|C (test risk) · `owner` agent id · `model` haiku|sonnet|opus · `owns` files/globs this task may edit · `depends` task ids · `uses` ids to read for this task · `check` ONE runnable command, exit 0 = done · `done` human acceptance (cites SPEC `AC` ids).
Parallel rule: tasks run in parallel only if their `owns` are disjoint and all `depends` are done; marked `[P gN]`. Shared files: `tests/conftest.py` belongs to T18 only; `utils/database.py` to T05/T06 (sequential).
Environment: all `check` commands run from the project root inside the project venv created by T18 (`.venv`, from `requirements-dev.txt`). The global interpreter is not a valid environment (ADR-002: it has streamlit 1.57 with a broken starlette). Router stack items `stack:duckdb`, `stack:skfolio`, `stack:pydantic` are out of scope per ADR-001/ADR-003 and appear in no task until the owner answers those ADRs.

## Phase 0 — Foundation (delivered)
- [x] T01 Existing app runs + early real build
  layer: infra · tier: C · owner: devops · model: sonnet
  owns: main.py, pages/**, utils/**, .gitignore
  depends: -
  uses: blueprint:finance-research, stack:python, stack:pandas
  check: `python -m compileall -q main.py pages utils scripts populate_funding.py`
  done: app imported as is (4dd8172 start), README synced (67762bd), `.venv/` ignored (de35545); audit 2026-10-24 ran `streamlit run main.py` with HTTP 200 and `/_stcore/health` 200 in a clean venv. Blueprint not applied (ADR-001, ADR-002).
- [x] T02 Pin dependencies + dev requirements
  layer: infra · tier: B · owner: devops · model: haiku
  owns: requirements.txt, requirements-dev.txt
  depends: T01
  uses: stack:python, rule:python
  check: `python -c "import pathlib,sys;ls=[l for l in pathlib.Path('requirements.txt').read_text().splitlines() if l.strip() and not l.startswith('#')];sys.exit(0 if ls and all('==' in l for l in ls) else 1)"`
  done: 8 top-level `==` pins + pytest 9.1.1 (c3ccdb3); README says Python 3.11+ (d7a17f9). Transitive pins open: ADR-002.
- [x] T03 Bind Streamlit to loopback
  layer: infra · tier: A · owner: devops · model: sonnet
  owns: .streamlit/config.toml
  depends: T01
  uses: rule:folders
  check: `python -c "import tomllib;c=tomllib.load(open('.streamlit/config.toml','rb'));assert c['server']['address']=='127.0.0.1'"`
  done: AC13.1; tracked config with `address = "127.0.0.1"`, `gatherUsageStats = false` (aa0da1c); netstat showed `127.0.0.1:PORT LISTENING` in the audit.
- [x] T04 Phase 0 build gate
  layer: infra · tier: C · owner: devops · model: haiku
  owns: -
  depends: T02, T03
  uses: stack:pytest
  check: `python -m compileall -q main.py pages utils scripts && python -m pytest -q`
  done: compile OK and 21 passed on 2026-10-25.

## Phase 1 — MVP slice: ledger, holdings, history, metrics, pages (delivered)
- [x] T05 SQLite schema, CRUD and holdings replay
  layer: data · tier: A · owner: backend-dev · model: sonnet
  owns: utils/database.py
  depends: T04
  uses: stack:pandas, rule:tests
  check: `python -m pytest -q tests/test_database.py`
  done: four tables (ARCHITECTURE section 4); AC1.2, AC2.1, AC2.2, AC2.3, AC2.4, AC2.5, AC5.1, AC6.1 pass; AC1.1 and AC12.1 partial (T19). Commits 4dd8172, f406b52 (dynamic assets).
- [x] T06 Safe legacy migration (backup, one transaction, row-count check)
  layer: data · tier: A · owner: backend-dev · model: opus
  owns: utils/database.py
  depends: T05
  uses: rule:tests, skill:test-driven-development
  check: `python -m pytest -q tests/test_database.py -k migration`
  done: AC12.2, AC12.3 (ead29a9); `.pre-migration-*.bak` written first; errors raised, never swallowed.
- [x] T07 Market-data access and asset list (Binance public via ccxt, file cache)
  layer: backend · tier: B · owner: backend-dev · model: sonnet
  owns: utils/price_fetcher.py, utils/assets.py
  depends: T04
  uses: mcp:context7, stack:pandas
  check: `python -c "import utils.price_fetcher, utils.assets"`
  done: F3, F4 behaviour as in SPEC (4dd8172, f406b52); no committed test yet (T22).
- [x] T08 Portfolio value history engine (pool and income logic)
  layer: backend · tier: A · owner: quant-research · model: opus
  owns: utils/portfolio_calculator.py
  depends: T05, T07
  uses: stack:pandas, stack:numpy, rule:tests
  check: `python -m pytest -q tests/test_portfolio_calculator.py`
  done: AC7.2, AC7.3 pass; AC7.1 partial (T20); known debt D2, D5, D9 recorded, not fixed (4dd8172, f406b52).
- [x] T09 Performance metrics + pandas 3 resample fix
  layer: backend · tier: B · owner: quant-research · model: sonnet
  owns: utils/metrics.py
  depends: T04
  uses: stack:pandas, stack:numpy
  check: `python -m pytest -q tests/test_metrics.py`
  done: AC8.1, AC8.2, AC8.3, AC8.4, AC8.5, AC8.6 pass; `ME`/`YE` fix (92da55e); annualization debt D1 recorded.
- [x] T10 Pages: dashboard, transactions, funding, pools, analytics
  layer: frontend · tier: C · owner: frontend-dev · model: sonnet
  owns: main.py, pages/transactions.py, pages/funding.py, pages/pools.py, pages/analytics.py
  depends: T05, T07, T08, T09
  uses: skill:data-visualization
  check: `python -m compileall -q main.py pages`
  done: F1, F2, F4, F5, F6, F9 pages (4dd8172, f406b52); audit AppTest of all 7 pages: 0 exceptions (not committed; T25, T26).
- [x] T11 Unit tests: database, metrics, portfolio calculator
  layer: qa · tier: A · owner: qa-tester · model: sonnet
  owns: tests/**
  depends: T05, T08, T09
  uses: skill:test-driven-development, stack:pytest, rule:tests
  check: `python -m pytest -q`
  done: 21 tests, tmp DB fixture, mocked prices, `data/portfolio.db` never touched (e9e7dd3).
- [x] T12 Phase 1 build gate
  layer: infra · tier: C · owner: devops · model: haiku
  owns: -
  depends: T06, T10, T11
  uses: stack:pytest
  check: `python -m compileall -q main.py pages utils scripts && python -m pytest -q`
  done: 21 passed on 2026-10-25.

## Phase 2 — Next slice: backtests and guide (delivered, P2)
- [x] T13 Backtest loaders, funding-arb and alt market-neutral engines, Backtest page
  layer: backend · tier: B · owner: quant-research · model: sonnet
  owns: utils/backtest_data.py, utils/backtest_funding_arb.py, utils/backtest_alt_mn.py, pages/backtest.py
  depends: T07
  uses: stack:pandas, stack:numpy, skill:data-visualization
  check: `python -m compileall -q utils/backtest_data.py utils/backtest_funding_arb.py utils/backtest_alt_mn.py pages/backtest.py`
  done: F10 exploratory engines (f406b52); validation limits D10 recorded.
- [x] T14 Flag synthetic/assumed backtest data explicitly
  layer: backend · tier: B · owner: quant-research · model: sonnet
  owns: utils/backtest_data.py, pages/backtest.py
  depends: T13
  uses: rule:tests
  check: `python -c "from utils.backtest_data import load_funding_arb_data as f;d=f('BTC','2024-01-01','2024-02-01',True);assert d.attrs['synthetic'] is True and d.attrs['notes']"`
  done: `attrs['synthetic']`/`attrs['notes']`, warning banner (b245d7a); audit finding 4 closed; residual D8.
- [x] T15 Clean the guide page (chat leftovers, external logo)
  layer: frontend · tier: C · owner: frontend-dev · model: haiku
  owns: pages/guide.py
  depends: T13
  uses: none
  check: `python -c "import pathlib,sys;t=pathlib.Path('pages/guide.py').read_text(encoding='utf-8');sys.exit(1 if ('st.image' in t or 'perplexity' in t) else 0)"`
  done: AC11.2 (31b0030).
- [x] T16 Remove unused imports (ruff F401)
  layer: infra · tier: C · owner: devops · model: haiku
  owns: main.py, pages/**, utils/**, scripts/**
  depends: T14, T15
  uses: rule:python
  check: `python -m ruff check --select F401 .`
  done: 0 F401 (cc48d85).
- [x] T17 Phase 2 build gate
  layer: infra · tier: C · owner: devops · model: haiku
  owns: -
  depends: T16
  uses: stack:pytest
  check: `python -m compileall -q main.py pages utils scripts && python -m pytest -q`
  done: 21 passed on 2026-10-25.

## Phase 3 — Test backlog for SPEC `[ ]` / `[~]` ACs (open; tests only, no behaviour change)
Characterization rule: where the SPEC documents a known defect (D1, D4, D5, D9), the test pins the CURRENT behaviour and names the debt id; changing the behaviour is an owner decision (new task, tier A, test-first).
- [ ] T18 Project venv from the pins + shared test fixtures
  layer: infra · tier: B · owner: devops · model: sonnet
  owns: tests/conftest.py, requirements-dev.txt, .venv/**
  depends: T17
  uses: stack:python, stack:uv, stack:pytest, rule:python
  check: `python -m pip check && python -c "import streamlit, pandas, ccxt" && python -m pytest -q`
  done: `.venv` created from `requirements-dev.txt` (T18 adds pinned `mypy` and `pandas-stubs` there; needed by T30) (or `uv` if the owner picks ADR-002 option 3); conftest gains a no-network guard and a price-mock fixture shared by T19-T27; 21 still pass.
- [x] T19 [P g1] Tier A: ledger stored rows, holdings inconsistency, migration edge cases
  layer: qa · tier: A · owner: qa-tester · model: sonnet
  owns: tests/test_database.py
  depends: T18
  uses: skill:test-driven-development, stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_database.py`
  done: AC1.1 (stored row values), AC12.1 (four tables listed, second `init_database()` changes nothing), AC12.4, AC12.5; characterization of D4: `get_current_portfolio` vs `get_portfolio_at_date` USDT differ after a crypto buy.
- [x] T20 [P g1] Tier A: history income math and edge cases
  layer: qa · tier: A · owner: qa-tester · model: opus
  owns: tests/test_portfolio_calculator.py
  depends: T18
  uses: skill:test-driven-development, stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_portfolio_calculator.py`
  done: AC7.1 (empty frame and columns), AC7.4 (funding income 1.0), AC7.5 (pool 500 -> 200), AC7.6 (missing price excluded, D9), AC7.7 (pre-2022 transaction ignored, D2); characterization of D5: last-month income in columns, not in `total_value`.
- [x] T21 [P g1] Metrics edge cases and annualization characterization
  layer: qa · tier: B · owner: qa-tester · model: sonnet
  owns: tests/test_metrics.py
  depends: T18
  uses: stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_metrics.py`
  done: AC8.7, AC8.8 (365- or 366-day series, stated tolerance), AC8.9; D1 pinned: volatility uses sqrt(252) regardless of row spacing.
- [ ] T22 [P g1] Market data: cache, normalization, errors, price discovery (mocked ccxt)
  layer: qa · tier: B · owner: qa-tester · model: sonnet
  owns: tests/test_price_fetcher.py, tests/test_assets.py
  depends: T18
  uses: stack:pytest, mcp:context7, rule:tests
  check: `python -m pytest -q tests/test_price_fetcher.py tests/test_assets.py`
  done: AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC4.1, AC4.2, AC4.4; `CACHE_FILE`/`ASSETS_CACHE_FILE` patched to tmp; no network.
- [ ] T23 [P g1] Backtest loaders and engines (synthetic and mocked data)
  layer: qa · tier: B · owner: qa-tester · model: sonnet
  owns: tests/test_backtest_data.py, tests/test_backtest_engines.py
  depends: T18
  uses: stack:pytest, stack:pandas, rule:tests
  check: `python -m pytest -q tests/test_backtest_data.py tests/test_backtest_engines.py`
  done: AC10.1, AC10.2, AC10.3, AC10.4, AC10.5, AC10.6, AC10.7; every frame asserts `attrs['synthetic']` per CLAUDE.md.
- [ ] T24 [P g1] Rate inputs auto-populate and helper scripts on a tmp DB
  layer: qa · tier: B · owner: qa-tester · model: sonnet
  owns: tests/test_rates_and_scripts.py
  depends: T18
  uses: stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_rates_and_scripts.py`
  done: AC5.3, AC6.3 (fixed clock 2025-10-15 via AppTest button click or patched datetime; 92 and 46 rows), AC5.4 (`delete_funding_rate`), AC14.1 (`DB_PATH` patched), AC14.2 (rate tables of both populate scripts equal; drop the case when T31 removes the duplicate).
- [ ] T25 [P g1] Page smoke (AppTest): dashboard and transactions
  layer: qa · tier: C · owner: qa-tester · model: sonnet
  owns: tests/test_pages_ledger.py
  depends: T18
  uses: mcp:context7, stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_pages_ledger.py`
  done: AC1.3, AC1.4, AC1.5, AC1.6, AC1.7, AC1.8, AC2.6, AC2.7, AC4.3 with tmp DB and mocked `get_price`/`get_current_price`/`find_dates_by_price`; AppTest API checked via context7.
- [ ] T26 [P g1] Page smoke (AppTest): funding, pools, analytics, backtest, guide
  layer: qa · tier: C · owner: qa-tester · model: sonnet
  owns: tests/test_pages_other.py
  depends: T18
  uses: mcp:context7, stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_pages_other.py`
  done: AC5.2, AC6.2, AC6.4, AC9.1, AC9.2, AC9.3, AC9.4, AC10.8, AC10.9, AC11.1; backtest runs on synthetic data only.
- [ ] T27 [P g1] Runtime and secrets checks as tests
  layer: qa · tier: B · owner: qa-tester · model: haiku
  owns: tests/test_runtime_config.py
  depends: T18
  uses: stack:pytest, rule:tests
  check: `python -m pytest -q tests/test_runtime_config.py`
  done: AC13.1 (config address), AC13.3 (`git ls-files data` empty, `data/portfolio.db` ignored), AC13.4 (no `getenv`/API key in `*.py`), AC11.2 (no `st.image`/perplexity in guide).
- [ ] T28 Phase 3 build gate
  layer: infra · tier: C · owner: devops · model: haiku
  owns: -
  depends: T19, T20, T21, T22, T23, T24, T25, T26, T27
  uses: stack:pytest
  check: `python -m compileall -q main.py pages utils scripts && python -m pytest -q`
  done: 0 failed, 0 skipped; `git status` shows no change under `data/`; counts pasted in STATE.

## Phase 4 — Gaps and tech debt (open; small, no behaviour change except F15)
- [ ] T29 [P g2] Disclaimer in README, dashboard and Backtest page (F15)
  layer: frontend · tier: B · owner: frontend-dev · model: haiku
  owns: README.md, main.py, pages/backtest.py
  depends: T28
  uses: rule:tests
  check: `python -c "import pathlib,sys;p='Not investment advice';sys.exit(0 if all(p.lower() in pathlib.Path(f).read_text(encoding='utf-8').lower() for f in ['README.md','main.py','pages/backtest.py']) else 1)" && python -m pytest -q`
  done: AC15.1, AC15.2; exact family text from SPEC line 8.
- [ ] T30 [P g2] mypy cleanup (non-strict, ADR-003)
  layer: backend · tier: B · owner: backend-dev · model: sonnet
  owns: utils/portfolio_calculator.py, utils/backtest_data.py, utils/backtest_alt_mn.py, utils/metrics.py
  depends: T28
  uses: rule:python, stack:pandas
  check: `python -m mypy --ignore-missing-imports utils main.py && python -m pytest -q`
  done: 8 errors in 4 files (2026-10-25, re-run by lead) -> 0, annotations only, tier A tests of T20 still green; strict mode only if the owner picks ADR-003 option 3.
- [ ] T31 [P g2] Remove the duplicate root populate script
  layer: backend · tier: B · owner: backend-dev · model: haiku
  owns: populate_funding.py, tests/test_rates_and_scripts.py
  depends: T28
  uses: none
  check: `python -c "import pathlib,sys;sys.exit(1 if pathlib.Path('populate_funding.py').exists() else 0)" && python -m pytest -q`
  done: `scripts/auto_populate_funding.py` is the only copy; AC14.2 case removed from T24's file; `scripts/migrate_database.py` (unsafe legacy migrator) listed for the owner, not removed.
- [ ] T32 Replace deprecated `use_container_width` (24 uses)
  layer: frontend · tier: C · owner: frontend-dev · model: haiku
  owns: main.py, pages/**
  depends: T29
  uses: mcp:context7, skill:data-visualization
  check: `python -c "import pathlib,sys;n=sum(pathlib.Path(f).read_text(encoding='utf-8').count('use_container_width') for f in ['main.py',*map(str,pathlib.Path('pages').glob('*.py'))]);sys.exit(1 if n else 0)" && python -m pytest -q tests/test_pages_ledger.py tests/test_pages_other.py`
  done: 0 uses; replacement argument (`width='stretch'`) verified for streamlit 1.66.1 via context7; page smoke tests green.
- [ ] T33 Phase 4 build gate
  layer: infra · tier: C · owner: devops · model: haiku
  owns: -
  depends: T29, T30, T31, T32
  uses: stack:pytest
  check: `python -m compileall -q main.py pages utils scripts && python -m mypy --ignore-missing-imports utils main.py && python -m pytest -q`
  done: green output pasted in STATE.

## Phase 5 — Hardening (always last, in this order)
- [ ] T34 Review fixes (from REVIEW.md)
  layer: backend · tier: A · owner: backend-dev · model: opus
  owns: utils/**, pages/**, main.py, tests/**
  depends: T33
  uses: rule:tests, skill:test-driven-development
  check: `python -m compileall -q main.py pages utils scripts && python -m pytest -q`
  done: every P0/P1 row of the review (reviewer + security-reviewer: integrity checklist, DNS-rebinding residual risk of ADR-004, D1-D13 sanity) fixed or waived by the owner; known-debt items stay unless the owner says otherwise.
- [ ] T35 QA pass (QA.md)
  layer: qa · tier: A · owner: qa-tester · model: sonnet
  owns: docs/QA.md
  depends: T34
  uses: rule:tests, stack:pytest
  check: `python -m pytest -q && python -c "import pathlib,sys;sys.exit(0 if pathlib.Path('docs/QA.md').is_file() else 1)"`
  done: risk map per tier; AC13.2 (netstat shows `127.0.0.1:<port>`), `/_stcore/health` 200, all 7 pages load; one read-only real Binance smoke (prices only, never the personal DB).
- [x] T36 README and CHANGELOG verified literally
  layer: docs · tier: C · owner: tech-writer · model: haiku
  owns: README.md, CHANGELOG.md
  depends: T35
  uses: none
  check: `python -c "import pathlib,sys;r=pathlib.Path('README.md').read_text(encoding='utf-8').lower();sys.exit(0 if 'not investment advice' in r and pathlib.Path('CHANGELOG.md').is_file() else 1)"`
  done: every README command run as written in the venv; assumptions table (USDT base, 252 annualization D1, estimates in F5/F6, 2022 start D2); disclaimer kept (AC15.1).
- [ ] T37 Release prep (no deploy, no push)
  layer: infra · tier: B · owner: devops · model: sonnet
  owns: docs/RELEASE.md
  depends: T36
  uses: rule:git
  check: `node E:/Main/Dev/coding-brain/scripts/secrets-scan.mjs --project . --history && python -m pytest -q`
  done: RELEASE.md lists version, limitations (D1-D13), owner decisions; merge of `chore/audit` and any push only with the owner's explicit yes.

## Traceability
| SPEC feature / AC | Tasks |
|---|---|
| F1 AC1.1 | T05, T19 |
| F1 AC1.2 | T05, T11 |
| F1 AC1.3, AC1.4, AC1.5, AC1.6, AC1.7, AC1.8 | T10, T25 |
| F2 AC2.1, AC2.2, AC2.3, AC2.4, AC2.5 | T05, T11 |
| F2 AC2.6, AC2.7 | T10, T25 |
| F3 AC3.1, AC3.2, AC3.3, AC3.4, AC3.5 | T07, T22 |
| F4 AC4.1, AC4.2, AC4.4 | T07, T22 |
| F4 AC4.3 | T10, T25 |
| F5 AC5.1 | T05, T11 |
| F5 AC5.2 | T10, T26 |
| F5 AC5.3, AC5.4 | T24 (AC5.4 page step also T26) |
| F6 AC6.1 | T05, T11 |
| F6 AC6.2, AC6.4 | T10, T26 |
| F6 AC6.3 | T24 |
| F7 AC7.1 | T08, T20 |
| F7 AC7.2, AC7.3 | T08, T11 |
| F7 AC7.4, AC7.5, AC7.6, AC7.7 | T20 |
| F8 AC8.1, AC8.2, AC8.3, AC8.4, AC8.5, AC8.6 | T09, T11 |
| F8 AC8.7, AC8.8, AC8.9 | T21 |
| F9 AC9.1, AC9.2, AC9.3, AC9.4 | T10, T26 |
| F10 AC10.1, AC10.2, AC10.3, AC10.4, AC10.5, AC10.6, AC10.7 | T13, T14, T23 |
| F10 AC10.8, AC10.9 | T14, T26 |
| F11 AC11.1 | T15, T26 |
| F11 AC11.2 | T15, T27 |
| F12 AC12.1 | T05, T19 |
| F12 AC12.2, AC12.3 | T06, T11 |
| F12 AC12.4, AC12.5 | T19 |
| F13 AC13.1 | T03, T27 |
| F13 AC13.2 | T03, T35 |
| F13 AC13.3, AC13.4 | T27 |
| F14 AC14.1, AC14.2 | T24, T31 |
| F15 AC15.1 | T29, T36 |
| F15 AC15.2 | T29 |
Known debt (ARCHITECTURE 7.2) is characterized, not fixed: D1 -> T21, D2/D5/D9 -> T20, D4 -> T19, D3 -> T29, D12 -> T18, D13 -> T30, T31, T32; D6, D7, D8, D10, D11 -> review (T34) for the owner's decision.

## Needed from owner
- Answer ADR-001 (SQLite + pandas, no DuckDB/skfolio), ADR-002 (pip pins vs uv), ADR-003 (typing/hypothesis): `docs/adr/`, STATE lines `architecture/adr-00N awaiting user ok`.
- Approve or edit `docs/SPEC.md` (reverse-engineered, pending).
- Decide whether any known debt D1-D13 should be fixed (each fix = new tier A task, test-first).
- Decide: merge `chore/audit` into `main` and push (nothing pushed).
- Local-only vs hosted: hosting needs auth + Dockerfile + external DB (not built; ADR-004).
