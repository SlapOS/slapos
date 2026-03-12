# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**slapos.cookbook** is a Python package providing 90+ [zc.buildout](https://www.buildout.org/) recipes for the [SlapOS](https://slapos.nexedi.com/) distributed cloud operating system. Each recipe is a buildout plugin that configures and deploys a specific software component within a SlapOS partition.

## Local Environment

Machine-specific paths are stored in `.claude/env.local.json` (not committed). Copy `.claude/env.local.json.example` and fill in paths for your environment. Keys:

- `cookbook-repository`: path to the slapos.cookbook checkout used for running unit tests
- `slapos-egg-testing-environment`: path to `slapos-local-development-environment.sh` for egg unit tests
- `slapos-sr-testing-environment`: path to `slapos-local-development-environment.sh` for software release integration tests
- `python-binary`: path to the Python binary with slapos.cookbook installed
- `public-dir`: path to the frontend-static public directory for publishing eggs

## Running Tests

Tests must be run from the **cookbook-repository** path (see `env.local.json`):

```bash
cd <cookbook-repository>
source <slapos-egg-testing-environment>
python -m unittest slapos.test.recipe.test_<module_name>
```

Run a single test class:
```bash
python -m unittest slapos.test.recipe.test_slaposconfiguration.JsonSchemaReportErrorTest
```

Run all recipe tests:
```bash
python -m unittest discover -s slapos/test/recipe -p 'test_*.py'
```

Run the full test suite (alternative):
```bash
python setup.py test --test-suite slapos.test.test_recipe.additional_tests
```

## Running rapid-cdn Integration Tests

rapid-cdn has full SlapOS instance deployment tests in `software/rapid-cdn/test/test.py`. Use the **`/run-sr-test`** command to run them:

```
/run-sr-test rapid-cdn test.TestClassName.test_method_name
/run-sr-test rapid-cdn test.TestClassName --save-data --debug
```

Flags: `--save-data` (regenerate expected output), `--debug` (keep instances alive on failure).

Key constraints:
- Tests **cannot run in parallel** — they share a SlapOS proxy on port 21584
- Before launching, check for active runners: `ps aux | grep '[p]ython_for_test.*unittest'`
- Slave test classes take ~4-15 min; master-only classes take ~4 min

## Running Software Release Deployment Tests (slapos-sr-testing)

Software releases can have integration tests in `software/<name>/test/` using the `slapos.testing` framework. These deploy actual SlapOS instances and test them.

### Environment setup and running

```bash
source <slapos-sr-testing-environment>
cd software/<name>/test/
python_for_test -m unittest discover -v
```
- `SLAPOS_TEST_DEBUG=1` — invoke debugger on error

### Test structure (reference: `software/html5as/test/`)

Each test directory contains:
- **`test.py`** — test module using `makeModuleSetUpAndTestCaseClass` from `slapos.testing.testcase`
- **`setup.py`** — package metadata (`name = 'slapos.test.<software-name>'`)
- **`README.md`** — one-line description

### Key patterns

- `setUpModule` builds/installs the software; `setUpClass` deploys an instance
- Connection parameters: use `self.computer_partition.getConnectionParameterDict()`
- Some software releases wrap params in JSON under `_` key (e.g. html5as: `json.loads(params['_'])`), others publish flat keys directly (e.g. erp5-mcp-hateoas: `params['mcp-url']`)
- Instance parameters are passed via `getInstanceParameterDict()` class method — same wrapping convention applies
- Tests take several minutes (software install + instance deploy); first run is slowest
- Tests **cannot run in parallel** — they share a SlapOS proxy

## Commit Messages

- Do **not** mention Claude, Anthropic, or any AI tool in commit messages or trailers (no `Co-Authored-By: Claude` lines).
- Commits should reflect the work itself, not the tools used to produce it.
- Format: `<module-or-area>: <description starting with lowercase verb>`
- Examples: `instancenode: skip error() for...`, `rapid-cdn: add access to...`


## Code Style

- **2-space indentation** throughout (vim modeline `sts=2` is standard)
- Python 2/3 compatibility via `six` is present in older files; new code should target Python 3 but be compatible with python2
- **Comments must be stateless**: describe what the code *is* or *does*, never what changed. Avoid phrases like "new API", "now uses X", "changed to Y", "previously Z". A comment should read correctly regardless of when it was written.

## Git Push Safety

- **NEVER** run `git push` without explicitly specifying both the remote and the branch (e.g., `git push perso my-branch`).
- The upstream (read-only) remote has a URL starting with `https://lab.nexedi.com/nexedi/`. **NEVER** push to it.
- All other remotes whose URL starts with `https://lab.nexedi.com/cedric.leninivin/` are personal forks where pushing is allowed.
- Before pushing, always verify the remote URL with `git remote get-url <remote>`.
- If the user asks to push, confirm the target remote and branch before executing.
- **NEVER** use commands that reset a branch to another ref (e.g., `git checkout -B <branch> <ref>`, `git branch -f <branch> <ref>`, `git reset --hard <ref>`) — these silently overwrite the branch's upstream tracking config. To update a branch with latest upstream, use `git rebase <upstream-remote>/master` which preserves the existing tracking.

## Architecture

### Recipe Structure

Recipes live in `slapos/recipe/` in two forms:
- **Directory-based**: `slapos/recipe/<name>/__init__.py` (may include templates in `template/`)
- **File-based**: `slapos/recipe/<name>.py`

All recipes are registered as `zc.buildout` entry points in `setup.py`. A recipe class must implement `install()` (and optionally `update()`) methods conforming to the buildout recipe interface.

### Base Classes (`slapos/recipe/librecipe/`)

- **`GenericBaseRecipe`** (`generic.py`) — Primary base class for new recipes. Provides `createExecutable()`, `substituteTemplate()`, `createFile()`, etc.
- **`GenericSlapRecipe`** (`genericslap.py`) — Extends GenericBaseRecipe with SlapOS master connectivity (partition parameters, request/publish).
- **`BaseSlapRecipe`** (`__init__.py`) — Legacy base class (deprecated). Sets up standard partition directory structure (bin, etc, srv, var, tmp, etc/run, etc/promise).
- **`wrap()`/`unwrap()`** (`__init__.py`) — JSON serialization utilities for SlapOS master communication.

### Key Recipe Modules

- **`slapconfiguration.py`** — Retrieves partition parameters from SlapOS master. Variants: plain, serialised, jsonschema (with JSON Schema validation), instancenode.deferred (reads from local DB instead of master).
- **`instancenode.py`** — Manages child instance requests on behalf of a root instance. Processes instance lists, handles SLA filtering, maintains a local SQLite database.
- **`cdninstancenode.py`** — CDN-specific extension of instancenode with domain validation, DNS resolution, and HMAC-based authentication.
- **`localinstancedb.py`** — SQLite database accessor with WAL mode for concurrent access. `LocalDBAccessor` base class, `HostedInstanceLocalDB` for instance list management.
- **`request.py`** / **`publish.py`** — Core recipes for requesting child partitions and publishing connection parameters.
- **`wrapper.py`** — Creates executable wrapper scripts.

### Test Infrastructure (`slapos/test/`)

- Tests are in `slapos/test/recipe/test_<recipe_name>.py`, using `unittest` and `mock`.
- **`slapos/test/utils.py`** provides `makeRecipe()` — creates a recipe instance with mocked buildout, slap-connection, and egg directories. Requires `SLAPOS_TEST_EGGS_DIRECTORY` and `SLAPOS_TEST_DEVELOP_EGGS_DIRECTORY` environment variables (set by the `slapos-local-development-environment.sh` script).
- Test discovery: `slapos/test/test_recipe.py` uses `unittest.defaultTestLoader.discover()`.

### Non-Python Content

- **`software/`** — ~75 software release profiles (buildout `.cfg` files defining full application stacks like ERP5, MariaDB, Jupyter, rapid-cdn, etc.)
- **`stack/`** — Reusable buildout stack configurations (monitor, resilient, haproxy, etc.)
- **`component/`** — ~420 component build definitions (low-level compilation profiles for libraries and tools)

## Building Software Releases

### Environment setup

Source the slapos environment before running any slapos command:
```bash
export PATH=/opt/slapgrid/cfaa2217e0f9ea9ef9e05b634f6dbecb/bin:/usr/bin:/bin:$PATH
export SLAPOS_CONFIGURATION=/srv/slapgrid/slappart76/srv/runner/etc/slapos.cfg
export SLAPOS_CLIENT_CONFIGURATION=$SLAPOS_CONFIGURATION
```

### Build a single software release

Only one `slapos node software` process can run at a time. Kill any existing one first:
```bash
kill $(cat /srv/slapgrid/slappart76/srv/runner/var/run/slapos-node-software.pid 2>/dev/null) 2>/dev/null
MAKEFLAGS=-j20 slapos node software --only <path-to-software.cfg>
```

### Software release structure (html5as reference pattern)

A software release in `software/<name>/` typically contains:
- **`software.cfg`** — Build-time profile. Extends `stack/slapos.cfg`, component profiles, and `buildout.hash.cfg`. Installs eggs, downloads templates.
- **`buildout.hash.cfg`** — Template integrity tracking (md5sums). Must be in `extends`.
- **`instance.cfg.in`** — Rendered at build time by `slapos.recipe.template:jinja2`. Produces `instance.cfg` with resolved binary paths.
- **`instance-<name>.cfg.in`** — Downloaded at build time (NOT rendered), rendered at instance time. Contains `{{ slapparameter_dict }}` and other instance-time variables.

### Two-level template rendering

1. **Build time**: `[instance-profile]` renders `instance.cfg.in` → `instance.cfg`, injecting binary paths (`raw haproxy_bin ${haproxy:location}`) and template locations (`key instance_foo instance-foo:target`).
2. **Instance time**: `instance.cfg` contains `[dynamic-template-*]` sections that render instance templates via jinja2, passing `slap_configuration`, `slapparameter_dict`, and forwarding binary paths.

Instance-time templates must be **downloaded** at build time (via `slapos.recipe.build:download`), NOT rendered with jinja2 — they contain `{{ }}` variables only available at instance time.

```ini
# Build-time download pattern
[download-base]
recipe = slapos.recipe.build:download
url = ${:_profile_base_location_}/${:_update_hash_filename_}

[instance-foo]
<= download-base
```

### Version pinning

- Section must be `[versions]` (with 's')
- Use **hyphens** in package names (`erp5-mcp-hateoas`), not underscores — buildout normalizes names
- Use `:whl` suffix for packages with non-setuptools build systems (hatchling, flit) to avoid `--no-build-isolation` failures: `mcp = 1.6.0:whl`
- `stack/slapos.cfg` pins many common packages; software-level `[versions]` can override
- When overriding `pydantic`, must also override `pydantic-core` (tightly coupled versions)

### Common build errors

- **"No module named 'hatchling'"** → Add `:whl` to the version pin
- **"Picked: X" / allow-picked-versions = false** → Add version pin; check hyphen vs underscore
- **"requirement not allowed by [versions] constraint"** → Override the stack pin in your `[versions]`

## Environment Note

If the Bash tool hangs, set `export SHELL=/bin/bash` before launching Claude Code (the default shell on this system is interactive-only and blocks non-interactive use).
