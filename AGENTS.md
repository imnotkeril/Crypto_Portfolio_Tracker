# AGENTS.md — Crypto Portfolio Tracker

Instructions for any coding agent (Cursor, Codex, Claude Code).

- Goal: local Streamlit tracker for a personal crypto portfolio (transactions, funding, pools, metrics, backtests).
- Stack: Python 3.11+, Streamlit, pandas, ccxt, SQLite, pytest.
- Read first: `docs/STATE.md` (progress), `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/plan.md`.
- Shared conventions: `E:/Main/Dev/coding-brain/rules/` (only the files relevant to your task) and `E:/Main/Dev/coding-brain/known-traps.md`.
- Work one task from `docs/plan.md` at a time; verify (`python -m pytest -q`), tick it, add a line to `docs/STATE.md`, commit locally.
- Never commit secrets (`.env*`) or `data/`. Never push or deploy without the owner's approval.
- Code, comments and docs in English.
