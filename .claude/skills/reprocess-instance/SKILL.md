---
description: Reprocess SlapOS instances (kill existing process, run slapos node instance --force)
allowed-tools: Bash(*), Read
---

# Reprocess Instances

TRIGGER when: instance configuration files changed (.cfg.in templates, schemas) and instances need reprocessing, OR after a software rebuild that changed instance-time configs.

## Arguments

**$ARGUMENTS** — optional partition reference (e.g., `T-0`, `slappart3`). If omitted, process all instances.

## Current environment

- env.local.json: !`cat .claude/env.local.json 2>/dev/null || echo "NOT FOUND"`

## Execution

Run the bundled reprocess script:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/reprocess.sh .claude/env.local.json $ARGUMENTS
```

The script will:
1. Source the SlapOS environment
2. Kill any running `slapos node instance` process
3. Run `slapos node instance --force --only=<partition>` (or `slapos node instance --force` when no partition is given). `--only` does not imply `--force`, so both flags are required to force reprocessing of a specific partition.
4. Show the last 30 lines of output

## After reprocessing

Check for errors in the output. If a partition failed, suggest inspecting logs or running `/slapos-status` to see the current state.
