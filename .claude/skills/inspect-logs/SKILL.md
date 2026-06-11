---
description: Inspect SlapOS build and instance logs for errors and debugging
allowed-tools: Bash(*), Read, Grep, Glob
---

# Inspect SlapOS Logs

TRIGGER when: the user asks to check logs, debug a build failure, debug an instance deployment failure, or investigate why something is not working.

Show relevant SlapOS log output for debugging.

## Arguments

**$ARGUMENTS** — optional context: "software" (build logs), "instance" (deployment logs), a software name, or a keyword to grep for. If empty, show both software and instance log tails.

## Current environment

- env.local.json: !`cat .claude/env.local.json 2>/dev/null || echo "NOT FOUND"`

## Log file locations

Read the environment to determine the runner path. The standard log paths are:

- **Software build log**: `~/srv/runner/var/log/slapos-node-software.log`
- **Instance deployment log**: `~/srv/runner/var/log/slapos-node-instance.log`

## Execution

### If $ARGUMENTS contains "software" or "build"

Show the tail of the software build log, focusing on errors:

```bash
# Show last 100 lines
tail -n 100 ~/srv/runner/var/log/slapos-node-software.log

# Grep for errors
grep -i -n 'error\|traceback\|failed\|exception' ~/srv/runner/var/log/slapos-node-software.log | tail -30
```

### If $ARGUMENTS contains "instance" or "deploy"

Show the tail of the instance deployment log, focusing on errors:

```bash
# Show last 100 lines
tail -n 100 ~/srv/runner/var/log/slapos-node-instance.log

# Grep for errors
grep -i -n 'error\|traceback\|failed\|exception' ~/srv/runner/var/log/slapos-node-instance.log | tail -30
```

### If $ARGUMENTS contains a keyword

Search both logs for the keyword:

```bash
grep -i -n '$KEYWORD' ~/srv/runner/var/log/slapos-node-software.log | tail -20
grep -i -n '$KEYWORD' ~/srv/runner/var/log/slapos-node-instance.log | tail -20
```

### If $ARGUMENTS is empty

Show the tail of both logs with error highlighting:

```bash
echo "=== SOFTWARE BUILD LOG (last 50 lines) ==="
tail -n 50 ~/srv/runner/var/log/slapos-node-software.log

echo "=== INSTANCE DEPLOYMENT LOG (last 50 lines) ==="
tail -n 50 ~/srv/runner/var/log/slapos-node-instance.log
```

## Additional log sources

If the main logs are insufficient, check partition-specific logs:

- **Partition instance log**: `~/srv/runner/instance/slappartN/.slapgrid/log/instance.log`
- **Supervisord logs**: `~/srv/runner/instance/slappartN/var/log/`
- **Promise results**: `~/srv/runner/instance/slappartN/etc/plugin/`

List partitions first:
```bash
ls ~/srv/runner/instance/
```

## Interpreting common patterns

- `Traceback` followed by an exception → Python error in recipe or template rendering
- `While installing <section>` → buildout section that failed
- `Error: Picked: <package>` → missing version pin (see CLAUDE.md "Version pinning")
- `No module named` → missing egg or component
- `md5sum mismatch` → `buildout.hash.cfg` needs updating (run `update-hash`)
