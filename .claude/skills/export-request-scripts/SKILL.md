---
name: export-request-scripts
description: Export request scripts for all deployed top-level SlapOS instances from the proxy database
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Glob, Grep
---

# Export Request Scripts

Generate request scripts for all top-level SlapOS instances currently deployed in the local proxy.

## Step 1: Query the proxy database

Run:
```bash
sqlite3 ~/srv/runner/var/proxy.db "SELECT reference, partition_reference, software_release, software_type, xml FROM partition17 WHERE requested_by = '' AND slap_state = 'busy'"
```

This returns only top-level instances (`requested_by = ''` excludes child instances spawned by other partitions).

For each row, extract:
- `reference` — partition ID (e.g. `slappart0`)
- `partition_reference` — instance name (e.g. `erp5mcp`)
- `software_release` — software URL
- `software_type` — type (e.g. `default`)
- `xml` — serialised request parameters

## Step 2: Parse instance parameters from XML

The `xml` column uses one of two patterns:

**json-in-xml**: A single `<parameter id="_">...</parameter>` containing a JSON string:
```xml
<parameter id="_">{"key": "value"}</parameter>
```
→ Use `partition_parameter_kw={"_": json_parameter}` where `json_parameter` is the raw JSON string (pretty-printed).

**Direct XML**: Multiple `<parameter id="key">value</parameter>` elements:
```xml
<parameter id="user-authorized-key">ssh-ed25519 AAAA...</parameter>
```
→ Use `partition_parameter_kw={"key": "value", ...}`.

## Step 3: Check for existing scripts

Search all `~/srv/project/*.py` files for each instance's `partition_reference`. For each instance, run:
```bash
grep -l '<partition_reference>' ~/srv/project/*.py 2>/dev/null
```

Look specifically for the instance name appearing in a `request(` call context. If any `.py` file already contains that instance name, **skip** that instance and note which file handles it.

## Step 4: Generate request scripts

For each top-level instance not already covered by an existing script, generate `~/srv/project/<partition_reference>-request.py`.

### For json-in-xml instances (parameter `_` contains JSON):

```python
#!/usr/bin/env python
import json
import os

software_url = os.path.expanduser("<software_release with ~ replacing home dir>")

parameter_dict = {
  <key-value pairs from the parsed JSON>
}

print("Supplying %s" % software_url)
supply(software_url, "slaprunner")
print("Supplied %s" % software_url)

print("requesting instance")
instance = request(
  software_url,
  "<partition_reference>",
  partition_parameter_kw={"_": json.dumps(parameter_dict)},
)
print("instance requested")
params = instance.getConnectionParameterDict()
if "_" in params:
  print(json.dumps(json.loads(params["_"]), indent=2))
else:
  print(json.dumps(params, indent=2))
```

### For direct XML instances:

```python
#!/usr/bin/env python
import json
import os

software_url = os.path.expanduser("<software_release with ~ replacing home dir>")

print("Supplying %s" % software_url)
supply(software_url, "slaprunner")
print("Supplied %s" % software_url)

print("requesting instance")
instance = request(
  software_url,
  "<partition_reference>",
  partition_parameter_kw={"key1": "value1", "key2": "value2"},
)
print("instance requested")
print(json.dumps(instance.getConnectionParameterDict(), indent=2))
```

### Rules:

- Only include `software_type="<type>"` if it is **not** `"default"`
- Replace the home directory prefix (e.g. `/srv/slapgrid/slappart76`) with `~` in the `software_url`, using `os.path.expanduser("~/...")`
- If the software URL is an external URL (starts with `http`), use it as-is without `os.path.expanduser`
- Only include `import os` if `os.path.expanduser` is actually used
- For json-in-xml parameters, define a Python `parameter_dict` dict literal and use `json.dumps(parameter_dict)` in the `partition_parameter_kw` — never use raw JSON strings
- Use native Python types in `parameter_dict`: integers for numbers (not strings), nested dicts/lists as-is

## Step 5: Show summary

Print a summary listing:
- **Generated scripts**: path and corresponding instance name
- **Skipped instances**: instance name and the existing file that already handles it

For each generated script, show the full command to run it:
```
~/bin/theia-shell -c "slapos console ~/srv/project/<partition_reference>-request.py"
```
