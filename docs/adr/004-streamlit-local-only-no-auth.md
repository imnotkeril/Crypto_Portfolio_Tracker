# ADR-004: Streamlit multipage UI, bound to 127.0.0.1, no authentication

- Status: accepted (reverse-engineered; commit aa0da1c; within router defaults: UI is optional and Streamlit is in the family snapshot)
- Date: 2026-10-25
- Deciders: architect (records); owner decision on hosting still open (docs/STATE.md "Needed from owner")

## Context and problem
SPEC F13: the app reads and deletes personal financial data and has no login. The audit (2026-10-24, finding 1) saw Streamlit listening on all interfaces. Router output form is "HTML report + CSV; UI optional"; the project already is a Streamlit app (main.py + 6 pages).

## Decision drivers
- Single owner on one Windows machine; no hosting in SPEC.
- known-traps "Security": localhost apps are reachable cross-origin (CSRF, DNS rebinding).

## Considered options
1. Streamlit on loopback via tracked `.streamlit/config.toml`, no auth.
2. Streamlit behind a reverse proxy with auth (hosting).
3. Replace the UI with static HTML reports (router default output).

## Decision
Chosen: **option 1**: `server.address = "127.0.0.1"`, `browser.gatherUsageStats = false`, port left at the Streamlit default 8501. Streamlit's own XSRF/CORS protections stay at their defaults (not overridden in config.toml); Streamlit offers no Host-header allow-list, so DNS rebinding is a residual risk accepted for a loopback-only personal tool (review item).

## Consequences
- Good: no network exposure; nothing to deploy.
- Bad / debt: any hosting needs auth, a Dockerfile and a server DB (non-goal until the owner decides); the residual DNS-rebinding risk must be re-checked by security review.

## Pros and cons of the options
- 1: + simplest, matches SPEC / - no protection if the bind is overridden (`--server.address 0.0.0.0` or `STREAMLIT_SERVER_ADDRESS`).
- 2: + remote access / - out of scope, needs auth module.
- 3: + router-aligned / - removes the product's main interface.

## Confirmation
`python -c "import tomllib;c=tomllib.load(open('.streamlit/config.toml','rb'));assert c['server']['address']=='127.0.0.1'"` exits 0 (plan T03); QA records `netstat` showing `127.0.0.1:<port>` (AC13.2).
