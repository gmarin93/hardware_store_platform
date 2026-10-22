# Decisions and assumptions

The owner authorized the planning/Claude setup and confirmed the path. Proposed defaults below are design recommendations, not asserted business facts. Reversible technical defaults were frozen in Phase 0 in [ADR 0001](../architecture/decisions/0001-technical-defaults.md). Unresolved commercial, safety or data-authority choices block only dependent work.

Status values: CONFIRMED (owner), DEFAULT-FROZEN (reversible technical default, adopted), PROPOSED (needs owner confirmation), OPEN (no default; owner input required).

| ID | Decision | Status | Default / next action | Blocks |
| --- | --- | --- | --- | --- |
| D01 | Payment scope | CONFIRMED | No gateway or processing, including placeholders | All work |
| D02 | Organization model | CONFIRMED 2026-10-21 | One business, multiple branches; ownership on all business records; second synthetic org in tests only | — |
| D03 | Language/currency | CONFIRMED 2026-10-21 (Spanish first) | es-CR UI and error messages; CRC configurable (currency first used in P3, not yet confirmed) | — |
| D04 | Product source and usage rights | OPEN | No data supplied. Synthetic fixtures only; no scraping/remote fetch until source and permitted use confirmed | Real import (P2 real data) |
| D05 | Inventory authority | OPEN | Local manual-authority mode proposed; external feed needs its own source contract | Real availability/reservations (P3) |
| D06 | Freshness / reservation duration | OPEN | Configurable per source and operation; tests use labeled illustrative durations | P3 production use |
| D07 | Public availability exposure | PROPOSED | Availability bands public; exact quantities staff-only | P3-01 public serializer |
| D08 | Sales units | DEFAULT-FROZEN (P1 subset) | ADR 0001: NUMERIC(14,3), unit enum, increment/min, sales_unit == stock_unit in P1; conversions via P3 ADR | P1 schema; P3 conversions |
| D09 | Prices/tax/rounding | OPEN | Synthetic default in ADR 0001 (scale 4/2, HALF_UP, line-level, tax-exclusive) labeled non-production; real tax basis/rates and quote validity need business confirmation | Production quote issuance |
| D10 | Identity | CONFIRMED 2026-10-21 | Same-origin Django DB sessions + CSRF; guest catalog browsing; customer auth for quotes | — |
| D11 | Roles and staff authority | CONFIRMED 2026-10-21 | Roles: ADMIN, EMPLOYEE, CUSTOMER, GUEST. Employee is branch-scoped and covers sales and warehouse work; admin is organization-wide. Matrix in DOMAIN_CONTRACTS. Discount overrides deferred; no cashier payment role | — |
| D12 | Fulfillment | PROPOSED | Complete order; one branch per order; explicit unpick for cancellation during picking | P3 |
| D13 | Runtime AI provider | OPEN | Keep adapter. Candidate OpenAI Agents SDK per source prompt; choose pinned SDK/model at P4 and approve budget | Provider-backed P4 work |
| D14 | Search/queues | DEFAULT-FROZEN | Postgres exact/full-text/trigram; no embeddings/Redis/Celery until measured need | — |
| D15 | Photos/privacy | PROPOSED | Real catalog images in MVP; customer uploads deferred pending consent/retention | Optional P6 |
| D16 | Hosting/production | OPEN | Local Compose only | Production deployment |
| D17 | Scale/latency | OPEN | Agree catalog size, peak load, latency and AI cost budgets with measured fixtures | P5 release gate |
| D18 | Versions | DEFAULT-FROZEN (method) | ADR 0001 selection method; exact versions recorded in ADR 0002 during P1-01 | P1-01 installation |
| D19 | Customer onboarding | OPEN | P1: fixtures/management command only. Self-registration vs staff-created customers to decide | P3 customer journeys |
| D20 | P1 network use | CONFIRMED 2026-10-21 | Owner authorized full local P1 setup: official docs/compatibility pages, pinned PyPI and npm installs, pinned Docker image pulls, Playwright browser download. No deploys, pushes or paid services | — |
| D21 | Claude permission hardening | CONFIRMED 2026-10-21 | `.claude/settings.json` deny rules for env files, credential stores and git push; `hardware-build` has disable-model-invocation and requires an explicit phase. Limitation: Read rules do not stop Bash from reading a file; prose rules still apply | — |
| D23 | Employee duty split | OPEN (optional) | Coordinator mapping: employees may quote, convert, pick, fulfill and cancel (incl. explicit unpick) in their branches; stock adjustments, prices, staff management and audit are admin-only. Owner may restrict any of these before P3 | P3-01/P3-03 |
| D22 | Node runtime | OPEN | Local Node v20.19.2 may not meet current Next.js minimum or support window; P1-01 verifies. If unsuitable: pinned Compose Node image or owner-installed LTS | P1-01 |

Use ADRs under docs/architecture/decisions/ when decisions are resolved. Record context, choice, alternatives, consequences and validation. A ledger approval flag cannot substitute for the owner's authorization. Never log secrets or customer data as decision evidence.
