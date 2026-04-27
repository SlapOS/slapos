# Add a SlapOS Promise

TRIGGER when: the user asks to add, create, or implement a promise/monitor check in a SlapOS instance profile, OR you need to add a promise as part of a larger task.

Generate the buildout sections for a new SlapOS promise in an instance profile.

## Arguments

**$ARGUMENTS** — description of the promise to add (what to check, which instance profile, etc.). If empty, ask the user what the promise should check.

## Background — What is a Promise?

A Promise is a Python script generated during instantiation in `instance_home/etc/plugin/`. Slapgrid executes promises to determine instance health. Each promise inherits from `GenericPromise` and implements up to three methods:

- **`sense()`** — collects monitoring data (required)
- **`test()`** — returns Green/Red based on sense results
- **`anomaly()`** — detects sustained failures (e.g., last 3 senses bad)

Reference: https://handbook.rapid.space/rapidspace-DesignDocument.Understanding.Slapos.Promises

## Promise Patterns (choose the right one)

### Pattern A: Built-in promise plugin (no custom Python)

Use for common checks. Add to the instance `.cfg.in` file:

```ini
[my-promise-name]
<= monitor-promise-base
promise = <plugin_name>
name = my-promise-name.py
config-<key> = <value>
```

Available built-in plugins:
- `check_socket_listening` — TCP port open (`config-host`, `config-port`)
- `check_url_available` — URL responds (`config-url`)
- `check_file_state` — file exists/has content (`config-filename`, `config-state`)
- `check_command_execute` — run a shell command, check exit code (`config-command`). Use ONLY for simple shell commands, NOT for Python logic.

### Pattern B: Custom promise from slapos.toolbox

Use when a reusable promise plugin exists in `slapos.toolbox`:

```ini
[my-promise]
recipe = slapos.cookbook:promise.plugin
eggs = slapos.toolbox
output = ${directory:plugins}/my_promise.py
module = check_site_state
config-site-url = ${publish:site-url}
config-connection-timeout = 20
```

### Pattern C: SR-specific custom promise with testable code in a Python module

Use when custom Python logic is needed and should be unit-testable. The core logic lives in a Python module built as part of the software release; the promise plugin is a thin wrapper that imports and calls it.

Many software releases (e.g., rapid-cdn) ship a `software.py` + `setup.py` that get develop-installed during `slapos node software`. If the SR already has this setup, skip to Step 2. If not, create the module infrastructure first:

**Step 1 — Create the Python module** (skip if SR already has `software.py` + `setup.py`):

Create `software.py` in the SR directory with a no-op Recipe class (needed as a buildout entry point) and your check function:
```python
import os
import sys

class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass
  def install(self):
    return []
  def update(self):
    return self.install()

def my_check_function(param1, param2=300):
  """Returns (status, message) where status is 'ok', 'warning', or 'error'."""
  if not os.path.exists(param1):
    return ('error', 'File does not exist: %s' % param1)
  # ... check logic ...
  return ('ok', 'Check passed')
```

Create `setup.py` in the SR directory:
```python
from setuptools import setup
setup(
  name='software',
  install_requires=[],  # add dependencies as needed
  entry_points={
    'zc.buildout': ['default = software:Recipe'],
  }
)
```

Add build sections to `software.cfg` to download, prepare, and develop-install the module:
```ini
[software-setup]
recipe = slapos.recipe.build:download
url = ${:_profile_base_location_}/setup.py

[software-py]
recipe = slapos.recipe.build:download
url = ${:_profile_base_location_}/software.py

[software-prepare]
recipe = plone.recipe.command
command =
  rm -fr ${buildout:parts-directory}/${:_buildout_section_name_} &&
  mkdir -p ${buildout:parts-directory}/${:_buildout_section_name_} &&
  cp ${software-setup:target} ${buildout:parts-directory}/${:_buildout_section_name_}/ &&
  cp ${software-py:target} ${buildout:parts-directory}/${:_buildout_section_name_}/

[software-develop]
recipe = zc.recipe.egg:develop
setup = ${software-prepare:location}

[software-install]
recipe = zc.recipe.egg
eggs = software
```

**Step 2 — Add the promise sense template** in the instance `.cfg.in`:
```ini
[my-promise-sense]
recipe = slapos.recipe.template
output = ${directory:bin}/${:_buildout_section_name_}
inline =
  import software
  from zope.interface import implementer
  from slapos.grid.promise import interface
  from slapos.grid.promise.generic import GenericPromise

  @implementer(interface.IPromise)
  class RunPromise(GenericPromise):
    def sense(self):
      status, message = software.my_check_function(
        '${section:param1}')
      if status == 'error':
        self.logger.error(message)
      elif status == 'warning':
        self.logger.warning(message)
      else:
        self.logger.info(message)
```

**Step 3 — Wire with `slapos.cookbook:promise.plugin`**:
```ini
[my-promise]
recipe = slapos.cookbook:promise.plugin
eggs =
  slapos.core
  software
file = ${my-promise-sense:output}
output = ${directory:plugins}/my_promise.py
```

The `software` in `eggs` makes the develop-installed module importable by the promise at runtime.

**Step 4 — Add unit tests** for the check function (no SlapOS dependencies needed):
```python
import unittest
import tempfile
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import software

class TestMyCheckFunction(unittest.TestCase):
  def test_missing_file(self):
    status, msg = software.my_check_function('/nonexistent')
    self.assertEqual(status, 'error')
  # ...
```

### Pattern D: Fully inline custom promise

Use for simple custom checks that don't warrant a separate module or unit tests:

```ini
[my-promise-sense]
recipe = slapos.recipe.template
output = ${directory:bin}/${:_buildout_section_name_}
inline =
  import os
  from zope.interface import implementer
  from slapos.grid.promise import interface
  from slapos.grid.promise.generic import GenericPromise

  @implementer(interface.IPromise)
  class RunPromise(GenericPromise):
    def sense(self):
      # ... custom logic using buildout-substituted variables ...
      if error_condition:
        self.logger.error("Something is wrong")
      else:
        self.logger.info("All good")

[my-promise]
recipe = slapos.cookbook:promise.plugin
eggs = slapos.core
file = ${my-promise-sense:output}
output = ${directory:plugins}/my_promise.py
```

## GenericPromise API

Key methods available in promise classes:
- `self.getConfig(key, default=None)` — get config values passed via `config-<key>`
- `self.logger.info/warning/error(msg)` — log promise results
- `self.setPeriodicity(minute=N)` — set check frequency (call in `__init__`)
- `self.setTestLess()` — run only for anomaly, not during deployment
- `self.setAnomalyLess()` — run only during deployment, no anomaly checking
- `self.getLastPromiseResultList(result_count=N, only_failure=False)` — read past results
- `self._anomaly(result_count=3, failure_amount=3)` — standard anomaly check

## Important rules

- **NEVER use `check_command_execute` for Python logic** — it spawns a new Python process per check. Use `slapos.cookbook:promise.plugin` instead (shared process per partition).
- Plugin filenames in `output` use **underscores** (e.g., `my_promise.py`), section names use **hyphens**.
- Add the promise section to buildout `parts` or `part_list` (Jinja2 profiles use `{% do part_list.append('my-promise') %}`).
- After adding sections, update `buildout.hash.cfg` md5sums.
- Template variables (`${section:key}`) are substituted at buildout time. Jinja2 variables (`{{ var }}`) at rendering time.

## After generating

Verify the promise works:
1. `slapos node software --only=<hash>` (if software.py or setup.py changed)
2. `slapos node instance --only=<partition>`
3. Check promise output: `slapos node promise` or look in `etc/plugin/`
