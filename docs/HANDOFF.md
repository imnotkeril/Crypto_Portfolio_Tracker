# Handoff
status: active
date: 2026-11-02
from-chat-tokens: ~300k

## Goal
Bring the local Streamlit crypto portfolio tracker (E:/Main/Dev/Python/Done/Crypto_portfolio) to done under the coding-brain framework, router finance/portfolio-risk (agent's guess, owner not confirmed). No push, PR or deploy without the owner's yes.

## State
- Done: audit, SPEC (reverse-engineered, NOT owner-approved), ARCHITECTURE + 4 ADR, plan (37 tasks, 22 ticked), review (reviewer + security-reviewer), 8 review fixes with regression tests, QA (verdict YELLOW), README simplified with 4 screenshots in docs/img, CHANGELOG 1.0.0.
- Evidence: 76 passed, 0 skipped; compileall ok; doc-check spec/plan 0 fail, architecture 0 fail + 3 owner gates; pip check clean.
- Running: nothing (all test servers stopped).
- Branch/commit: chore/audit @ 3751ea3, tree clean. 38 local commits after 4dd8172, NONE pushed (remote origin exists, main untouched).

## Decisions
- Auditors for architecture and plan ran on sonnet, not fable (fable out of credits): weaker than the opus author, their OK carries less weight; audit/qa and audit/release-prep were not run.
- R-01 left unfixed on purpose: methodology change, needs the owner.
- design-reviewer skipped (default Streamlit widgets); real-browser pass only for Backtest and dashboard, other pages via AppTest.
- DB copy kept at E:/Main/Dev/Python/Done/_backups_crypto_portfolio/ (outside repo).

## Next
1. Activate venv: `.venv/Scripts/python.exe -m pytest -q` (expect 76 passed), then read docs/STATE.md and docs/plan.md (open tasks T22-T35, T37).
2. Do plan tasks in order with `step-brief.mjs --task <id>`: T22-T27 tests for price_fetcher/backtests/pages, T30 mypy (8 errors), T31 duplicate populate script, T32 use_container_width (24 uses).
3. After the owner answers the questions below: implement R-01 (time-weighted returns) and apply the ADR answers.

## Open questions
- R-01 (P1): deposits/withdrawals are counted as performance; make returns time-weighted (recommended) or only document it?
- ADR-001: keep SQLite+pandas (router default is parquet+duckdb+skfolio)?
- ADR-002: keep pip + requirements pins on Python 3.11 (router default is uv + uv.lock)?
- ADR-003: no strict mypy/pyright/pydantic/hypothesis; add hypothesis for tier-A only?
- Approve docs/SPEC.md, confirm router, merge/push chore/audit, local-only or hosted?

## Traps
- Global Python env is broken (streamlit 1.57 + old starlette); always use project .venv. Scratchpad venvs can vanish.
- pip needs `--use-feature=truststore` here (self-signed TLS chain); never disable verification.
- Never run scripts/*.py or the app from the repo root against real data/portfolio.db; use a temp copy with its own data dir.
- Subagents have no shell or browser in some types; run doc-check, pytest and browser checks yourself.

## Verify
- `.venv/Scripts/python.exe -m pytest -q`
- `node E:/Main/Dev/coding-brain/scripts/doc-check.mjs --project . --step plan`
