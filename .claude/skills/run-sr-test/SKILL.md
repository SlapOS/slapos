---
name: run-sr-test
description: Run a software release integration test in the background with proper environment setup
argument-hint: "<software-name> <test-target> [--save-data] [--debug]"
allowed-tools: Bash, Read
---

# Run Software Release Integration Test

Run a software release integration test in the background with proper environment setup.

## Arguments

**$ARGUMENTS** — space-separated tokens parsed as follows:

- **Software name** (required): directory name under `software/` (e.g. `rapid-cdn`, `erp5-mcp-hateoas`)
- **Test target** (required): fully qualified test identifier, e.g.
  `test.TestSlave` (whole class) or
  `test.TestSlave.test_url` (single method)
- **--save-data**: set `SAVE_TEST_DATA=1` to regenerate expected test data files
- **--debug**: set `SLAPOS_TEST_DEBUG=1` to keep instances alive after failure

Default behaviour (no flags): rebuild software, check software, debug off.

## Environment Setup

Read `.claude/env.local.json` for machine-specific paths. The relevant key is:

- `slapos-sr-testing-environment`: path to the `slapos-local-development-environment.sh` for integration tests

## Pre-flight

Before launching the test, verify no other test is already running:

```bash
ps aux | grep '[p]ython_for_test' | grep -v grep
```

If a process is found, warn the user and do **not** start a new test. Software release tests
use fixed SlapOS proxy ports and cannot run concurrently.

## Execution

Run the test **in the background** using the Bash tool with `run_in_background: true`.

Build the command using the environment script from `.claude/env.local.json`:

```bash
cd <project-root>/software/<software-name>/test/ && \
source <slapos-sr-testing-environment> && \
SLAPOS_TEST_DEBUG=${DEBUG:-0} \
${SAVE_DATA:+SAVE_TEST_DATA=1} \
python_for_test -m unittest ${TEST_TARGET} -v 2>&1
```

Construct the actual command by substituting:
- `${TEST_TARGET}` = the test target from arguments
- Do NOT set `SLAPOS_TEST_SKIP_SOFTWARE_REBUILD` or `SLAPOS_TEST_SKIP_SOFTWARE_CHECK` — always let the framework rebuild and check software
- Include `SLAPOS_TEST_DEBUG=1` only if `--debug` was passed (otherwise `SLAPOS_TEST_DEBUG=0`)
- Include `SAVE_TEST_DATA=1` only if `--save-data` was passed

Tell the user the test is running in the background and approximately how long it may take. When the background task completes, analyze the output.

## Result Analysis

After the test finishes, check the output for these patterns:

| Pattern | Meaning | Action |
|---------|---------|--------|
| `OK` at end | All tests passed | Report success |
| `FAILED (failures=N)` | Assertion failures | Show failing test names and first diff/assertion |
| `assertTestData` mismatch | Expected output changed | Suggest re-running with `--save-data` if the new output is correct |
| `Connection refused` on port 21584 | Another test is running or proxy didn't start | Wait a few minutes and retry |
| `nxdbom ... Cannot load .installed.cfg` | Software not built for current hash | Software will be rebuilt automatically |
| `ERROR` with traceback | Code error | Show the traceback and suggest a fix |

## rapid-cdn Test Class Reference

rapid-cdn tests are the most common use case. Here is a timing reference:

| Class | Type | ~Duration | Notes |
|-------|------|-----------|-------|
| `TestMasterRequestDomain` | master | 4 min | Domain-mode master request |
| `TestMasterRequest` | master | 4 min | Standard master request |
| `TestMasterAIKCDisabledAIBCCDisabledRequest` | master | 4 min | AIKC/AIBCC disabled |
| `TestSlave` | slave | 12-15 min | Main slave test (largest) |
| `TestSlaveHttp3` | slave | 12-15 min | HTTP/3 variant |
| `TestEnableHttp2ByDefaultFalseSlave` | slave | 12-15 min | HTTP/2 disabled variant |
| `TestReplicateSlave` | slave | 8 min | Replication |
| `TestReplicateSlaveOtherDestroyed` | slave | 8 min | Replication with destroyed node |
| `TestRe6stVerificationUrlSlave` | slave | 8 min | Re6st verification |
| `TestSlaveSlapOSMasterCertificateCompatibilityOverrideMaster` | slave | 8 min | Cert compat override |
| `TestSlaveSlapOSMasterCertificateCompatibility` | slave | 10 min | Cert compat |
| `TestSlaveSlapOSMasterCertificateCompatibilityUpdate` | slave | 10 min | Cert compat update |
| `TestSlaveCiphers` | slave | 8 min | Custom cipher config |
| `TestSlaveRejectReportUnsafeDamaged` | slave | 8 min | Reject/report/unsafe/damaged slaves |
| `TestSlaveHostHaproxyClash` | slave | 8 min | Host clashing |
| `TestPassedRequestParameter` | master | 4 min | Parameter passing |
| `TestSlaveHealthCheck` | slave | 10 min | Health check |
| `TestSlaveManagement` | slave | 8 min | Slave management |
| `TestCDNHTTP` | slave | 8 min | CDN HTTP features |
