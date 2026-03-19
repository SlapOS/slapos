---
name: test-results
description: Fetch test results for a git commit from ERP5's test_result_module
argument-hint: "[commit-hash]"
allowed-tools: Bash
---

# Fetch Test Results from ERP5

Look up test results for a git commit from ERP5's `test_result_module`.

## Arguments

**$ARGUMENTS** — optional commit hash (short or full). If omitted, use `HEAD`.

## Execution

### Step 1: Determine the commit hash

If the user provided a commit hash in `$ARGUMENTS`, use it. Otherwise, run:

```bash
git rev-parse HEAD
```

Store both the full hash and the short hash (`git rev-parse --short HEAD`).

### Step 2: Discover test_result_module fields

Use `mcp__erp5__erp5_search` to search `test_result_module` with the commit hash as the `reference` filter. Select these fields: `title`, `reference`, `string_index`, `simulation_state`, `creation_date`, `int_index`.

Search query: wrap the commit hash in `%` wildcards for partial matching (e.g., `reference:"%<hash>%"`). Use the **full** commit hash first. If no results, retry with the **short** hash.

### Step 3: Read detailed results

For each test result document found, use `mcp__erp5__erp5_read` on its path to get full details.

Then search for test result lines within each test result using `mcp__erp5__erp5_search` on the test result's path (e.g., `test_result_module/XXXX`) to find child documents (test result lines). Read a sample of any failed lines for details.

### Step 4: Present summary

Format the output as:

```
## Test Results for <short-hash>

**Commit**: <full-hash>
**Found**: N test result(s)

### <Test Result Title> — <state>
- **Created**: <date>
- **Status**: <pass/fail summary>
- **Lines**: X passed, Y failed

#### Failures (if any)
- <test name>: <error summary>
```

## Handling edge cases

- **No results found**: Tell the user no test results were found for this commit. Suggest they check whether tests have been submitted, or try a different commit hash.
- **Multiple test results**: Show all of them, newest first.
- **Still running**: If `simulation_state` is not a final state (e.g., `started`), note that the test is still in progress.
