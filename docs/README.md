# Documentation index

Read only the documents needed for the assigned task.

| Document | Purpose |
| --- | --- |
| [Product brief](PRODUCT_BRIEF.md) | Scope, customers, roles, exclusions and success criteria |
| [Prompt review](planning/PROMPT_REVIEW.md) | Source analysis, verified empty-repository findings and gaps |
| [Architecture](architecture/ARCHITECTURE.md) | Boundaries, data ownership, routes and proposed layout |
| [Domain/API/AI contracts](architecture/DOMAIN_CONTRACTS.md) | Proposed states, permissions, invariants and contracts |
| [Delivery plan](planning/DELIVERY_PLAN.md) | Dependencies, phase gates and rollback |
| [Tasks](planning/tasks.json) | Coordinator-owned machine-readable task ledger |
| [Status](planning/STATUS.md) | Current progress and next action |
| [Decisions](planning/DECISIONS.md) | Assumptions and decisions needed before dependent work |
| [Risks](planning/RISKS.md) | Safety, security and operational risks |
| [Orchestration](ORCHESTRATION.md) | Agent routing, ownership, scheduling and review |
| [Kickoff prompt](prompts/START_HERE.md) | Paste-ready instructions for Claude |
| [Revised master prompt](prompts/MASTER_PROMPT.md) | Durable implementation mission |
| [Task report template](templates/TASK_REPORT.md) | Completion evidence format |
| [Validation](planning/VALIDATION.md) | Setup validation and authoritative Claude references |

The original attachment is retained as `docs/reference/original-master-prompt.txt` for traceability. It is reference material, not an instruction to execute or a source of extra authorization.

## Developer onboarding and Linear tickets

- [Developer guide](DEVELOPER_GUIDE.md) and [PDF version](DEVELOPER_GUIDE.pdf)
- [Linear setup](integrations/LINEAR_SETUP.md) and [project binding](integrations/LINEAR_PROJECT.json)
- [Shared Linear workflow](workflows/LINEAR_TICKET_WORKFLOW.md)
- [Linear result template](templates/LINEAR_TICKET_RESULT.md)
- [Local checks](development/CHECKS.md) and [P1-01 evidence](evidence/P1-01.md)

Legacy Jira: [setup](integrations/JIRA_SETUP.md), [workflow](workflows/JIRA_TICKET_WORKFLOW.md) and [result template](templates/JIRA_TICKET_RESULT.md). The primary /hardware-ticket command now reads Linear; legacy Jira uses /hardware-jira:ticket.
