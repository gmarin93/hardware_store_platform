# Package validation

Prepared 2026-10-21, America/Costa_Rica.

## Observed

- Confirmed target: /Users/glenmarin/Documents/Development/hardware_store/hardware_store_platform.
- Before setup, the local directory contained only .git and had no commits.
- Installed CLI reports Claude Code 2.1.283.
- Claude Code agent and skill configuration shapes were checked against the official documentation.
- Application implementation, application tests, migrations, provider evaluations and deployment have not run.
- Claude has not been launched to execute these workflows; configuration validation is not an end-to-end agent behavior test.

## Authoritative configuration references

- [Anthropic: custom subagents](https://code.claude.com/docs/en/sub-agents): project agent location, YAML frontmatter, tool lists and inherited model.
- [Anthropic: skills](https://code.claude.com/docs/en/skills): project SKILL.md files, slash commands and argument substitution.

The files use simple name/description frontmatter for skills, and name/description/tools/model for agents. No experimental agent-team flag, custom hook, permission bypass or nested-agent dependency is needed. Normal skill discovery remains enabled; build authorization is checked against the direct user request.

## Static verification

The preparation session executed a Node.js validation using an existing YAML parser without installing dependencies. It verified 30 files, 8 agent definitions, 3 skill definitions, 24 tasks and 23 local Markdown links. YAML parsed successfully; agent names/tool allowlists and read-only reviewer restrictions passed; task owners/dependencies were valid and acyclic; all unexecuted tasks remained pending. Git showed only the newly created package files in the target repository.

An independent read-only architecture review examined the contracts and orchestration. Two findings were corrected: release/expiry must remain possible during source outages, and idempotency uniqueness must exclude the payload fingerprint so conflicting retries are rejected. The task acceptance criteria now cover both cases.

The Python skill-creator validator was not used because PyYAML was unavailable in the default Python environment. Equivalent frontmatter/name checks were executed with the already installed Node YAML parser. No packages were installed. These are static/configuration checks, not live Claude execution or application tests.

## First-session verification

Start a fresh Claude session in the project. Confirm it recognizes hardware-plan and the named specialists; run /hardware-plan 0. Check the transcript for actual delegation and reconcile the docs before a build. If definitions are not discovered, verify working directory and restart the session. Global/managed Claude settings may impose additional restrictions; this package does not override them.
