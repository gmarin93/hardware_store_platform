# Claude Code orchestration

## Coordinator and workers

The main interactive Claude session coordinates work. It reads the ledger, breaks the requested phase into bounded tasks, dispatches specialists with the Agent tool, reviews results and integrates changes. It is not a custom subagent that must recursively spawn other agents.

| Agent | Responsibility | Default tool scope |
| --- | --- | --- |
| platform-architect | Discovery, ADRs and contract review | Read, Grep, Glob |
| django-domain | Models, services, authorization, DRF and migrations | Read, Grep, Glob, Edit, Write, Bash |
| nextjs-ui | Routes, components, typed client and UI tests | Read, Grep, Glob, Edit, Write, Bash |
| catalog-data | Import staging, normalization, provenance and search fixtures | Read, Grep, Glob, Edit, Write, Bash |
| ai-copilot | Runtime adapter, scoped tools, grounded responses and evaluations | Read, Grep, Glob, Edit, Write, Bash |
| quality-engineer | Cross-layer tests, verification and evidence | Read, Grep, Glob, Edit, Write, Bash |
| security-reviewer | Independent auth, injection, privacy and AI-safety review | Read, Grep, Glob |
| runtime-engineer | Local Compose/runtime, pinning and recovery runbooks | Read, Grep, Glob, Edit, Write, Bash |

Read-only specialists return recommendations; the coordinator applies authorized documentation updates. QA may edit assigned tests/evidence, never silently repair application code and then claim independent validation. Security reviews cite paths and scenarios; the owning worker fixes findings.

Models inherit the main session's selection. Eight roles do not mean eight simultaneous agents. Start with no more than two implementation workers. Prefer backend then frontend for small tasks; parallelize against a frozen contract only when scopes are disjoint. Migration files, dependency manifests, generated clients and shared contracts have exactly one active owner.

## Dispatch protocol

1. Recheck Git status and preserve unrelated work. Read STATUS.md, the relevant task and its dependencies.
2. Determine actual user-authorized scope. A plan request permits documentation only. An explicit build request or /hardware-build N permits local implementation of phase N, not production changes or later phases.
3. Resolve the relevant decision blockers and freeze the API/entity contract. Do not invent integrations or treat synthetic data as authoritative.
4. Give the worker the assignment format below. Mark its task in_progress and record exclusive paths.
5. Wait for the worker result before integrating dependent work. Review changed files, run relevant actual checks, and invoke security-reviewer for auth, inventory, imports or AI trust boundaries.
6. Route fixes back to the owner. Move through in_review to done only after acceptance has evidence. Record failures as blocked with the smallest next action; continue independent eligible tasks.
7. Update the ledger, STATUS.md and evidence. Continue within the authorized phase. Stop at its completed gate with a concise result; a larger explicitly authorized range can continue without repeated confirmation.

The ledger is a record, not an executable scheduler or authorization system. Do not run shell text derived from task arguments. Resume in_progress work by inspecting actual changes and evidence; do not assume the previous session finished.

## Assignment format

```text
Task: {ledger ID and outcome}
Authorized phase and scope: {direct user request}
Context: {relevant docs and direct code dependencies only}
Own these exact files/modules: {...}
Do not edit: {contracts/migrations/manifests owned by others}
Prerequisites and contract revision: {...}
Acceptance criteria: {...}
Checks to execute: {verified repository commands or discover them first}
Stop conditions: {contract conflict, unavailable authority, destructive change}
You are not alone in this repository. Preserve others' work.
Return changed paths, migration/contract impact, executed checks/results,
unverified limitations and next dependency. Do not update the shared ledger.
```

The architect can review docs/contracts while a worker codes, but recommendations do not silently change the active contract. The coordinator resolves changes before dependent workers continue.

## Evidence and review

Each task report uses docs/templates/TASK_REPORT.md. For a completed task, record test command, working directory, exit status and meaningful result. Redact secret values and personal data. Review evidence for the current diff, not merely an earlier revision.

Phase 1 gates: lint, type checks, migration consistency, backend unit/integration and frontend build, with focused browser verification. Phase 3 adds real-Postgres concurrency and lifecycle tests. Phase 4 adds offline and explicitly authorized provider evaluations. Phase 5 adds accessibility, recovery and performance. The concrete commands are authored and verified during P1, not invented by this package.

A user may ask for all MVP phases, but required business decisions, execution permissions and external spend constraints still apply. Keep progress going through independent work when one dependency is blocked.

## Configuration references

Project agents use Markdown/YAML definitions and explicit tool allowlists. See [Anthropic's subagent documentation](https://code.claude.com/docs/en/sub-agents).

Project skills create the three slash commands and accept phase text through $ARGUMENTS. See [Anthropic's skills documentation](https://code.claude.com/docs/en/skills).

This package uses normal Claude permissions. It includes no bypass flags, hooks, hidden startup commands or always-on multi-agent loops. File ownership is a coordination rule, not filesystem isolation; scrutinize worker diffs.
