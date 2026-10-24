# Plan (adopted from audit 2026-10-24)

Branch: `chore/audit` (local only, never pushed).

## Done
- [x] Commit 13 unsaved files (backtests, assets, dynamic portfolio); DB backed up by copy to `../_backups_crypto_portfolio/`
- [x] Bind Streamlit to 127.0.0.1 (`.streamlit/config.toml`, tracked)
- [x] Backtests flag synthetic/assumed data explicitly (`df.attrs`, red warning in UI)
- [x] Safe legacy DB migration (file backup, one transaction, row-count check, errors raised)
- [x] Fix pandas 3 `resample('M'/'Y')` -> `ME`/`YE` (monthly/yearly returns crashed)
- [x] Tests: 21 (database, metrics, portfolio_calculator) - `python -m pytest -q`
- [x] Clean `pages/guide.py` (chat leftovers, external logo, footnotes)
- [x] Pin deps (`requirements.txt`), `requirements-dev.txt`, README Python 3.11+
- [x] Remove unused imports (ruff F401)

## Remaining (doable, optional)
- [ ] Replace deprecated `use_container_width` (24 uses) with `width='stretch'`
- [ ] mypy cleanup (8 annotation errors), remaining ruff style items
- [ ] Remove duplicate `populate_funding.py` (root) vs `scripts/auto_populate_funding.py`
- [ ] Tests for backtest engines and price_fetcher (needs mocked ccxt)
- [ ] Real-data backtest run (needs network to Binance futures; not run in audit)

## Needed from owner
- Decide: merge `chore/audit` into `main` and push (nothing pushed).
- Local-only vs hosted: hosting needs auth + Dockerfile + external DB (not built).
