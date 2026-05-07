---
name: show-instances
description: Show deployed SlapOS instances for a software release and their connection parameters
disable-model-invocation: true
argument-hint: "<software-name>"
allowed-tools: Bash, Read, Glob
---

# Show Instances

Show deployed instances for: $ARGUMENTS

Parse `$ARGUMENTS` as `<software-name>` — the directory name under `software/` (e.g. `erp5-mcp-hateoas`).

## Step 1: Identify the software release

The software release path is:
```
~/srv/project/erp5-mcp/software/<software-name>/software.cfg
```

Read `software/<software-name>/software.cfg.json` to get the software release name and serialisation mode.
Read `software/<software-name>/instance-input-schema.json` to know the available instance parameters.

## Step 2: List instances

Run:
```bash
~/bin/theia-shell -c "export PATH=/opt/slapgrid/cfaa2217e0f9ea9ef9e05b634f6dbecb/bin:\$PATH && export SLAPOS_CONFIGURATION=\$HOME/srv/runner/etc/slapos.cfg && export SLAPOS_CLIENT_CONFIGURATION=\$SLAPOS_CONFIGURATION && slapos proxy show" 2>&1
```

From the output, find all partitions whose `software_release` matches the software release path. For each matching partition, extract:
- **Partition reference** (e.g. `slappart0`)
- **Instance name** (partition_reference column, e.g. `erp5mcp`)
- **State** (requested_state)
- **Connection parameters** (listed below the table as `slappartN: instance-name`)

## Step 3: Display summary

For each instance, display a clear summary:

```
## <instance-name> (slappartN) — <state>

Connection parameters:
  param1 = value1
  param2 = value2
  ...

Request parameters (from instance-input-schema.json):
  <list the schema's properties with types, defaults, and which are required>
```

If no instances are found, say so and show the available parameters from the schema so the user knows what to pass to `/deploy-instance`.

## Step 4: Offer next steps

- If instances exist, offer to show more details or deploy another instance
- Mention `/deploy-instance <software-name> <instance-name> param=value ...` for deploying a new one
- If ports are in use, suggest the next available port
