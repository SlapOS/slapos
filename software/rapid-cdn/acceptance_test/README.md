# Rapid.CDN error-page-manager — human acceptance test

A step-by-step **manual** acceptance procedure for the Rapid.CDN
**error-page-manager (EPM)**, run by a human on a VM connected to a **real
SlapOS master**, driving the **real user interfaces**:

- the **SlapOS master panel** — to request the cluster, set its parameters,
  request shared instances, and read the published connection parameters;
- the EPM **operator** error-page editor (a web page at `operator-url`);
- the **shared-instance** editor (a web page at each slave's `upload-url`);
- the **CDN frontend** actually serving the rendered error page in a browser.

## Why this exists (and how it differs from the other two levels)

The `error-page-manager` fix (bug `bug_module/20260722-9BC510`) is covered at
three levels; this is the third:

| Level | Where | Who runs it | What it covers |
|---|---|---|---|
| Headless CI | `../test/test.py` (`TestErrorPageManager*`) | CI, automatically | Correctness, resilience, scale invariant — via slapproxy, no browser. |
| Operator scale/chaos kit | `../scale_test/` | An operator, by hand on a dev node | Thousands of slaves, multiple frontends, chaos — scripted. |
| **Human acceptance (this)** | this directory | **A human, in a browser, against a real master** | Real allocation path + the operator/slave UX and what an end user actually sees. |

Automation cannot judge the visual UI, and slapproxy is not the real master —
this procedure closes both gaps. It is **not** a `slapos.testing` suite; it is a
checklist a person follows and records the outcome of.

## Prerequisites

- Access to a **real SlapOS master** where you can request instances, and a VM
  with a **web browser** that can reach the cluster's frontend and the EPM URLs
  (the EPM listens on IPv6 — ensure the VM has IPv6 reachability to it, or use
  the master-published operator URL if the master proxies it).
- The Rapid.CDN software release available on the master.
- Willingness to wait: the frontend error-page **updater polls about every 60 s**,
  so the browser-serving checks (section D) need a short wait + refresh after an
  upload before the new page appears.

## How to use

Work top to bottom. Each check is **Action → Expected on-screen result**. Record
Pass/Fail/Notes in the table at the end (or copy it into a dated report, e.g.
`rapid-cdn-epm-acceptance-report-YYYY-MM-DD.md`).

**Override precedence** (the rule several checks verify), highest first:
1. site-owner (shared-instance) override,
2. operator custom page,
3. built-in default page.

---

## A. Provision through the master panel

### A1 — Request the cluster
- **Action:** In the master panel, request a new instance of the Rapid.CDN
  software release with software type **`default`**. Give it a name (e.g.
  `acceptance-cluster`) and set the instance parameters (at minimum a `domain`,
  e.g. `example.org`). Submit.
- **Expected:** The instance is accepted and, after allocation/convergence,
  reports as started/green in the panel with no failing promises.

### A2 — Request shared instances (slaves)
- **Action:** Request **two** shared instances of the cluster. For at least one
  (call it the *down-backend slave*), set its `url` parameter to a
  non-listening address (e.g. `http://[::1]:1/`) so the origin is down and the
  frontend must serve an error page. Submit and let it converge.
- **Expected:** Both shared instances appear allocated under the cluster, each
  with its own auto-derived domain.

### A3 — Read the published connection parameters
- **Action:** Open the cluster's connection parameters in the panel and note the
  **operator URL** (`error-page-manager-operator-url`). Open each shared
  instance's connection parameters and note its **upload URL**
  (`error-page-upload-url`) and its **domain**.
- **Expected:** All URLs are present. The operator and upload URLs are HTTPS
  and carry a token path segment. Keep this tab open — later sections use these.

---

## B. Operator error-page editor (web UI)

### B1 — Operator UI loads
- **Action:** Open the **operator URL** in the browser.
- **Expected:** An HTML editor page loads over HTTPS showing **one editable row
  per supported code — all seven: 400, 404, 408, 500, 502, 503, 504** — each
  with a text area and Save / Reset controls.

### B2 — Save a custom operator page
- **Action:** In the **404** text area, enter recognisable HTML (e.g.
  `<html><body><h1>Operator 404 — acceptance</h1></body></html>`) and click
  **Save** for that code.
- **Expected:** The page reloads/refreshes and the 404 text area now shows the
  HTML you saved (the change persisted).

### B3 — Reset to built-in
- **Action:** Click **Reset** for the 404 row.
- **Expected:** The page refreshes and the 404 text area is empty again (custom
  page removed; the built-in default is back in effect).

### B4 — Bad operator token is rejected
- **Action:** In the browser, edit the operator URL to corrupt the token
  segment (e.g. change the last path element) and open it.
- **Expected:** Access is refused (**401 Unauthorized**); no editor is shown.

---

## C. Shared-instance editor (web UI)

### C1 — Shared UI loads (only 502/503/504)
- **Action:** Open the *down-backend slave*'s **upload URL** in the browser.
- **Expected:** An editor page loads showing **only three codes: 502, 503, 504**
  (the cluster-only codes 400/404/408/500 are **not** offered here).

### C2 — Save a custom shared page
- **Action:** In the **503** text area enter recognisable HTML (e.g.
  `<html><body><h1>Slave 503 — acceptance</h1></body></html>`) and click **Save**.
- **Expected:** The page refreshes and the 503 text area shows your HTML.

### C3 — Reset the shared page
- **Action:** Click **Reset** for the 503 row.
- **Expected:** The 503 text area is empty again.

### C4 — Cluster-only code is not settable here
- **Action:** Confirm there is no 404 (or other cluster-only) editor on this
  page. (If you craft a request to save one anyway, it must be refused.)
- **Expected:** The shared editor exposes only 502/503/504; an attempt to save a
  cluster-only code is rejected (**400 Bad Request**).

### C5 — Bad shared token is rejected
- **Action:** Corrupt the token in the upload URL and open it.
- **Expected:** Refused (**401 Unauthorized**).

---

## D. Frontend serving — what the end user sees

These use a **browser hitting the CDN frontend** on the *down-backend slave*'s
domain. Because that slave's origin is down, the frontend must serve an EPM
error page. After each upload/delete, **wait ~60–120 s and refresh** (updater
poll interval) before judging.

To resolve the slave domain to the frontend from your VM, add a hosts entry (or
use the browser/OS override) mapping the slave domain to the frontend's IPv6
address on its HTTPS port, then browse `https://<slave-domain>/`.

### D1 — Built-in page for a down backend
- **Action:** With no overrides set, browse the slave domain over HTTPS.
- **Expected:** An **HTTP 503** built-in "Service Unavailable" error page renders
  (the cluster default), not a connection error and not origin content.

### D2 — Operator override is served
- **Action:** In the operator editor (section B) save a custom **503** with
  recognisable text. Wait ~60–120 s, then refresh the slave domain in the browser.
- **Expected:** The rendered 503 page now shows the **operator's** custom text.

### D3 — Site-owner override wins over operator (precedence)
- **Action:** In the shared editor (section C) save a **different** custom **503**
  for this slave. Wait ~60–120 s and refresh the slave domain.
- **Expected:** The rendered page now shows the **shared-instance** text, not the
  operator text — the site-owner override takes precedence.

### D4 — Delete reverts down the precedence chain
- **Action:** In the shared editor, **Reset** 503. Wait ~60–120 s, refresh.
  Then in the operator editor **Reset** 503. Wait ~60–120 s, refresh again.
- **Expected:** After the shared reset, the page reverts to the **operator** 503;
  after the operator reset, it reverts to the **built-in** 503. (A slave with no
  override "inherits" the operator/cluster page — it is served the cluster file,
  no per-slave page is created for it.)

---

## E. Lifecycle

### E1 — A slave added after startup inherits the cluster page
- **Action:** With an operator 503 set, request a **new** shared instance
  (down backend). Let it converge, then browse its domain (~wait for the updater).
- **Expected:** The new slave immediately serves the **operator/cluster** 503
  page even though it never set its own — until it uploads its own override.

### E2 — Removing a slave prunes its override
- **Action:** Give a slave its own 503 override, confirm it serves, then request
  that shared instance **destroyed** in the master panel. Let the cluster
  reconverge.
- **Expected:** The removed slave's override is pruned — it no longer appears in
  the EPM state and is no longer served. (This is the real-master path; note that
  a local slapproxy cannot destroy a slave — see `../scale_test/CAVEATS.md`.)

---

## F. Monitoring UI

### F1 — Monitor pages are healthy
- **Action:** From the cluster's published monitor URL, open the monitoring web
  UI for the cluster and the EPM partition.
- **Expected:** The monitor pages load and the promises for the EPM and frontend
  partitions are **green** (no failing checks).

---

## Results

| Check | Pass/Fail | Notes |
|---|---|---|
| A1 cluster requested |  |  |
| A2 shared instances requested |  |  |
| A3 connection parameters read |  |  |
| B1 operator UI loads (7 codes) |  |  |
| B2 operator save |  |  |
| B3 operator reset |  |  |
| B4 operator bad token 401 |  |  |
| C1 shared UI loads (3 codes) |  |  |
| C2 shared save |  |  |
| C3 shared reset |  |  |
| C4 cluster-only code rejected |  |  |
| C5 shared bad token 401 |  |  |
| D1 built-in 503 served |  |  |
| D2 operator override served |  |  |
| D3 site-owner precedence |  |  |
| D4 delete reverts down chain |  |  |
| E1 new slave inherits cluster page |  |  |
| E2 removed slave pruned |  |  |
| F1 monitor green |  |  |

Record the software release / MR revision under test, the master, the date, and
the tester. File failures with a screenshot where the on-screen result differs
from "Expected".
