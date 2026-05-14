# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository. Most
project conventions live in `AGENTS.md` (shared with Codex, OpenCode,
Gemini CLI, Aider, and other agents that follow the [agents.md](https://agents.md)
spec). This file adds Claude-Code-only shortcuts and notes.

@AGENTS.md

## Claude Code skill shortcuts

These skills under `.claude/skills/` wrap the workflows in `AGENTS.md` as
slash commands. They follow the [Agent Skills](https://agentskills.io)
(`SKILL.md`) format, so they also work in OpenCode, Codex, Gemini CLI,
and Goose — but the slash-command UX is Claude-Code-specific.

- Scaffolding: `/add-component`, `/add-template`, `/add-parameter`,
  `/add-frontend`, `/add-service`, `/add-promise`, `/add-logrotate`,
  `/add-monitoring`
- Build/deploy helpers: `/rebuild-software`, `/reprocess-instance`,
  `/slapos-status`
- Diagnostics + tests: `/run-sr-test`, `/inspect-logs`, `/test-results`,
  `/destroy-instance`

The `/rebuild-software`, `/reprocess-instance`, and `/slapos-status`
scripts source `~/bin/slapos-standalone-activate` automatically.

## Environment note specific to Claude Code

If the Bash tool hangs, set `export SHELL=/bin/bash` before launching
Claude Code (the default shell on this system is interactive-only and
blocks non-interactive use).
