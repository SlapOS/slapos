# Add Logrotate for a Service

TRIGGER when: the user asks to add log rotation for a SlapOS service, OR you need to manage log file growth for a service that writes logs.

Generate the buildout section to add a logrotate entry for a service's log files.

## Arguments

**$ARGUMENTS** — service name, log file paths, and post-rotation command. If empty, ask the user which service's logs to rotate.

## Background — SlapOS Logrotate

The logrotate stack is included with the monitoring stack (`stack/monitor/buildout.cfg`). It provides a `logrotate-entry-base` section that handles rotation scheduling, compression, and retention. Each service that writes log files should have its own logrotate entry.

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.Logrototate

**Prerequisite:** The monitoring stack must be extended in the software release (see `/add-monitoring`). The `logrotate-entry-base` section comes from `stack/logrotate/instance-logrotate-base.cfg.in`.

## Step-by-step procedure

### Step 1 — Identify log files and the service

Read the instance `.cfg.in` to find:
- The section that defines the service (e.g., `[my-service]`)
- The log file paths (e.g., `${my-service:path_access_log}`, `${my-service:path_error_log}`)
- The PID file path if a post-rotation signal is needed (e.g., `${my-service:path_pid}`)

### Step 2 — Add the logrotate entry section

In the instance `.cfg.in` file, add:

```ini
[logrotate-entry-my-service]
<= logrotate-entry-base
name = my-service
log = ${my-service:path_access_log} ${my-service:path_error_log}
post = kill -USR1 $(cat ${my-service:path_pid})
```

Key properties:
- `<= logrotate-entry-base` — inherits rotation settings from the logrotate stack
- `name` — unique name for this logrotate entry (appears in `etc/logrotate.d/`)
- `log` — space-separated list of log file paths to rotate
- `post` — command to run after rotation (typically send signal to reopen logs)

### Step 3 — Add to buildout parts

```ini
[buildout]
parts =
  ...existing parts...
  logrotate-entry-my-service
```

Or in Jinja2-driven profiles:
```jinja2
{% do part_list.append('logrotate-entry-my-service') %}
```

## Common post-rotation signals

| Service | Signal | Command |
|---------|--------|---------|
| nginx | USR1 | `kill -USR1 $(cat ${nginx:path_pid})` |
| Apache | GRACEFUL | `kill -USR1 $(cat ${apache:path_pid})` |
| HAProxy | USR1 | `kill -USR1 $(cat ${haproxy:path_pid})` |
| No signal needed | — | omit the `post` key |

## Optional logrotate-entry-base overrides

These can be set in the logrotate entry section (see `stack/logrotate/instance-logrotate-base.cfg.in`):

```ini
[logrotate-entry-my-service]
<= logrotate-entry-base
name = my-service
log = ${my-service:log_path}
frequency = daily
rotate-num = 30
nocompress = true
create = true
```

## After generating

1. Run `/reprocess-instance` to create the logrotate configuration
2. Verify: `ls <partition>/etc/logrotate.d/` — the entry name should appear
3. Test rotation: the logrotate cron runs automatically, or force with logrotate binary
