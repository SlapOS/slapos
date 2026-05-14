---
name: add-template
description: Add a Jinja2 Template to a Software Release
---

# Add a Jinja2 Template to a Software Release

TRIGGER when: the user asks to add a template file to a SlapOS software release, OR you need to create a new template as part of a larger task (e.g., adding a config file, an HTML page, a script that needs Jinja2 variables at instance time).

Generate the buildout sections across multiple files to properly download a template at build time and render it at instance time.

## Arguments

**$ARGUMENTS** — description of the template to add (template purpose, which software release, target instance profile). If empty, ask the user what template to add and where.

## Background — Two-Level Template Rendering

SlapOS uses a two-level rendering pattern:

1. **Build time** (`slapos node software`): Templates are **downloaded** from the source tree into the software release directory using `slapos.recipe.build:download`. They are NOT rendered at this stage — they contain `{{ }}` Jinja2 variables that are only available at instance time.
2. **Instance time** (`slapos node instance`): Templates are **rendered** with `slapos.recipe.template:jinja2`, which substitutes instance-specific variables (IP addresses, ports, paths, user parameters).

**Critical rule:** Instance-time templates must be downloaded at build time (via `slapos.recipe.build:download`), NOT rendered with `slapos.recipe.template:jinja2` — they contain `{{ }}` variables only available at instance time.

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.A.Template.To.Software.Release

## Step-by-step procedure

### Step 1 — Identify the software release

Locate the software release directory under `software/<name>/`. Read the existing files to understand the structure:
- `software.cfg` — find the `[template-cfg]` section and `[download-base]` macro
- `instance.cfg.in` — find the `[profile-common]` section
- `buildout.hash.cfg` — understand existing template registrations
- The target instance `.cfg.in` file where the template will be rendered

### Step 2 — Create the template file

Create the template file (typically in `templates/` subdirectory). Use Jinja2 syntax for instance-time variables:

```
{# Example: templates/my_config.conf.in #}
{% if some_param %}
setting = {{ some_param }}
{% endif %}
server_address = {{ partition_ipv6 }}:{{ port }}
```

### Step 3 — Register in `buildout.hash.cfg`

Add a section matching the section name you will use in `software.cfg`:

```ini
[template_my_config]
_update_hash_filename_ = templates/my_config.conf.in
md5sum =
```

The md5sum will be filled automatically by the `update-hash` hook.

### Step 4 — Download at build time in `software.cfg`

Add a download section using the `download-base` macro:

```ini
[template_my_config]
<= download-base
```

Then forward the template path to instance profiles by adding to the `[template-cfg]` context:

```ini
[template-cfg]
context =
  ...existing context...
  key template_my_config_target template_my_config:target
```

### Step 5 — Forward through `instance.cfg.in`

Pass the template path into the instance profile's `[profile-common]` section (or equivalent context section):

```ini
[profile-common]
...existing keys...
template_my_config = {{ template_my_config_target }}
```

### Step 6 — Render at instance time in the instance `.cfg.in`

Add a section in the target instance template to render the template with instance-time variables:

```ini
[my-config]
recipe = slapos.recipe.template:jinja2
template = {{ parameter_list['template_my_config'] }}
rendered = ${directory:etc}/my_config.conf
context =
  key some_param :some_param
  section html5as html5as
some_param = {{ parameter_dict['some_param'] }}
```

Add the section name to buildout parts:

```ini
[buildout]
parts =
  ...existing parts...
  my-config
```

Or in Jinja2-driven profiles:
```jinja2
{% do part_list.append('my-config') %}
```

## Naming conventions

- **Section names** in `software.cfg` and `buildout.hash.cfg` use **underscores**: `template_my_config`
- **Template filenames** use underscores or hyphens: `templates/my_config.conf.in`
- The `_update_hash_filename_` value is the relative path from the software directory
- The forwarding key pattern is `template_<name>_target` → `template_<name>:target`

## After generating

1. The `update-hash` hook will automatically update `buildout.hash.cfg` md5sums when you edit files under `software/*/`
2. Run `/rebuild-software` if `software.cfg` was modified
3. Run `/reprocess-instance` to render the new template
4. Verify the rendered file exists in the partition directory (e.g., `srv/runner/instance/slappartN/etc/`)
