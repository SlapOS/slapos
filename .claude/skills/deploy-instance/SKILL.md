---
name: deploy-instance
description: Deploy a new SlapOS instance from a software release in this repository
disable-model-invocation: true
argument-hint: "<software-name> <instance-name> [param=value ...]"
allowed-tools: Bash, Read, Glob, Grep, Write
---

# Deploy a SlapOS Instance

Deploy a new instance: $ARGUMENTS

Parse $ARGUMENTS as: `<software-name> <instance-name> [param=value ...]`
- `software-name`: directory name under `software/` (e.g. `erp5-mcp-hateoas`)
- `instance-name`: SlapOS partition reference name (e.g. `my-instance`)
- Remaining args: instance parameters as `key=value` pairs

## Step 1: Inspect the software release

Given `<software-name>`, locate:
- `software/<software-name>/software.cfg` — the software release profile
- `software/<software-name>/software.cfg.json` — read the `serialisation` field to determine parameter wrapping
- `software/<software-name>/instance-input-schema.json` — read to understand available parameters, types, defaults, and required fields

Print a summary:
- Serialisation mode (`json-in-xml` means parameters are wrapped under `_` key)
- Required parameters and their types
- Default values

If any required parameters are missing from the user's `param=value` args, ask before proceeding.

## Step 2: Check existing instances

Run:
```bash
source ~/bin/slapos-standalone-activate 2>/dev/null && slapos proxy show 2>&1
```

Show existing instances using the same software release. Warn if ports or names would conflict. Identify which ports are already in use so the new instance uses a different one.

## Step 3: Ask about frontend

Ask the user if a frontend (shared apache-frontend instance) is needed for this deployment. If yes, ask for:
- The frontend name (e.g. `My-Frontend.20250311`)
- Which connection parameter contains the backend URL (e.g. `family-default-v6`, `url`, `mcp-url`)

Skip this step if the software clearly does not need a frontend (e.g. CLI tools, background workers).

## Step 4: Generate the request script

Generate a Python request script at `~/srv/project/<instance-name>-request.py`.

The software release path is:
```
~/srv/project/erp5-mcp/software/<software-name>/software.cfg
```

### Script structure

```python
#!/usr/bin/env python
import json
import os

software_url = os.path.expanduser("~/srv/project/erp5-mcp/software/<software-name>/software.cfg")
```

#### For `json-in-xml` serialisation:
```python
parameter_dict = {
  "param1": "value1",
  "param2": 42,
}

print("Supplying %s" % software_url)
supply(software_url, "slaprunner")
print("Supplied %s" % software_url)

print("requesting instance")
instance = request(
  software_url,
  "<instance-name>",
  partition_parameter_kw={"_": json.dumps(parameter_dict)},
)
print("instance requested")
params = instance.getConnectionParameterDict()
if "_" in params:
  print(json.dumps(json.loads(params["_"]), indent=2))
else:
  print(json.dumps(params, indent=2))
```

#### For `xml` serialisation or no serialisation:
```python
print("Supplying %s" % software_url)
supply(software_url, "slaprunner")
print("Supplied %s" % software_url)

print("requesting instance")
instance = request(
  software_url,
  "<instance-name>",
  partition_parameter_kw={"param1": "value1", "param2": "value2"}
)
print("instance requested")
params = instance.getConnectionParameterDict()
print(json.dumps(params, indent=2))
```

Use integer types for integer parameters (no quotes around numbers in JSON).

#### If frontend was requested (from Step 3), append:
```python
backend_url = params.get("<backend-url-key>", "")
print("<backend-url-key>: %s" % backend_url)
if backend_url:
  frontend_software_url = "http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg"
  print("requesting frontend with url: " + backend_url)
  frontend = request(
    frontend_software_url,
    "<frontend-name>",
    partition_parameter_kw={"type": "zope", "url": backend_url, "https-only": True},
    shared=True,
  )
  frontend_params = frontend.getConnectionParameterDict()
  if "secure_access" in frontend_params:
    print("Frontend URL: %s" % frontend_params["secure_access"])
  else:
    print("Frontend not ready yet")
else:
  print("No backend URL found, no frontend requested")
```

Write the script using the Write tool to `~/srv/project/<instance-name>-request.py`.

## Step 5: Execute the request script

Run the script via `slapos console`:
```bash
source ~/bin/slapos-standalone-activate 2>/dev/null && slapos console ~/srv/project/<instance-name>-request.py 2>&1
```

This registers the request in the SlapOS proxy database. The cron-spawned `slapos node instance` will deploy it on its next run.

If the connection parameters are empty (instance not yet deployed), inform the user:
- The instance request has been registered
- `slapos node instance` runs periodically via cron and will deploy it automatically
- To trigger deployment immediately: `source ~/bin/slapos-standalone-activate 2>/dev/null && slapos node instance`
- The request script can be re-run anytime to check updated connection parameters

## Step 6: Verify deployment

Run these checks:

1. **Supervisor status**: check that the new process is RUNNING:
   ```bash
   source ~/bin/slapos-standalone-activate 2>/dev/null && slapos node supervisorctl status 2>&1 | grep <software-name-pattern>
   ```

2. **Connection parameters**: re-run the request script to retrieve published connection parameters:
   ```bash
   source ~/bin/slapos-standalone-activate 2>/dev/null && slapos console ~/srv/project/<instance-name>-request.py 2>&1
   ```

3. **Endpoint test**: if the connection parameters include a URL, curl it to verify it responds:
   ```bash
   curl -sk <url> 2>&1
   ```

Print a summary of:
- Script location (`~/srv/project/<instance-name>-request.py`)
- Partition reference (slappartN)
- All connection parameters
- Endpoint test result
