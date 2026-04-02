---
description: Rebuild a SlapOS software release (kill existing process, remove .completed, run slapos node software)
allowed-tools: Bash(*), Read
---

# Rebuild Software Release

TRIGGER when: code changes require rebuilding a software release (software.cfg, setup.py, software.py, templates, buildout.hash.cfg, component changes), OR after the user edits files that affect the software build.

## Arguments

**$ARGUMENTS** — optional software release name or path fragment (e.g., `rapid-cdn`, `html5as`). If omitted, auto-detect from the current working directory.

## Current environment

- env.local.json: !`cat .claude/env.local.json 2>/dev/null || echo "NOT FOUND"`

## Execution

Run the bundled rebuild script:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/rebuild.sh .claude/env.local.json $ARGUMENTS
```

The script will:
1. Source the SlapOS environment
2. List available software releases from the proxy
3. Match the requested SR (or auto-detect from cwd)
4. Kill any running `slapos node software` process
5. Remove the `.completed` marker
6. Run `slapos node software --only=<hash>`
7. Report success or failure

## After rebuild

If the rebuild succeeded and instance config files also changed, suggest running `/reprocess-instance` next.
