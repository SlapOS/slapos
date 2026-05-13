---
description: "VERY DANGEROUS — irreversibly destroys a SlapOS instance. Runs slapos request --state destroyed, then loops slapos node report until the partition is gone. Always requires explicit user confirmation; never run autonomously."
argument-hint: "<partition-reference>"
allowed-tools: Bash(*), Read
---

# Destroy a SlapOS Instance

> ⚠️ **VERY DANGEROUS — IRREVERSIBLE.** This skill permanently deletes a
> partition's filesystem (databases, logs, generated configs, buildout
> artifacts). There is no undo. Only run it when the user has explicitly asked
> to destroy a *specific* instance by reference.

## When NOT to trigger

- The user said "clean up", "reset", "redeploy", "fix", or "remove the
  error" — these are not destruction requests. Ask what they mean first.
- The user did not name a specific partition reference. Never infer one;
  ask.
- You are running in auto/loop mode without a human in the loop.

## When to trigger

The user explicitly says e.g. "destroy <ref>", "tear down <ref>", "delete
partition <ref>", "slapos request --state destroyed <ref>".

## Arguments

**$ARGUMENTS** — required. The SlapOS partition reference (the
`partition_reference` column in `partition17`, e.g. `my-instance`, `erp5mcp`).
**Not** the slot id (`slappart3`, `T-0`) — use the logical name.

The script refuses to run with no argument, or with suspicious values like
`*`, `all`, or an empty string.

## Why a simple `slapos request --state destroyed` is not enough

`slapos request --state destroyed` only **marks** the partition for
destruction in the proxy database. Actual tear-down happens in the
`slapos node report` pass, and is multi-step:

1. First `report` stops running processes and marks the instance as
   `stopped`.
2. `slapos.core/slapos/grid/slapgrid.py:1969-1973` skips destruction on any
   pass where processes are still `RUNNING`/`STARTING`, so a second `report`
   is needed once processes have actually exited.
3. A final `slapos node instance` (or `report`) pass sweeps up the now
   software-less partition directory (`slapgrid.py:1420`).

This skill wraps the whole sequence and polls until the partition is gone.

## Environment

The script supports two modes:
- **Default**: sources `~/bin/slapos-standalone-activate` (standard SlapOS
  standalone environment).
- **Testing**: pass `env.local.json` path to source
  `slapos-sr-testing-environment` instead.

## Execution

Run the bundled destroy script. **Before running, confirm with the user that
the reference is correct** — the script will also prompt, but do not suppress
or auto-answer that prompt.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/destroy.sh $ARGUMENTS
```

If a testing environment is needed (env.local.json exists), pass it as first
arg:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/destroy.sh .claude/env.local.json $ARGUMENTS
```

The script will:
1. Source the SlapOS environment (standalone or testing).
2. Look up the software URL for the partition reference from
   `$SLAPOS_BASE/var/proxy.db` (table `partition17`).
3. Print the matching row and prompt `Type 'yes' to continue:` on stdin.
   Anything other than `yes` aborts before any destructive action.
4. Kill any running `slapos node software|instance|report` process so the
   destroy loop has exclusive access.
5. Run `slapos request <ref> <software_url> --state destroyed`.
6. Loop up to **5** passes of `slapos node report`, then (once `report`
   settles) a final `slapos node instance --force --only=<slot>` to clean
   the free partition. Polls the proxy DB after each pass; exits as soon as
   the partition's `slap_state` is no longer `busy`.
7. Prints a summary, or a `WARN` if the partition is still present after
   the cap (e.g. a stuck service preventing tear-down).

## After destruction

- Run `/slapos-status` to visually confirm the partition is gone or marked
  free.
- If the instance was created via `/deploy-instance`, the per-instance
  request script at `~/srv/project/<reference>-request.py` is **not**
  removed by this skill — tell the user so they can decide whether to
  delete it.
- If the `WARN` path triggered, suggest `slapos node supervisorctl status`
  to find the hung service, then re-run the skill.
