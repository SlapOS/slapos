# Add an Instance Parameter (slapparameter)

TRIGGER when: the user asks to add a configurable parameter to a SlapOS instance, OR you need to make a value user-configurable via `slapos request --parameters`.

Generate the buildout configuration to define a default value, merge with user-supplied parameters, and use it in instance templates.

## Arguments

**$ARGUMENTS** — name and description of the parameter to add, which software release, default value, and whether to publish it. If empty, ask the user what parameter to add.

## Background — SlapOS Parameters

Instance parameters (slapparameters) are user-supplied values passed via `slapos request --parameters key=value`. They flow through the system as:

1. User passes parameters via SlapOS request
2. `slap-configuration:configuration` provides them as a dict
3. Instance templates merge defaults with user values
4. The merged dict is used in Jinja2 templates

Reference: https://handbook.rapid.space/user/rapidspace-HowTo.Add.A.Parameter

## Step-by-step procedure

### Step 1 — Identify the parameter setup

Read the instance profile chain:
- `instance.cfg.in` — find the section that renders the target instance template. Look for `default-parameters` and `slapparameter_dict` in the context.
- The target instance `.cfg.in` — find how `parameter_dict` is constructed.
- `instance.cfg.in` — check if `[slap-configuration]` uses `slapos.cookbook:slapconfiguration` (plain) or `slapos.cookbook:slapconfiguration.serialised` (serialised). The serialised variant is needed when parameters are JSON-encoded.

### Step 2 — Add default value in `instance.cfg.in`

Find the section that renders the target instance template (e.g., `[instance-html5as]`). Add or update the `default-parameters` JSON:

```ini
[instance-html5as]
recipe = slapos.recipe.template:jinja2
...
context =
  ...existing context...
  key slapparameter_dict slap-configuration:configuration
  jsonkey default_parameter_dict :default-parameters
default-parameters =
  {
    ...existing defaults...
    "my-new-param": "default_value"
  }
```

Key elements:
- `jsonkey default_parameter_dict :default-parameters` parses the JSON into a dict
- `key slapparameter_dict slap-configuration:configuration` provides user-supplied params

If the instance does not yet have parameter support, you also need to:
1. Add `key slapparameter_dict slap-configuration:configuration` to the context
2. Add `jsonkey default_parameter_dict :default-parameters` to the context
3. Switch `[slap-configuration]` from `slapos.cookbook:slapconfiguration` to `slapos.cookbook:slapconfiguration.serialised` and add `key` and `cert` fields:

```ini
[slap-configuration]
recipe = slapos.cookbook:slapconfiguration.serialised
computer = ${slap-connection:computer-id}
partition = ${slap-connection:partition-id}
url = ${slap-connection:server-url}
key = ${slap-connection:key-file}
cert = ${slap-connection:cert-file}
```

### Step 3 — Merge defaults with user parameters

In the instance `.cfg.in` file, ensure the parameter merge exists (usually already present):

```jinja2
{% set parameter_dict = dict(default_parameter_dict, **slapparameter_dict) %}
```

This creates `parameter_dict` where user-supplied values override defaults.

### Step 4 — Use the parameter

Reference the parameter in the instance template:

```ini
[my-section]
my-setting = {{ parameter_dict['my-new-param'] }}
```

With a conditional:
```jinja2
{% if parameter_dict.get('my-new-param') %}
[my-optional-section]
setting = {{ parameter_dict['my-new-param'] }}
{% endif %}
```

### Step 5 — Optionally publish the parameter

To make the parameter visible in connection information:

```ini
[publish-connection-information]
...existing publications...
my-new-param = {{ parameter_dict['my-new-param'] }}
```

If the software release uses serialised parameters, also switch the publish recipe from `slapos.cookbook:publish` to `slapos.cookbook:publish.serialised`.

### Step 6 — Update `instance-input-schema.json` (if it exists)

If the software release has a JSON Schema for input validation, add the parameter:

```json
{
  "properties": {
    "my-new-param": {
      "type": "string",
      "title": "My New Parameter",
      "description": "Description of what this parameter controls",
      "default": "default_value"
    }
  }
}
```

## Parameter serialisation modes

Check `software.cfg.json` for the `serialisation` field:

- **`json-in-xml`**: Parameters are wrapped under a `_` key as a JSON string. The `jsonkey` context directive handles this automatically.
- **No serialisation / direct**: Parameters are flat key-value pairs from `slap-configuration:configuration`.

## After generating

1. Run `/reprocess-instance` to apply the new parameter with its default value
2. Test with explicit parameter: `slapos request <name> <uri> --parameters my-new-param=custom_value`
3. Verify the parameter appears where expected (config file, published connection info, etc.)
