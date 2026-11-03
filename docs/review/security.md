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
