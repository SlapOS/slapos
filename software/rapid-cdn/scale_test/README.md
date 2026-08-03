# Rapid.CDN error-page-manager — operator scale & chaos kit

An on-node toolkit for exercising the Rapid.CDN **error-page-manager (EPM)** at
a scale the headless CI suite cannot reach (thousands to ~10,000 shared slaves,
multiple frontend nodes) and for chaos-testing its server↔client resilience.

**This is not a `slapos.testing` test suite** and is *not* discovered by the CI
`test_suite` machinery. It is a set of operator scripts run by hand on a
development node that has a local slapproxy. The automated, CI-friendly scale
coverage lives in `../test/test.py::TestErrorPageManagerScale` — this kit is for
going beyond that, deliberately and under human supervision.

For the invariant under test and why it matters, see the automated test's
docstring: the EPM manifest is **O(overrides)** — it lists the seven cluster
defaults plus a `shared/<ref>/<code>.http` key only where a slave actually
overrides a code, so it stays flat regardless of the slave count. This kit
verifies that on a real, large deployment and measures the cost.

Read `CAVEATS.md` before a large run — it documents the infra limits (slapproxy
form caps, per-request O(N), no live slave-destroy, kedifa cert throughput) and
the reversible node patch a >1000-slave run needs.

## Prerequisites

- A SlapOS development node with a local slapproxy (node id `local_computer` by
  default) and the Rapid.CDN software release compiled.
- The scripts default to `/opt/slapos.git/software/rapid-cdn/software.cfg`;
  override with `RAPIDCDN_SOFTWARE=/path/to/software.cfg` for another checkout.
- `slapos console` / `slapos node instance` available (this kit drives
  convergence; at scale you typically disable the per-minute crons and converge
  manually — see `CAVEATS.md`).

## Contents

| File | Kind | Purpose |
|---|---|---|
| `scale-request-cluster.py` | slapos console | Request the base `scale-cluster` with `EPM_FRONTEND_QTY` frontends. |
| `scale-request-slaves.py` | slapos console | Request a range of shared slaves (`EPM_SLAVE_START`/`EPM_SLAVE_COUNT`/`EPM_SLAVE_URL`). |
| `scale-remove-slave.py` | slapos console | Destroy slaves by reference (`EPM_REMOVE_REFS`). See CAVEATS for the slapproxy no-op. |
| `scale-request-mixed-cluster.py` | slapos console | Mixed-SR cluster: control plane on the checkout, `frontend-2` pinned to the last release. |
| `request-epm-standalone.py` | slapos console | Request a standalone `error-page-manager` partition (no full cluster). |
| `epm-collect-params.py` | slapos console | Dump every endpoint / on-disk path the harness needs to `epm-params.json`. |
| `epm-e2e.py` | python3 | The stdlib end-to-end harness (`Ctx`, scenarios, resilience helpers). Imported by the two below. |
| `scale-validate.py` | python3 | Per-rung metrics: manifest size/latency, EPM RSS/threads, seed symlinks, serving, resilience → `scale-metrics.csv`. |
| `epm-chaos-test.py` | python3 | Break server↔client comms (SIGKILL EPM, drop the port, reset conns, kill updater, flood) and assert continuity. |

## Flow

All `slapos console` steps use your node's config, e.g.
`CFG=/etc/opt/slapos/slapos.cfg`.

### 1. Deploy

```bash
# base cluster with 4 frontends
EPM_FRONTEND_QTY=4 slapos console --cfg "$CFG" scale-request-cluster.py
# ... converge (slapos node instance) until the cluster is green ...

# 200 slaves whose backend is down (so the frontend serves the EPM error page)
EPM_SLAVE_START=1 EPM_SLAVE_COUNT=200 EPM_SLAVE_URL=down \
  slapos console --cfg "$CFG" scale-request-slaves.py
# ... converge again ...
```

Ramp in rungs (100 → 1000 → 3000 → 10000), converging and validating at each
step. Add more slaves by advancing `EPM_SLAVE_START`.

### 2. Collect params + measure

```bash
slapos console --cfg "$CFG" epm-collect-params.py          # writes epm-params.json
python3 scale-validate.py --params epm-params.json --label 200
# appends a row to scale-metrics.csv and prints the rung summary
```

The key assertion at every rung: `manifest_cluster == 7` and
`manifest_shared == 0` (flat), and one override anywhere adds exactly one shared
key. `seed_link_problems` must stay `0`.

### 3. Chaos (optional)

```bash
python3 epm-chaos-test.py --params epm-params.json \
  --epm-prog <epm-on-watch-supervisor-program-name> \
  --report epm-chaos-report.md
```

Pass the EPM's on-watch supervisor program name (find it with
`slapos node supervisorctl --cfg "$CFG" status | grep error-page-manager`). The
run reports end-user **serving continuity** through each fault.

### 4. Teardown

Destroy the requested instances and, if you disabled them, re-enable the crons.
See `CAVEATS.md` for the `.timestamp` reset needed to re-converge add/remove and
the fact that slapproxy cannot actually destroy a shared slave.

## Relationship to the CI scale test

`../test/test.py::TestErrorPageManagerScale` runs headless with a default of 200
slaves and honours the **same** `RAPIDCDN_TEST_EPM_SLAVE_COUNT` idea — set that
env var to crank the CI test up (e.g. `RAPIDCDN_TEST_EPM_SLAVE_COUNT=1000`) for
a nightly/manual larger run without this kit. Use this kit when you need a full
multi-frontend cluster, real serving, or chaos — things the standalone CI
partition deliberately does not cover.
