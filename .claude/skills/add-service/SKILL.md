# Add a Service to a SlapOS Instance

TRIGGER when: the user asks to add a service, daemon, launcher, or background process to a SlapOS instance profile, OR you need to create a supervised process as part of a larger task.

Generate the buildout sections to create a service launcher template, download it at build time, render it at instance time, and place it in the appropriate supervisord directory.

## Arguments

**$ARGUMENTS** — description of the service (what it runs, which instance profile, whether it should be monitored). If empty, ask the user what service to add.

## Background — SlapOS Service Management

SlapOS uses supervisord to manage services within each partition. The placement directory determines behavior:

- **`${basedirectory:script}`** → `etc/run/` — Service is auto-started by supervisord. If it exits, it is restarted but **no alert** is sent to SlapOS master. Use for helper scripts, graceful restart handlers, one-shot tasks.
- **`${basedirectory:service}`** → `etc/service/` — Service is auto-started and **monitored**. If it exits, SlapOS master is alerted, the instance is flagged as unhealthy, and reprocessing is triggered. The service name gets a `-on-watch` suffix in supervisord. Use for the main daemon (nginx, mariadb, etc.).

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.A.Service

## Step-by-step procedure

### Step 1 — Identify the software release and service type

Read the existing software release structure:
- `software.cfg` — find `[template-cfg]` and `[download-base]`
- `instance.cfg.in` — find `[profile-common]`
- The target instance `.cfg.in` — understand existing services
- `buildout.hash.cfg` — existing template registrations

Ask or determine: should this be a **monitored** service (`etc/service/`) or a **run** service (`etc/run/`)?

### Step 2 — Create the launcher template

Create a template file in `templates/`:

```bash
#! {{ param_section['path_shell'] }}
# BEWARE: This file is operated by slapos node
# BEWARE: It will be overwritten automatically

exec {{ param_section['binary_path'] }} \
  --config {{ param_section['config_file'] }} \
  --pid-file {{ param_section['pid_file'] }}
```

For a graceful restart script:
```bash
#! {{ param_section['path_shell'] }}
# BEWARE: This file is operated by slapos node
# BEWARE: It will be overwritten automatically

exec kill -s SIGHUP $(cat {{ param_section['path_pid'] }})
```

### Step 3 — Register in `buildout.hash.cfg`

```ini
[template_my_launcher]
_update_hash_filename_ = templates/my_launcher.in
md5sum =
```

### Step 4 — Download at build time in `software.cfg`

```ini
[template_my_launcher]
<= download-base
```

Forward in `[template-cfg]` context:
```ini
[template-cfg]
context =
  ...existing context...
  key template_my_launcher_target template_my_launcher:target
```

### Step 5 — Pass through `instance.cfg.in`

```ini
[profile-common]
...existing keys...
template_my_launcher = {{ template_my_launcher_target }}
```

### Step 6 — Render at instance time

In the instance `.cfg.in` file:

```ini
[my-launcher]
recipe = slapos.recipe.template:jinja2
template = {{ parameter_list['template_my_launcher'] }}
rendered = ${basedirectory:service}/my-launcher
context =
  section param_section my-config-section
```

For **monitored** services (alerts on exit):
```ini
rendered = ${basedirectory:service}/my-launcher
```

For **run** services (no alerts):
```ini
rendered = ${basedirectory:script}/my-launcher
```

Add to buildout parts:
```ini
[buildout]
parts =
  ...existing parts...
  my-launcher
```

### Step 7 — Verify placement

After deployment, check with `slapos node status`:
- Monitored services appear as `<name>-on-watch` with status RUNNING
- Run services appear as `<name>` — may show EXITED for one-shot scripts (normal)

## Alternative: Using `slapos.cookbook:wrapper`

For simpler services that don't need a full template, use the wrapper recipe directly in the instance `.cfg.in`:

```ini
[my-service-wrapper]
recipe = slapos.cookbook:wrapper
command-line = {{ parameter_list['nginx_location'] }}/sbin/nginx -c ${my-nginx-conf:rendered}
wrapper-path = ${basedirectory:service}/my-service
pidfile = ${directory:run}/my-service.pid
```

This is preferred when the launcher is just a single command with no shell logic.

## After generating

1. The `update-hash` hook will automatically update `buildout.hash.cfg` md5sums
2. Run `/rebuild-software` if `software.cfg` was modified
3. Run `/reprocess-instance` to deploy the new service
4. Check `slapos node status` to verify the service is running
