# Linear setup for hardware-store developers

Linear is the primary tracker for the hardware-store project. The project /hardware-ticket skill now routes to Linear; legacy Jira access remains explicitly namespaced under /hardware-jira:ticket.

## Project binding

Expected workspace slug: hardware-store. Team: Hardware Store (HAR), immutable team ID fbeb8b14-807c-4152-9794-c014afb4008b.
Delivery project: [Hardware Store Platform — Delivery](https://linear.app/hardware-store/project/hardware-store-platform-delivery-5c170417d4f8), immutable project ID fa87e75c-37e5-4cda-8945-2e286fa1cce0.
The versioned binding is [LINEAR_PROJECT.json](LINEAR_PROJECT.json). No immutable workspace ID was exposed in the verified connector response; that value remains null. Do not invent it.

Codex has fetched real HAR records including HAR-88. That authenticates neither your Claude session nor another developer's account.

## Choose one connection path

### A. Local plugin (recommended for this guide)

From the repository root:

```sh
claude --plugin-dir ./tools/claude-plugins/hardware-linear
```

Inside Claude, open /mcp, select the plugin's Linear server, complete browser OAuth and choose hardware-store. Then:

```text
/hardware-linear:ticket HAR-88 plan
```

The plugin supplies its ticket skill and a secret-free read-only HTTP MCP definition. It depends on this repository's docs and existing .claude/agents. It is not published, globally installed, authenticated by this package or a standalone platform generator.

### B. Project skill with your Claude connection

Reuse a working authorized Linear connection. If none exists, run the following yourself from this repository:

```sh
claude mcp add --transport http --scope local linear-server https://mcp.linear.app/mcp/readonly
claude
```

Authenticate with /mcp and select hardware-store. Then:

```text
/hardware-ticket HAR-88 plan
```

The project skill and plugin entry point share [LINEAR_TICKET_WORKFLOW.md](../workflows/LINEAR_TICKET_WORKFLOW.md). Choose one server path to avoid duplicate connections. Both commands require a real issue key, optionally followed by plan or implement. A bare invocation defaults to the eligible implementation scope.

## Why the default endpoint is read-only

Linear documents https://mcp.linear.app/mcp/readonly as an endpoint exposing only read tools. That is sufficient to read acceptance criteria and coordinate local coding.

The standard https://mcp.linear.app/mcp endpoint permits read/write according to authorization. If a separately requested action needs to post a comment or update a status, use an explicitly authorized write-capable connection and the exact requested action. This package does not enable it or automatically change remote records. A pre-existing write-capable server may be used for issue reads, but the workflow still forbids unsolicited writes.

## First authenticated verification

1. Confirm /hardware-ticket or /hardware-linear:ticket is recognized in a fresh session.
2. Confirm Linear shows connected in /mcp.
3. Fetch HAR-88 in plan mode.
4. Verify team/project and immutable issue identity against LINEAR_PROJECT.json.
5. Inspect requirements snapshot, SOURCE.json and PLAN.md.
6. Confirm that no application changes or Linear mutations occurred in plan mode.
7. Request implementation only within the intended ticket scope.

For HAR-88, implementation means design documentation/wireframes using frontend-design. It does not authorize building the later quotation/inventory APIs.

Local plugin/JSON/YAML validation is separate from this authenticated check. This update has not started a paid Claude conversation or authenticated Claude OAuth; a full Claude plan-mode run remains to be verified in the developer's session.

## Troubleshooting

- Missing tools: authenticate the actual Claude connection; do not assume Codex's connector is shared.
- Multiple workspaces/wrong team: select the intended account/context and inspect returned immutable IDs; do not guess from HAR alone.
- Read-only write failure: expected. Do not retry through another route without explicit action and connection authorization.
- Missing or moved issue: re-fetch by actual schema, preserve immutable identity/history and stop on project-binding mismatch.
- Pasted requirements only: use an unverified plan; never invent a successful live fetch.
- Existing Jira evidence: preserve it under its original path. New verified Linear evidence uses docs/tickets/linear/.

## Official references

- [Linear MCP server and read-only endpoint](https://linear.app/docs/mcp)
- [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp)
- [Claude plugin loading](https://code.claude.com/docs/en/plugins/create)
- [Claude skills](https://code.claude.com/docs/en/skills)
