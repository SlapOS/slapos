---
description: Rebuild a SlapOS software release (kill existing process, run slapos node software --force)
allowed-tools: Bash(*), Read
---

# Rebuild Software Release

TRIGGER when: code changes require rebuilding a software release (software.cfg, setup.py, software.py, templates, buildout.hash.cfg, component changes), OR after the user edits files that affect the software build.

## Arguments

**$ARGUMENTS** — optional software release name or path fragment (e.g., `rapid-cdn`, `html5as`). If omitted, auto-detect from the current working directory.

## Environment

The script supports two modes:
- **Default**: sources `~/bin/slapos-standalone-activate` (standard SlapOS standalone environment)
- **Testing**: pass `env.local.json` path to source `slapos-sr-testing-environment` instead

## Execution

Run the bundled rebuild script:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/rebuild.sh $ARGUMENTS
```

If a testing environment is needed (env.local.json exists), pass it as first arg:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/rebuild.sh .claude/env.local.json $ARGUMENTS
```

The script will:
1. Source the SlapOS environment (standalone or testing)
2. List available software releases from the proxy
3. Match the requested SR (or auto-detect from cwd)
4. Kill any running `slapos node software` process
5. Run `slapos node software --force --only=<hash>` (the `--force` flag ignores the extends-cache; removing `.completed` alone is not equivalent)
6. Report success or failure

## After rebuild

If the rebuild succeeded and instance config files also changed, suggest running `/reprocess-instance` next.
