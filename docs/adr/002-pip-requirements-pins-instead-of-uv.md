# ADR-002: pip + pinned requirements.txt on Python 3.11+ instead of uv + uv.lock on 3.12

- Status: proposed (reverse-engineered from commits c3ccdb3, d7a17f9; deviates from the router default, awaiting owner ok)
- Date: 2026-10-25
- Deciders: architect (records); owner (must confirm)

## Context and problem
The finance family default is `stack:python` 3.12 + `stack:uv` (`pyproject.toml`, committed `uv.lock`, `.python-version`, `.venv`, everything via `uv run`), see `rules/python.md` and `blueprint:finance-research`. The project uses `pip install -r requirements.txt` with 8 top-level `==` pins and `requirements-dev.txt` (pytest 9.1.1); README states Python 3.11+ (pandas 3 needs >= 3.11). There is no `pyproject.toml`, no lockfile and no project `.venv`.

## Decision drivers
- Adoption mode: the owner's workflow and README already use pip.
- Reproducibility (family rule): installs must be repeatable.
- Observed 2026-10-25: the machine's global Python 3.11.9 has streamlit 1.57.0, pandas 3.0.2, numpy 1.26.4 (not the pins) and `import streamlit` fails because transitive `starlette` 0.27.0 is too old (`pip check`: streamlit requires starlette>=0.40.0). Top-level pins alone do not pin transitive packages.

## Considered options
1. Keep pip + top-level pins (current).
2. pip + fully frozen lock (`pip freeze` / pip-tools) in a project `.venv`.
3. Router default: uv project (`uv init`, `uv add` the same pins, commit `uv.lock`, `.python-version` 3.12).

## Decision
Chosen for now: **option 1 as the documented current state**; the architect does not switch tools in adoption mode. Recommendation for the owner: option 3 (router default) or at least option 2, because option 1 does not pin transitive dependencies (proved by the starlette break above). Plan task T18 creates a project `.venv` from the pins either way.

## Consequences
- Good: no change for the owner; README commands work as written in a clean venv (audit 2026-10-24).
- Bad / debt: transitive dependencies float; no `.python-version`; family checks written as `uv run ...` are run as `python -m ...` in this project.

## Pros and cons of the options
- 1: + zero effort / - non-reproducible transitive set.
- 2: + full lock with familiar pip / - lock is per-platform, manual refresh.
- 3: + router-aligned, cross-platform lock, interpreter pinned / - new tool for the owner; Python 3.12 would need a re-run of all tests.

## Confirmation
Owner answer recorded here and in docs/STATE.md. If option 3 is chosen: `uv sync --locked && uv run pytest -q` green; if option 1/2: `python -m pip check` clean inside `.venv`.
