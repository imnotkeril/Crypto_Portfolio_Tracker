# Crypto Portfolio Tracker

Streamlit app (SQLite, ccxt/Binance public data). Family: webapp/tool (local only, no auth).

- Run: `streamlit run main.py` (binds 127.0.0.1 via `.streamlit/config.toml`)
- Test: `python -m pytest -q` (throwaway DB, mocked prices; never touch `data/portfolio.db`)
- Deps pinned in `requirements.txt`; Python 3.11+
- Never commit `data/` (personal DB). Back up the DB by copy before schema changes.
- Backtests must flag synthetic data (`df.attrs['synthetic']`).
- State: `docs/STATE.md`, plan: `docs/plan.md`, audit: `docs/AUDIT_2026-10-24.md`
