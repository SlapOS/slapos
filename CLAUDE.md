# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository. Most
project conventions live in `AGENTS.md` (shared with Codex, OpenCode,
Gemini CLI, Aider, and other agents that follow the [agents.md](https://agents.md)
spec). This file adds Claude-Code-only notes.

@AGENTS.md

## Skills and coding rules ship as plugins

The SlapOS development skills and the coding-rules knowledge base are no longer
vendored in this repo — they live in a single standalone, agent-agnostic
[Agent Skills](https://agentskills.io) repository,
[`slapos-agent-skills`](https://lab.nexedi.com/cedric.leninivin/slapos-agent-skills),
packaged as a Claude Code plugin marketplace with four plugins:

- `slapos-scaffolding` — `/add-component`, `/add-template`, `/add-parameter`,
  `/add-service`, `/add-promise`, `/add-logrotate`, `/add-monitoring`,
  `/add-frontend`.
- `slapos-build-deploy` — `/rebuild-software`, `/reprocess-instance`,
  `/deploy-instance`, `/destroy-instance`, `/show-instances`,
  `/export-request-scripts`.
- `slapos-diagnostics` — `/slapos-status`, `/inspect-logs`, `/test-results`,
  `/run-sr-test`.
- `slapos-coding-rules` — the harvested coding-rules tables plus a hook that
  checks staged commits against them.

This repo ships `.claude/settings.json` pre-registering the marketplace, so
Claude Code offers to install the plugins when you open the checkout. To install
manually:

```
/plugin marketplace add https://lab.nexedi.com/cedric.leninivin/slapos-agent-skills.git
/plugin install slapos-scaffolding@slapos-agent-skills
/plugin install slapos-build-deploy@slapos-agent-skills
/plugin install slapos-diagnostics@slapos-agent-skills
/plugin install slapos-coding-rules@slapos-agent-skills
```

Several build/deploy/diagnostics skills read machine-specific paths from
`.claude/env.local.json` (not committed). Copy the `env.local.json.example`
template from the slapos-agent-skills plugin into `.claude/env.local.json` and
fill it in. For other agents (Codex, Gemini CLI, OpenCode, Goose), see the
plugin repo's `README.md` for the manual install path.

## Environment note specific to Claude Code

If the Bash tool hangs, set `export SHELL=/bin/bash` before launching
Claude Code (the default shell on this system is interactive-only and
blocks non-interactive use).
