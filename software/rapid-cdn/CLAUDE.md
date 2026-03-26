# rapid-cdn development notes

## Running tests

Always run from the `test/` subdirectory, otherwise Python resolves `test` as the stdlib module:

```bash
cd software/rapid-cdn/test
python_for_test -m unittest test.TestErrorPageManager
# or for the full suite:
python_for_test -m unittest test
```

After changing any profile/schema/template file, update hashes first:

```bash
cd software/rapid-cdn
python_for_test ../../update-hash
```

## Instance profile patterns

### Connection parameters (publish.serialised)

`slapos.cookbook:publish.serialised` wraps everything under a `_` key. In tests:

```python
# writing
return {'_': json.dumps({'key': 'value'})}

# reading
conn = json.loads(cls.requestDefaultInstance().getConnectionParameterDict()['_'])
```

### monitor.bootstrap

`[directory]` must include `scripts = ${:etc}/run`. The monitor template places `bootstrap-monitor` there; if shadowed with a different path, supervisor never runs it.

### slapos.recipe.build init phase

`init =` runs before `install =` and before `mkdirectory` has created dirs. Always use `os.makedirs(..., exist_ok=True)` inside `init`.

### _buildout_safe_dumps

`dumps()` in Jinja2 outer templates escapes `$` → `\x24`. Never pass values containing `${section:key}` through `dumps()`. Instead build Python literals by string concatenation and let buildout expand the variables itself:

```jinja2
{%- do pairs.append('("' + ref + '", "${directory:tokens}/' + ref + '")') %}
  raw my_list [{{ pairs | join(', ') }}]
```

### Buildout paths and double slashes

Buildout directory sections often have trailing slashes (e.g. `srv = ${buildout:directory}/srv/`), which produces double-slash paths in children (`/path/srv//error-pages`). In generated Python scripts, always normalize at load time:

```python
MY_DIR = os.path.normpath('{{ my_dir }}')
```

And use a separator-terminated prefix for path traversal checks:

```python
if not full.startswith(MY_DIR + os.sep + 'subdir' + os.sep):
```

### extra-context for wrapper templates

Jinja2 wrapper sections using `:command` need:

```ini
extra-context =
  key content :command
```

### bin/python interpreter

To make `bin/python` available in the software's bin dir, add to `[software-install]`:

```ini
interpreter = python
```

## Error Page Manager (EPM) feature — design summary

### What was built

The Error Page Manager is a dedicated SlapOS partition (`software-type = error-page-manager`) that serves a small HTTPS server (Python, self-signed cert) allowing:

- The **operator** to upload custom HTML for any of the seven supported error codes (400, 404, 408, 500, 502, 503, 504) via a REST API and a browser UI.
- Each **slave/site owner** to override the backend-related codes (502, 503, 504) for their own site only.

HAProxy on each frontend node reads `.http` errorfiles from disk. The EPM writes these files; a poller (`error-page-updater`) on each frontend polls the EPM every ~60 s and reloads HAProxy when files change.

### Directory layout under the EPM partition

```
srv/error-pages/
  operator/          # operator-uploaded HTML bodies (one file per code)
  slaves/            # slave-uploaded HTML bodies (one dir per slave ref)
  haproxy/
    default/         # operator errorfiles rendered as HTTP/1.0 responses
    slaves/{ref}/    # per-slave errorfiles (502/503/504 only)
```

### Override precedence

1. Slave override (if set) — affects that slave's 502/503/504 only
2. Operator custom page (if set)
3. Built-in default (shipped in `templates/error-pages/*.http`)

### Key files

| File | Purpose |
|---|---|
| `instance-error-page-manager.cfg.in` | EPM partition profile |
| `templates/error-page-manager.py.in` | HTTPS management server |
| `templates/error-page-updater.py.in` | Frontend poller/reloader |
| `templates/error-pages/*.http` | Built-in default error pages |
| `instance-error-page-manager-{input,output}-schema.json` | Parameter schemas |
| `doc/error-pages-operator.rst` | Operator user guide |
| `doc/error-pages-slave.rst` | Slave/site-owner user guide |

### Bugs fixed during development

1. **New slave init copied from builtins, not from `haproxy/cluster/`** (`instance-error-page-manager.cfg.in` `[error-pages-init]`): new slaves got built-in defaults even when the operator had already set overrides. Fixed by sourcing from `haproxy_default` instead of `builtin_dir`.

2. **`error-page-updater` did not reload backend HAProxy** after updating slave errorfiles (`instance-slave-list.cfg.in` `on_update`): only the frontend graceful command was called. Fixed by appending `&& {{ backend_haproxy_configuration['graceful-command'] }}`.

### Test data placeholders

The EPM partition gets its own IPv6 address. Add it to the `@@_ipv6_address@@` replacement list in `TestDataMixin.getDataReplacementDict` and look it up with:

```python
error_page_manager_partition = cls.getPartitionId('error-page-manager')
cls.error_page_manager_ipv6 = cls.getPartitionIPv6(error_page_manager_partition)
```

Token and certificate values are replaced by dedicated `@@..._epm-upload-token@@` and `@@error-page-certificate@@` placeholders.

### Updating test data

Test data files are committed snapshots. When EPM connection parameters change:

```bash
cd software/rapid-cdn/test
SAVE_TEST_DATA=1 python_for_test -m unittest test   # first run: saves + fails
python_for_test -m unittest test                     # second run: must pass
```
