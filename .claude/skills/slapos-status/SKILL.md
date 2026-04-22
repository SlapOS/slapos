---
description: Show SlapOS proxy status — software releases, partitions, and connection parameters
allowed-tools: Bash(*), Read
---

# SlapOS Status

TRIGGER when: the user asks about deployed instances, partition state, what's running, or wants to inspect the SlapOS proxy.

## Arguments

**$ARGUMENTS** — optional filter (software name, partition reference, or keyword). If omitted, show everything.

## Environment

The script supports two modes:
- **Default**: sources `~/bin/slapos-standalone-activate` (standard SlapOS standalone environment)
- **Testing**: pass `env.local.json` path to source `slapos-sr-testing-environment` instead

## Execution

Run the bundled status script:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/status.sh $ARGUMENTS
```

If a testing environment is needed (env.local.json exists), pass it as first arg:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/status.sh .claude/env.local.json $ARGUMENTS
```

The script will:
1. Source the SlapOS environment (standalone or testing)
2. Run `slapos proxy show`
3. Optionally filter output by the given keyword

## Interpreting output

The proxy show output has three tables:
- **computer**: registered computers and their IPs
- **software**: installed software releases (URL, state, md5 hash)
- **partition**: deployed instances (reference, software release, type, state, connection parameters)

Partition states: `busy` = allocated, `free` = available. Instance states: `started`, `stopped`, `destroyed`.
