---
name: add-monitoring
description: Add the Monitoring Stack to a Software Release
---

# Add the Monitoring Stack to a Software Release

TRIGGER when: the user asks to add monitoring, promises infrastructure, or logrotate to a SlapOS software release, OR when the instance profile needs `monitor-promise-base`, `logrotate-entry-base`, or `monitor-publish` which are provided by the monitoring stack.

Generate the buildout configuration changes across software.cfg, instance.cfg.in, and instance templates to integrate the monitoring stack.

## Arguments

**$ARGUMENTS** — which software release to add monitoring to. If empty, ask the user.

## Background — SlapOS Monitoring Stack

The monitoring stack (`stack/monitor/buildout.cfg`) provides:
- **Promise infrastructure** — `monitor-promise-base` section for health checks
- **Logrotate** — `logrotate-entry-base` section for log rotation
- **Monitor web service** — dedicated HTTP service for remote monitoring
- **`monitor-publish`** — publishes monitoring connection parameters (`monitor-setup-url`)

This is a prerequisite for `/add-promise`, `/add-logrotate`, and `/add-frontend` (which uses promises).

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.Monitoring.Stack

## Step-by-step procedure

### Step 1 — Read the current software release

Read these files to understand the current state:
- `software.cfg` — check if `stack/monitor/buildout.cfg` is already extended
- `instance.cfg.in` — find `[template-cfg]` forwarding and `[profile-common]`
- The target instance `.cfg.in` — check existing extends and parts

If the monitoring stack is already extended, skip to the deployment step.

### Step 2 — Extend the monitor stack in `software.cfg`

Add to the `[buildout]` extends list:

```ini
[buildout]
extends =
  ...existing extends...
  ../../stack/monitor/buildout.cfg
```

### Step 3 — Forward the monitor template in `software.cfg`

Add `monitor2-template:output` to the `[template-cfg]` context:

```ini
[template-cfg]
context =
  ...existing context...
  key template_monitor monitor2-template:output
```

The `monitor2-template` section is provided by the monitor stack and outputs the compiled monitor template.

### Step 4 — Pass through `instance.cfg.in`

Add to `[profile-common]` (or equivalent):

```ini
[profile-common]
...existing keys...
template_monitor = {{ template_monitor }}
```

### Step 5 — Extend in the instance template

In the instance `.cfg.in` file, add the monitor template to the buildout extends:

```ini
[buildout]
...
extends = {{ parameter_list['template_monitor'] }}
```

This makes `logrotate-entry-base`, `monitor-promise-base`, and monitor web service sections available.

### Step 6 — Add monitor instance parameter

Add a section to configure the monitor HTTP port:

```ini
[monitor-instance-parameter]
monitor-httpd-port = {{ parameter_dict['monitor-httpd-port'] }}
```

And add the default port to `default-parameters` in `instance.cfg.in`:

```ini
default-parameters =
  {
    ...existing defaults...
    "monitor-httpd-port": 8197
  }
```

### Step 7 — Extend `monitor-publish` in publish section

Modify the publish section to inherit monitor connection parameters and switch to the serialised recipe:

```ini
[publish-connection-information]
recipe = slapos.cookbook:publish.serialised
<= monitor-publish
...existing publications...
```

The `<= monitor-publish` adds `monitor-setup-url` and other monitoring parameters to the published connection information automatically. The `publish.serialised` recipe is needed for the monitoring stack's serialised parameter handling.

Also update `[slap-configuration]` in `instance.cfg.in` to use the serialised variant if not already:

```ini
[slap-configuration]
recipe = slapos.cookbook:slapconfiguration.serialised
computer = ${slap-connection:computer-id}
partition = ${slap-connection:partition-id}
url = ${slap-connection:server-url}
key = ${slap-connection:key-file}
cert = ${slap-connection:cert-file}
```

## What the monitoring stack provides

After integration, these sections become available in instance templates:

| Section | Purpose |
|---------|---------|
| `monitor-promise-base` | Base for promise plugins (`<= monitor-promise-base`) |
| `logrotate-entry-base` | Base for logrotate entries (`<= logrotate-entry-base`) |
| `monitor-publish` | Publishes monitoring URLs |
| `monitor-instance-parameter` | Monitor HTTP port configuration |

## After generating

1. Run `/rebuild-software` — extending a new stack requires a software rebuild
2. Verify `template-monitor.cfg` exists in `srv/runner/software/<hash>/`
3. Run `/reprocess-instance` to deploy the monitoring web service
4. Check `slapos node status` for monitor-related processes
5. Access the monitor URL from published connection parameters
