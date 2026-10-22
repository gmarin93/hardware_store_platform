# Prompt analysis and repository baseline

Prepared on 2026-10-21, America/Costa_Rica.

## Verified baseline

The owner confirmed the target as `/Users/glenmarin/Documents/Development/hardware_store/hardware_store_platform`. Inspection found only `.git`; Git reported no commits on `main` and an unavailable tracked `origin/main` reference. No remote fetch was performed. No application, dependencies, database, API, tests, inventory feed or catalog dataset was present. Do not infer a remote repository is empty from this local observation.

Claude Code is installed locally as version 2.1.283. The neighboring Powerhouse project is unrelated and must not be used as an existing hardware-store implementation.

## What to retain from the source

Keep the modular Django backend, typed Next.js frontend, inventory authority distinction, Costa Rican vocabulary, provenance, branch permissions, transactional reservations, validated AI references and concrete safety evaluations. These are strong foundations.

## What to change

| Source issue | Revised instruction |
| --- | --- |
| Describes an EXISTING app despite an empty target | Inspect first; bootstrap only when no existing application is found |
| Asks one assistant to hold many expert roles | Main-session coordinator plus bounded specialist assignments |
| Includes payment placeholders and later POS/payment integration | Exclude all payment processing and payment placeholders |
| Introduces many apps/screens immediately | Activate domain modules only in the relevant phase |
| Delays complete deterministic sales workflow until after AI | Prove quote → order → reservation → fulfillment before AI |
| Leaves reservation, money and quotation lifecycles implicit | Freeze explicit service contracts and concurrency invariants |
| Allows broad free-form AI explanations | Keep factual store claims evidence-bound in cards and prose |
| Says phases are approved without an approval mechanism | User-requested phase defines implementation scope; ledger tracks evidence |
| Lists tests without requiring reproducible completion records | Each task records commands, actual results, limitations and review |
| Blurs coding-agent orchestration and runtime AI | Coding specialists do not require a multi-agent runtime application |

## Requirements-to-existing-code matrix

Status is application implementation status at inspection, not documentation completeness.

| Requirement | Status | Delivery |
| --- | --- | --- |
| Architecture and decision package | PARTIAL | This draft; Phase 0 validates defaults |
| Next.js/Django/Postgres runtime | MISSING | P1 |
| Authentication and branch/object permissions | MISSING | P1 |
| Canonical catalog, variants and units | MISSING | P1 |
| Import provenance, validation and synonyms | MISSING | P2 |
| Exact/fuzzy/structured search | MISSING | P2 |
| Live inventory authority and freshness | MISSING | P3; actual source remains a decision |
| Reservations, locking, expiry and audit | MISSING | P3 |
| Quotations, pricing snapshots and operational orders | MISSING | P3 |
| Grounded AI and safety evaluation | MISSING | P4 |
| Customer and employee end-to-end experience | MISSING | P1–P5 |
| Warehouse picking and fulfillment | MISSING | P3/P5 |
| Delivery, transfers, returns and management analytics | MISSING | Optional P6 |
| Semantic retrieval and photo interpretation | MISSING | Optional P6, evidence-driven |
| Real dataset rights, price feed and stock feed | MISSING | No sources supplied; production blocker |
| Payment gateway/processing | EXCLUDED | Explicit owner request |

No existing implementation was assessed as COMPLETE or UNSAFE because none exists locally. Proposed risks are in the risk register, not claims about found vulnerabilities.

## Initial deliverables mapping

A: baseline here. B: matrix here and RISKS.md. C/D: ARCHITECTURE.md. E: DOMAIN_CONTRACTS.md. F: source-authority section in DOMAIN_CONTRACTS.md and DECISIONS.md. G: DELIVERY_PLAN.md/tasks.json. H: DECISIONS.md.
