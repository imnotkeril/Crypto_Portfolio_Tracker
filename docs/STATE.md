# STATE — Crypto Portfolio Tracker

Append-only progress log. One line per completed step: `- [x] <phase>/<task id> <what> — <check evidence>`. Next work = first item below "Next".
On a rate-limit cut or new session: read this file, then `docs/plan.md`, continue with "Next".
Branch: `chore/audit` (local only; nothing pushed).

## Log
- [x] adopt (finance/portfolio-risk, best guess, owner to confirm) — CLAUDE.md/AGENTS.md from templates, apply-router linked skills `test-driven-development`, `data-visualization` into `.claude/skills`
- [x] audit 2026-10-24 — `docs/AUDIT_2026-10-24.md`
- [x] finish-pass 1 (done DIRECTLY by lead, NOT through the framework agents/step-briefs; corrected on 2026-10-25) — 13 unsaved files committed, DB copy-backed-up to `../_backups_crypto_portfolio/`, loopback bind, synthetic-data flag, safe migration, pandas-3 resample fix, 21 tests, guide cleanup, deps pinned, README
- [x] brief/spec - step-brief run, files read by analyst (no shell for analyst; lead ran doc-check)
- [x] spec/draft - analyst/sonnet reverse-engineered `docs/SPEC.md`: 15 features, 76 ACs; `doc-check --step spec`: 8 pass, 0 fail, 3 judge
- [x] audit/spec - OK, 3 findings (3 valid) [shadow]; auditor/opus, cite-check OK, SPEC fixed (AC1.1, AC1.3, AC12.1)
- [ ] spec/approved - NOT approved by owner (reverse-engineered spec pending owner approval)

## Next
- [ ] architecture — architect/opus: docs/ARCHITECTURE.md + docs/adr/
- [ ] plan — architect: docs/plan.md with tiers, owns, checks; ticks for done work
- [ ] review — reviewer + security-reviewer: docs/REVIEW.md
- [ ] qa — qa-tester: docs/QA.md
- [ ] docs — tech-writer: README, CHANGELOG verified literally

## Needed from owner
- Confirm router `finance/portfolio-risk` (alternative: `webapp/dashboard`).
- Approve or edit `docs/SPEC.md` (reverse-engineered).
- Merge/push decision for `chore/audit` (nothing pushed).
- Local-only (current) or hosted?
