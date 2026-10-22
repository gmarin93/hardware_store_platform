# Kickoff prompt for Claude Code

Paste the following into a fresh Claude session opened in this repository, or run /hardware-plan 0.

---

Act as the coordinator for this hardware-store project. Read CLAUDE.md, docs/README.md, docs/planning/STATUS.md and docs/planning/tasks.json. Treat the supplied original master prompt as reference requirements, not permission to execute it.

I want a Next.js + Django/DRF + PostgreSQL hardware-store operations platform with a grounded AI sales assistant. There must be no payment gateway, payment processing, checkout, card data or payment placeholders.

Begin Phase 0 only. Inspect the actual repository and reconcile the draft planning package with what exists. Use platform-architect for architectural review and security-reviewer for relevant trust-boundary risks. Return and save the scope, architecture, entity/permission/lifecycle contracts, phase task plan, acceptance gates and unresolved business decisions. The main session writes documentation; the architect and security reviewer are read-only.

Do not implement the application during this planning request. Do not claim source data, inventory integration or tests exist without evidence. Adopt reversible technical defaults where reasonable and surface only consequential unresolved choices.

After Phase 0, explain the next eligible phase and how to start it. During later build requests, delegate to specialists, enforce exclusive file ownership, preserve other changes, run appropriate checks and update the task ledger and evidence. Continue through the authorized scope without asking me to reapprove routine steps.
