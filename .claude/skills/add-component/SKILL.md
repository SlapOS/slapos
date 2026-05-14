---
name: add-component
description: Add a Component to a Software Release
---

# Add a Component to a Software Release

TRIGGER when: the user asks to add a component, binary, or library to a SlapOS software release, OR you need to make an external tool (curl, tar, openssl, etc.) available to an instance.

Generate the buildout configuration to extend a component profile, forward the component location through the template chain, and use the binary in instance templates.

## Arguments

**$ARGUMENTS** — name of the component to add and which software release (e.g., "add curl to html5as", "add openssl to rapid-cdn"). If empty, ask the user which component and software release.

## Background — Component Architecture

SlapOS components are pre-built libraries and tools defined in `component/<name>/buildout.cfg`. Each component profile compiles the software and exposes its installation path via `${<name>:location}`. To use a component binary in an instance, the location must be threaded through three configuration levels:

1. **`software.cfg`** — extends the component profile, forwards `${<name>:location}` to instance templates
2. **`instance.cfg.in`** — receives the location and passes it to instance profiles
3. **`instance_<type>.cfg.in`** — uses the binary path (e.g., `{{ parameter_list['curl_location'] }}/bin/curl`)

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.A.Component

## Step-by-step procedure

### Step 1 — Find the component profile

Check if the component exists in the repository:

```
component/<name>/buildout.cfg
```

Common components: `curl`, `tar`, `openssl`, `bash`, `coreutils`, `git`, `nginx`, `python3`, `nodejs`, `mariadb`, `postgresql`, `haproxy`, `6tunnel`, etc.

Read the component profile to identify:
- The section name (usually matches the directory name)
- What `${<name>:location}` provides (bin/, lib/, include/ directories)

### Step 2 — Extend in `software.cfg`

Add the component profile to the `[buildout]` extends list:

```ini
[buildout]
extends =
  ...existing extends...
  ../../component/<name>/buildout.cfg
```

### Step 3 — Forward location via `[template-cfg]`

Add the component location to the `[template-cfg]` context in `software.cfg`:

```ini
[template-cfg]
context =
  ...existing context...
  key <name>_location <name>:location
```

Use `raw` instead of `key` if the location should be a literal string (rare):
```ini
  raw <name>_location ${<name>:location}
```

### Step 4 — Pass through `instance.cfg.in`

Add the location to `[profile-common]` (or the equivalent context section):

```ini
[profile-common]
...existing keys...
<name>_location = {{ <name>_location }}
```

### Step 5 — Use in the instance template

Reference the binary in the instance `.cfg.in` file:

```ini
[my-section]
<name>-binary = {{ parameter_list['<name>_location'] }}/bin/<binary>
```

Or directly in a command:
```ini
[my-command]
recipe = plone.recipe.command
command = {{ parameter_list['curl_location'] }}/bin/curl -Lks $URL | {{ parameter_list['tar_location'] }}/bin/tar xzv -C ${:location}
```

## Common component paths

| Component | Binary path |
|-----------|------------|
| curl | `bin/curl` |
| tar | `bin/tar`, `bin/gtar` |
| openssl | `bin/openssl` |
| bash | `bin/bash` |
| coreutils | `bin/*` (cat, cp, mv, etc.) |
| git | `bin/git` |
| nginx | `sbin/nginx` |
| haproxy | `sbin/haproxy` |

## After generating

1. Run `/rebuild-software` — adding a component requires a full software rebuild
2. Run `/reprocess-instance` to propagate the new binary paths
3. Verify the binary is accessible from the partition
