# ADR-003: No strict typing / runtime validation tooling (mypy strict, pyright, beartype, pydantic, hypothesis) today

- Status: proposed (reverse-engineered; deviates from the router default, awaiting owner ok)
- Date: 2026-10-25
- Deciders: architect (records); owner (must confirm)

## Context and problem
Family default: full annotations, `from __future__ import annotations`, mypy strict + pyright strict, `pandas-stubs`, `beartype` on public boundaries, pydantic for config, pandera at data boundaries, `hypothesis` for invariants. The code has partial annotations (`typing.Dict/List/Optional`, `end_date: str = None`), no mypy/pyright config, no beartype/pydantic/pandera/hypothesis dependency. `python -m mypy --ignore-missing-imports utils main.py` on 2026-10-25: 6 errors in 3 files (the audit of 2026-10-24 counted 8 with a different scope). ruff F401 is clean (cc48d85).

## Decision drivers
- Adoption mode, no rewrite; the owner's open item is "mypy cleanup", not "strict mode".
- Tier A money math (ledger, income) benefits most from property tests, which need hypothesis.

## Considered options
1. Keep as is; clean the existing mypy errors in non-strict mode (plan T30).
2. Non-strict mypy clean + hypothesis for tier A invariants only (dev dependency).
3. Router default: mypy strict + pyright strict + beartype + pydantic/pandera.

## Decision
Chosen for now: **option 1 as the documented current state**; plan T30 targets non-strict mypy with 0 errors. Recommendation for the owner: option 2 (small cost, real value for ledger invariants such as "USDT never negative from a buy"). Option 3 is a large change across all files with little benefit for a local single-user tool.

## Consequences
- Good: no new dependencies; plan stays small.
- Bad / debt: no runtime checks at data boundaries (Binance responses, DB rows); invariants are covered only by example tests.

## Pros and cons of the options
- 1: + cheapest / - weakest guarantees.
- 2: + property tests where money moves / - one dev dependency.
- 3: + router-aligned / - touches every module; beartype/pydantic add little to Streamlit pages.

## Confirmation
`python -m mypy --ignore-missing-imports utils main.py` exits 0 after T30; owner answer recorded here and in docs/STATE.md.
