# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**slapos.cookbook** is a Python package providing 90+ [zc.buildout](https://www.buildout.org/) recipes for the [SlapOS](https://slapos.nexedi.com/) distributed cloud operating system. Each recipe is a buildout plugin that configures and deploys a specific software component within a SlapOS partition.

## Local Environment

Machine-specific paths are stored in `.claude/env.local.json` (not committed). Copy `.claude/env.local.json.example` and fill in paths for your environment. Keys:

- `cookbook-repository`: path to the slapos.cookbook checkout used for running unit tests
- `environment-script`: path to `slapos-local-development-environment.sh` for unit tests
- `integration-test-environment-script`: path to the environment script for integration tests
- `python-binary`: path to the Python binary with slapos.cookbook installed
- `public-dir`: path to the frontend-static public directory for publishing eggs

## Running Tests

Tests must be run from the **cookbook-repository** path (see `env.local.json`):

```bash
cd <cookbook-repository>
source <environment-script>
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

rapid-cdn has full SlapOS instance deployment tests in `software/rapid-cdn/test/test.py`. Use the **`/run-rapid-cdn-test`** command to run them:

```
/run-rapid-cdn-test test.TestClassName.test_method_name
/run-rapid-cdn-test test.TestClassName --save-data --rebuild --debug
```

Flags: `--save-data` (regenerate expected output), `--rebuild` (rebuild software), `--debug` (keep instances alive on failure).

Key constraints:
- Tests **cannot run in parallel** — they share a SlapOS proxy on port 21584
- Before launching, check for active runners: `ps aux | grep '[p]ython_for_test.*unittest'`
- If config files changed (`instance.cfg.in`, `buildout.hash.cfg`, etc.), run with `--rebuild` first
- Slave test classes take ~4-15 min; master-only classes take ~4 min

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

- **NEVER** run `git push` without explicitly specifying both the remote and the branch (e.g., `git push cln cln_slap_json`).
- **ONLY** push to remotes whose URL starts with `https://lab.nexedi.com/cedric.leninivin/` (the user's personal forks). Currently that is the `cln` remote. Before pushing, verify the remote URL with `git remote get-url <remote>`.
- **NEVER** push to `nxd` (nexedi upstream) or `origin` (romain's fork) — these are read-only sources.
- If the user asks to push, confirm the target remote and branch before executing.
- **NEVER** use commands that reset a branch to another ref (e.g., `git checkout -B <branch> <ref>`, `git branch -f <branch> <ref>`, `git reset --hard <ref>`) — these silently overwrite the branch's upstream tracking config. To update a branch with latest upstream, use `git rebase nxd/master` (or `git fetch nxd && git rebase nxd/master`) which preserves the existing tracking.

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

## Environment Note

If the Bash tool hangs, set `export SHELL=/bin/bash` before launching Claude Code (the default shell on this system is interactive-only and blocks non-interactive use).
