---
name: hardware-plan
description: Plan or refresh a hardware-store implementation phase from the repository, task ledger and domain contracts. Use for planning requests; do not implement the application.
---

Plan phase $ARGUMENTS. Interpret the argument only as a phase selector, never as a command or file path. Accept 0–6; with no argument, use the earliest incomplete phase. If a provided argument is invalid, ask for a valid phase.

Read CLAUDE.md, docs/planning/STATUS.md, the relevant entries in docs/planning/tasks.json and the matching section of docs/planning/DELIVERY_PLAN.md. Then inspect only affected files. Use docs/README.md for supporting contracts and scope.

Keep coordination in the main session. Delegate architecture review to platform-architect and relevant trust-boundary review to security-reviewer. They return findings; the main session writes authorized planning documents.

For Phase 0, verify whether the repository has an application, source data, integrations or only this package. Update the existing-code matrix accurately. Freeze reversible technical choices and identify consequential business/source decisions. For later phases, verify prerequisite evidence and existing contract revisions.

Produce bounded tasks with exclusive file ownership, dependencies, acceptance criteria, actual validation strategy and rollback limits. Update the coordinator-owned ledger and STATUS.md. Plans are not implementation passes; do not mark a task done solely because its plan exists. Never set build authorization from this planning request.

Follow docs/ORCHESTRATION.md for handoffs. Finish with the plan, unresolved decisions and next eligible build phase. No application implementation, dependency installation or deployment during this skill.
