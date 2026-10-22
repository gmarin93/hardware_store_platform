# Hardware Store Platform

Planning and Claude Code orchestration package for a hardware-store operations platform. **No payment gateway or payment processing.** No application has been implemented yet.

## Start with Claude Code

Open a fresh terminal session in this repository:

```sh
cd /Users/glenmarin/Documents/Development/hardware_store/hardware_store_platform
claude
```

At the Claude prompt, run:

```text
/hardware-plan 0
```

This checks the repository and finalizes the implementation decisions. When ready to build the foundation, run `/hardware-build 1`. Continue one phase at a time; `/hardware-review 1` can independently check progress. A phase command does not authorize subsequent phases or deployment. To authorize a range, state that range explicitly to Claude.

Or paste [the kickoff prompt](docs/prompts/START_HERE.md). The main session coordinates eight specialists: architect, Django, Next.js, catalog data, AI, QA, security and local runtime.

## Read the plan

- [Documentation index](docs/README.md)
- [Analysis of your original prompt](docs/planning/PROMPT_REVIEW.md)
- [Product scope](docs/PRODUCT_BRIEF.md)
- [Architecture and project structure](docs/architecture/ARCHITECTURE.md)
- [Phases and acceptance gates](docs/planning/DELIVERY_PLAN.md)
- [Orchestration and task ownership](docs/ORCHESTRATION.md)
- [Open decisions](docs/planning/DECISIONS.md)

The initial repository was empty apart from `.git`. The API paths and schema below are proposals until Phase 0 freezes them and implementation tests verify them. See [validation notes](docs/planning/VALIDATION.md) for what was actually checked.
