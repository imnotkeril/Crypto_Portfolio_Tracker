# Crypto Portfolio Tracker

Local Streamlit app: record crypto buys/sells, Coin-M funding and USDT-pool yields, then compute portfolio value history and risk/return metrics; plus two research backtests (funding arb, alt market-neutral). No auth, single user, SQLite.

- Router: finance/portfolio-risk
- Modules: none
- Stack: Python 3.11+, Streamlit 1.66, pandas 3, numpy, plotly, ccxt (Binance public data), statsmodels, SQLite, pytest
- Services: Binance public REST via ccxt (no keys, read-only)
- Decisions: `docs/ARCHITECTURE.md` (ADRs) · Spec: `docs/SPEC.md` · Architecture: `docs/ARCHITECTURE.md` · Plan: `docs/plan.md` · Review: `docs/REVIEW.md` · QA: `docs/QA.md` · Progress: `docs/STATE.md` · Audit: `docs/AUDIT_2026-10-24.md`

(Router was chosen by the agent as best guess; owner to confirm. `Router:` and `Modules:` lines are read by `step-brief.mjs`.)

## Commands
- Run: `streamlit run main.py` (binds 127.0.0.1 via `.streamlit/config.toml`)
- Test: `python -m pytest -q` (throwaway DB, mocked prices; never touches `data/portfolio.db`)
- Install: `pip install -r requirements.txt` (dev: `requirements-dev.txt`)

## Working rules
- Progress lives in `docs/STATE.md`. On session start, resume from its last unchecked step.
- Before each process step and before each plan task, generate its brief and follow it:
  `node E:/Main/Dev/coding-brain/scripts/step-brief.mjs --project . --step <step>` / `--task <id>`.
- After each task: run its check -> tick in `docs/plan.md` -> one line in `docs/STATE.md` -> local commit.
- No push / deploy / prod changes without the user's explicit yes.
- Never commit `data/` (personal DB); copy-backup the DB before any schema change.
- Backtests must flag synthetic data (`df.attrs['synthetic']`); never place real orders (no trading code here).
- Windows: use `python -m pytest`, set `PYTHONIOENCODING=utf-8`.
