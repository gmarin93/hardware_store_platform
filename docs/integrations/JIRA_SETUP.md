# Legacy Jira setup for Claude Code

Linear is now the primary tracker and /hardware-ticket reads HAR issues. Use [Linear setup](LINEAR_SETUP.md) for the normal workflow.

This guide preserves the intentionally selected legacy Jira plugin. Do not use /hardware-ticket HW-123; that entry point now validates Linear HAR keys.

## Load the legacy plugin

From this repository:

```sh
claude --plugin-dir ./tools/claude-plugins/hardware-jira
```

Open /mcp, select its Atlassian server and complete browser OAuth for the intended Jira site. Then:

```text
/hardware-jira:ticket HW-123 plan
```

HW-123 is illustrative. The plugin still reads [the separate Jira workflow](../workflows/JIRA_TICKET_WORKFLOW.md) and uses [the Jira result template](../templates/JIRA_TICKET_RESULT.md). It supplies a server definition, not an authenticated account or standalone project agents.

Choose the actual site when ambiguous. Keep prior Jira snapshots and source binding. Never mix a Jira key's evidence with Linear data or claim a Codex connection authenticates Claude.

## Scope

The legacy workflow permits requested reads and bounded local implementation, with plan mode for analysis only. It does not automatically comment, edit issues, transition status or reassign. It has not been live-tested through an authenticated Claude run by this documentation update.

## References

- [Atlassian setup](https://support.atlassian.com/atlassian-ai-gateway/docs/get-started-with-the-atlassian-remote-mcp-server/)
- [Primary Linear setup](LINEAR_SETUP.md)
