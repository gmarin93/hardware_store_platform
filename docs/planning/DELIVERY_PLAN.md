# Delivery plan

Implement small vertical slices and preserve every completed gate. A task is eligible only when dependencies, authorization and required decisions permit it. The detailed backlog is tasks.json; all implementation tasks begin pending. Timelines are deliberately unestimated until team capacity, data quality and integrations are known.

## P0 — Inspect and freeze the plan

P0-01 → P0-02. Recheck the actual repository, source data, architecture and scope. Record framework/version selection method, role matrix, stock/quotation/order states and data authority. Resolve reversible technical choices; identify business decisions that block only real-data use.

Exit: accurate inventory, requirements matrix, architecture, contract draft, risk register and decision ledger. Status 2026-10-21: P0-01 and P0-02 done; owner confirmed D02/D03/D10/D11. P1-01 waits on network authorization D20. Empty repository means bootstrap; unexpected existing code means adapt the plan. Draft documents alone do not complete this gate.

## P1 — Foundation and a catalog vertical slice

P1-01 → P1-02A → P1-02B → P1-03 → P1-04 (serial; contract rev 0.1.0 in ADR 0001). Establish pinned runtimes and reproducible local Compose, Django auth/CSRF, branch membership, canonical variants and API schema. Connect typed Next.js catalog views with labeled synthetic fixtures.

Exit: services start; migrations apply from empty Postgres; actual API and browser journey pass; unauthorized access and private-cache cases fail safely. Record verified commands under docs/development/CHECKS.md. No blanket test command is claimed before project scripts exist.

## P2 — Import and product discovery

P2-01 → P2-02 → P2-03 → P2-04. Stage imports with provenance and validation reports. Add exact SKU, full-text/trigram, synonyms and structured constraints. Show real candidate catalog images and useful empty/error states.

Exit: import reruns do not duplicate; incompatible variants remain separate; prices/stock are not silently promoted; deterministic search fixture results meet a recorded target. No scraping or source publication without permitted-use confirmation.

## P3 — Inventory and complete commercial operations

P3-01 → P3-02 → P3-03 → P3-04 → P3-05. Implement authority/freshness, stock ledger, reservation locks, authoritative prices, quote versions, accepted-quote conversion, picking, fulfillment and cancellation.

Exit: quote → order → pick → fulfill works without any payment concept. Real Postgres concurrency tests cover overselling, competing expiry/picking, duplicated conversion/fulfillment and multi-line rollback. Verify UNKNOWN versus zero, permission scope, decimal units and rounding. Real-store use stays blocked until source and business settings are confirmed.

## P4 — Grounded AI sales assistant

P4-01 → P4-02 → P4-03 → P4-04. Add one runtime adapter and permission-scoped tools. Implement clarification and safety behavior, evidence validation, server-hydrated cards and user-confirmed quote draft creation.

Exit: six canonical scenarios plus adversarial/failure cases pass. Offline fixtures and live-provider behavior are recorded separately. Hard gate: zero fabricated store claims or critical unsafe advice in the release suite. Provider evaluation needs selected model, version, explicit budget and permitted data.

## P5 — Operational readiness

P5-01 → P5-02 → P5-03 → P5-04. Complete scoped management APIs and service hardening, management surfaces, mobile/accessibility verification, observability, rate limits, retention, backup/restore and operational documentation.

Exit: representative customer/employee journeys, restore rehearsal, permissions, security and failure-mode tests pass. Performance/cost targets are measured. Production launch is a separate decision requiring resolved business/data/hosting assumptions.

## P6 — Optional extensions

Scope each separately: branch transfers, delivery assignment/proof of delivery, returns to inventory, partial fulfillment, manager analytics, richer promotions, photo interpretation and semantic retrieval. Restore the source prompt's wider ambitions only as selected work with new contracts. Payment work remains excluded.

## Rollback and evidence

For each slice, document changed files, database changes, required commands and result evidence in docs/evidence/{task-id}.md. Prefer additive migrations and backwards-compatible API changes. Rehearse migrations on disposable synthetic databases. Describe rollback limits before destructive migrations; use backups and forward fixes for irreversible transformations, never promise that every migration can be reversed.

No destructive reset of shared data to make tests pass. Local fixtures must be isolated from real data. After source changes invalidate evidence, rerun affected checks before marking done.
