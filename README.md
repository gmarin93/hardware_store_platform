# Hardware Store Platform

Hardware-store operations platform under phased development, with a local runtime foundation and Claude Code orchestration. **No payment gateway or payment processing.** Inspect current source, decisions and evidence for implementation status.

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

## Work from Linear

See [the developer guide](docs/DEVELOPER_GUIDE.md) and [PDF](docs/DEVELOPER_GUIDE.pdf). For the optional local plugin, start `claude --plugin-dir ./tools/claude-plugins/hardware-linear`, authenticate Linear through `/mcp`, then run `/hardware-linear:ticket HAR-88 plan`. The project command `/hardware-ticket HAR-88 plan` uses an existing authorized Claude Linear connection. Both share the same workflow; choose one connection path.

[Linear setup](docs/integrations/LINEAR_SETUP.md) explains read-only access, immutable issue binding and the separate Codex/Claude authentication. Plan first; request implementation for the eligible ticket scope. HAR-88 demonstrates the frontend-design skill.

## Read the plan

- [Documentation index](docs/README.md)
- [Analysis of your original prompt](docs/planning/PROMPT_REVIEW.md)
- [Product scope](docs/PRODUCT_BRIEF.md)
- [Architecture and project structure](docs/architecture/ARCHITECTURE.md)
- [Phases and acceptance gates](docs/planning/DELIVERY_PLAN.md)
- [Orchestration and task ownership](docs/ORCHESTRATION.md)
- [Open decisions](docs/planning/DECISIONS.md)

The initial repository was empty apart from `.git`. The API paths and schema below are proposals until Phase 0 freezes them and implementation tests verify them. See [validation notes](docs/planning/VALIDATION.md) for what was actually checked.
