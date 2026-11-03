# Audit: plan (docs/plan.md)
mode: shadow
author-model: opus · auditor-model: sonnet (fallback; fable out of credits, so this verdict carries less weight)

## Verdict
FIX
T30/T33 `check` (mypy over `utils main.py`) cannot reach exit 0 as planned: mypy is not in the project venv recipe and one erroring file is not owned by T30.

## Checklist
| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | every task has all fields incl. `uses`; `check` is a command | PASS | docs/plan.md:15 "uses: blueprint:finance-research, stack:python, stack:pandas" [script] 37 tasks |
| 2 | every chosen module appears in some task's uses; router phase-skills of build in some task's uses; blueprint in T01 | PASS | docs/plan.md:15 "uses: blueprint:finance-research, stack:python, stack:pandas" [script: no modules]; JUDGE: step-brief lists mcp:context7 and skill:test-driven-development (and data-visualization), all used (T06, T22, T10) |
| 3 | no two tasks in one [P gN] group share an owns path | PASS | docs/plan.md:144 "- [ ] T19 [P g1] Tier A: ledger stored rows, holdings inconsistency, migration edge cases" [script] 2 groups; I also compared g1 and g2 by hand, disjoint |
| 4 | depends graph has no cycle; T01 has no dependencies | PASS | docs/plan.md:14 "depends: -" [script] |
| 5 | each phase ends with a build gate task | PASS | docs/plan.md:207 "- [ ] T28 Phase 3 build gate" [script] 6 phases (Hardening ends with release prep, accepted by script) |
| 6 | every P1 AC is in the traceability table | PASS | docs/plan.md:283 "| SPEC feature / AC | Tasks |" [script] 57 ACs mapped |
| 7 | Hardening phase exists | PASS | docs/plan.md:252 "## Phase 5 — Hardening (always last, in this order)" [script] |
| 8 | slices vertical, tasks small enough; tier/model match risk (JUDGE) | PASS | docs/plan.md:49 "layer: data · tier: A · owner: backend-dev · model: opus" ; tier A on money/data/migration tasks T03, T05, T06, T08 |
| 9 | Audit done per rules/audit.md; doc-check exits 0 | PASS | doc-check: all PASS, only 3 JUDGE items (judged here); this file is the audit, Disposition and STATE line are the orchestrator's step |

Sample verification (venv interpreter): done-task checks T01, T02, T03, T07, T09-gate (pytest 21 passed), T06 (-k migration 2 passed), T14, T15, T16 (ruff F401) all exit 0. Commit hashes in done fields all exist in `git log` and match the claimed work (4dd8172, f406b52, 67762bd, de35545, c3ccdb3, d7a17f9, aa0da1c, ead29a9, e9e7dd3, 92da55e, b245d7a, 31b0030, cc48d85).

## Findings
- A-01 | P1 | source: step:plan | at: docs/plan.md:225 | quote: "owns: utils/portfolio_calculator.py, utils/backtest_data.py, utils/backtest_alt_mn.py" | scenario: T30 check runs mypy on all of utils and main.py; today mypy reports errors in utils/metrics.py:207 too (8 errors in 4 files, not 6), and metrics.py is owned by no open task, so a T30 agent restricted to its owns cannot make the check exit 0 and T33 stays red | fix: add utils/metrics.py to T30 owns (and correct the error count)
- A-02 | P1 | source: step:plan | at: docs/plan.md:228 | quote: "check: `python -m mypy --ignore-missing-imports utils main.py && python -m pytest -q`" | scenario: the plan says the venv is built from requirements-dev.txt (T18), which contains only requirements.txt and pytest==9.1.1; mypy and pandas-stubs are absent, so in the planned environment the check fails with 'No module named mypy' and no task owns requirements-dev.txt to add it | fix: have T30 (or T18) own requirements-dev.txt and pin mypy and pandas-stubs
- A-03 | P2 | source: step:plan | at: docs/plan.md:237 | quote: "Replace deprecated `use_container_width` (24 uses)" | scenario: grep finds 29 occurrences in main.py and pages today; the stated count misleads sizing but the check (zero occurrences) is still correct | fix: correct the number

## Notes (non-blocking)
- N-01 | opinion | at: docs/plan.md:8 | Riskiest assumption: that the T18 venv from requirements-dev.txt reproduces a working toolchain (mypy, ruff, pytest); ruff (T16 check) is also not in requirements-dev.txt.
- N-02 | opinion | at: docs/plan.md:279 | T37 check calls the secrets-scan script by an absolute brain path, which ties the plan to one machine.

## Disposition
| id | verdict | by | note |
|---|---|---|---|
| A-01 | valid | lead 2026-10-25 | mypy re-run: 8 errors in 4 files incl. utils/metrics.py:207; T30 owns + count fixed |
| A-02 | valid | lead | requirements-dev.txt had only pytest; T18 now owns it and adds mypy/pandas-stubs |
| P2 (24 vs 29 uses) | invalid | lead | `grep -rn use_container_width --include=*.py .` = 24 in the repo (auditor count likely included docs) |

Read: E:/Main/Dev/coding-brain/agents/auditor.md, E:/Main/Dev/coding-brain/rules/audit.md, E:/Main/Dev/coding-brain/process/plan.md, docs/plan.md, docs/SPEC.md (lines 8, 159-173 only), requirements-dev.txt, step-brief build output, doc-check plan output
