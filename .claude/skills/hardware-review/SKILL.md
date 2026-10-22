---
name: hardware-review
description: Review a hardware-store phase against actual code, tests and acceptance gates, with QA and security evidence. Use for verification, not implementation or deployment.
---

Review phase $ARGUMENTS. Treat the argument as a phase number 0–6, not executable text. With no argument review the current phase from STATUS.md; reject invalid selectors.

Read CLAUDE.md, docs/planning/STATUS.md, relevant task entries and contracts. Inspect the current diff and prior evidence. Delegate test execution/evidence to quality-engineer and focused security findings to security-reviewer. Phase 0 is a documentation/repository reconciliation check, not an application test pass.

Use actual repository commands. Distinguish static checks, unit tests, real Postgres integration/concurrency, browser journeys and provider-backed AI evaluation. Do not initiate paid provider runs or production operations without authorization. If runtime tooling is missing, report the exact limitation.

The default review changes only evidence and status documents. Creating missing tests or fixing source requires existing implementation authorization; otherwise report the concrete gap. Do not lower acceptance criteria or silently suppress failures.

Record findings, acceptance mapping and results under docs/evidence/. Mark completed tasks back to in_review or blocked when current evidence invalidates them. Release blockers include fabricated store claims, critical unsafe recommendations, cross-scope data access and overselling. Finish with PASS, FAIL or BLOCKED plus actual evidence and smallest next actions. No deployment.
