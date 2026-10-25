# ADR-001: Storage and analytics on SQLite + pandas/numpy; no DuckDB/parquet, no skfolio/riskfolio

- Status: proposed (reverse-engineered: the code already works this way; deviates from the router default, awaiting owner ok)
- Date: 2026-10-25
- Deciders: architect (records); owner (must confirm)

## Context and problem
Router `finance/portfolio-risk` defaults to parquet + `stack:duckdb` for research data and `stack:skfolio` (alternative riskfolio-lib) behind an own `portfolio/` wrapper, and its architecture row asks for an "ADR: skfolio vs riskfolio". The existing app (SPEC F1-F14) stores a personal ledger and monthly rate inputs in one SQLite file and computes history and metrics with pandas/numpy. SPEC section 3 lists optimizer, weights, rebalancing, VaR/CVaR and stress tests as non-goals.

## Decision drivers
- SPEC scope: a tracker, not an allocator (no optimizer, no covariance estimation).
- Data size: hundreds to low thousands of rows, one user, operational CRUD (insert/delete rows).
- The family rule itself says SQLite is right for operational state; DuckDB is for research datasets.
- Adoption mode: document what exists, no rewrite.

## Considered options
1. Keep SQLite (`data/portfolio.db`) + pandas/numpy; no optimizer library.
2. Router default: parquet + DuckDB for prices, SQLite for the ledger, skfolio wrapper.
3. riskfolio-lib instead of skfolio.

## Decision
Chosen: **option 1**, because the product has no optimizer, no covariance estimator and no research dataset to query; the data is small operational state that the family rules place in SQLite. skfolio vs riskfolio: **neither**; the question becomes live only if the owner adds an allocation feature (new SPEC feature, new ADR, shrinkage covariance by default per router).

## Consequences
- Good: zero new dependencies; one file to back up; CRUD with parameterized SQL already works and is tested (tests/test_database.py).
- Bad / debt: prices live in a JSON cache (`data/cache/price_cache.json`) with no manifest, no content hash and no quality gates; no shared returns layer to plug an optimizer into later; router "Done when" items about weights/constraints are not applicable.

## Pros and cons of the options
- 1: + matches SPEC and data size, no migration / - no reproducible data snapshot for research.
- 2: + router-aligned, hashable parquet snapshots / - rewrite of the price layer for a 1-user tracker; out of adoption scope.
- 3: + more risk measures / - same as 2, and nothing in SPEC needs it.

## Confirmation
`requirements.txt` contains no duckdb/skfolio/riskfolio; `python -m pytest -q tests/test_database.py` green; owner answer recorded here and in docs/STATE.md (`- [x] architecture/adr-001 - user ok <date>` or a new ADR).
