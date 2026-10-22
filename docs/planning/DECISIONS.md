# Decisions and assumptions

The owner authorized the planning/Claude setup and confirmed the path. Proposed defaults below are design recommendations, not asserted business facts. Claude can adopt reversible technical defaults during an authorized build; unresolved commercial, safety or data-authority choices block only dependent work.

| ID | Decision | Proposed default / next action | Required before |
| --- | --- | --- | --- |
| D01 | Payment scope | CONFIRMED: no gateway or processing, including placeholders | All work |
| D02 | Organization model | One business, multiple branches; ownership on all business records | P0 freeze |
| D03 | Language/currency | Spanish-first Costa Rica, CRC; configurable | P0 freeze |
| D04 | Product source and usage rights | No data supplied. Synthetic fixtures until source and permitted use confirmed | Real import |
| D05 | Inventory authority | No feed supplied. Local manual-authority mode is a proposed initial option; external feed mode needs its own source contract | Real availability/reservations |
| D06 | Freshness / reservation duration | Configurable thresholds per source and operation, set by business. Tests use explicit illustrative durations | P3 production use |
| D07 | Public availability | Availability bands by default; exact quantities staff-only unless owner chooses otherwise | Public availability launch |
| D08 | Sales units | Decimal quantities with SKU increments, explicit conversion rules | P1 schema freeze |
| D09 | Prices/tax/rounding | Authoritative managed price list; actual tax basis/rates, rounding and quote validity need business confirmation | Production quote issuance |
| D10 | Identity | Same-origin Django sessions with CSRF; customer auth for quotes, guest catalog browsing | P1 auth |
| D11 | Staff authority | Matrix in DOMAIN_CONTRACTS; discount overrides deferred; no cashier payment role | P1/P3 gates |
| D12 | Fulfillment | Complete order; one branch per order; explicit unpick for cancellation during picking | P3 |
| D13 | Runtime AI provider | Keep adapter. Candidate OpenAI Agents SDK per source prompt; choose pinned supported SDK/model at P4 and approve usage budget | Provider-backed P4 work |
| D14 | Search/queues | Postgres exact/full-text/trigram first; no embeddings/Redis/Celery until measured need | P2/P4 |
| D15 | Photos/privacy | Real catalog image selection in MVP; customer uploads/photo interpretation deferred pending consent, retention and secure processing | Optional P6 |
| D16 | Hosting/production | Provider, domain, backups, recovery targets and budget undecided; local Compose only | Production deployment |
| D17 | Scale/latency | Agree representative catalog size, peak requests, latency and AI cost budgets using measured fixtures | P5 release gate |
| D18 | Versions | Verify compatible current framework/runtime versions, pin exactly and record in ADR; no guessed “latest” | P1 installation |

Use ADRs under docs/architecture/decisions/ when decisions are resolved. Record context, choice, alternatives, consequences and validation. A ledger approval flag cannot substitute for the owner's authorization. Never log secrets or customer data as decision evidence.
