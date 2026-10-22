# Risk register

These are design risks for a new system, not vulnerabilities found in an existing app.

| Risk | Priority | Control / acceptance evidence | Owner |
| --- | --- | --- | --- |
| Overselling or double stock consumption | Critical | Postgres concurrent-worker tests, stable locks, constraints, idempotent transitions | django-domain |
| Freshness timestamp falsely refreshed | Critical | Preserve source_observed_at; stale/failed authority becomes UNKNOWN | django-domain |
| Fabricated product/price/stock in AI prose | Critical | Evidence-scoped IDs, hydrated cards, deterministic factual wording, negative evaluations | ai-copilot |
| Unsafe electrical/gas/pressure advice | Critical | Domain policy, missing-fact checks, human-reviewed adversarial evaluation | ai-copilot + security-reviewer |
| Cross-organization, branch or customer data access | Critical | Direct API/tool tests and field-level redaction | django-domain + security-reviewer |
| Prompt injection changes tools or permissions | Critical | Separate data/instructions, scoped tools, deny unauthorized effects | ai-copilot |
| Reservation expiry races with picking | High | One locking/transition boundary; expiry-versus-picking tests | django-domain |
| Invalid unit conversions or money rounding | High | Explicit increments/conversions, decimal rules and boundary tests | django-domain |
| Import overwrites truth or merges distinct variants | High | Staging, review and authoritative publication services; idempotent import | catalog-data |
| Upload/URL attack, SSRF, malicious documents | High | Allowlisted import sources, restricted network, file validation; no arbitrary AI fetching | catalog-data + security-reviewer |
| Unauthorized rights or outdated scraped data | High | Provenance and permitted-use assessment before publication | catalog-data + owner |
| Lost migration or overlapping agent edits | High | Exclusive ownership, serialized migrations/contracts, coordinator integration | Coordinator |
| Private information in logs/provider traces | High | Minimal context, redaction, retention and access controls | ai-copilot + runtime-engineer |
| Backup exists but cannot restore | High | Restore rehearsal and reconciled stock audit | runtime-engineer + quality-engineer |
| Full scope consumes excessive budget | Medium | Phase-scoped tasks; two implementation workers; measured AI budgets | Coordinator |
| Agent rules treated as a sandbox | High | Tool allowlists, standard permission system and independent review; no bypass flags | Coordinator |

Critical findings block the affected release. Track actual findings with file/evidence, exploit or failure scenario, owner and resolution; do not mark hypothetical risks “fixed” without evidence.
