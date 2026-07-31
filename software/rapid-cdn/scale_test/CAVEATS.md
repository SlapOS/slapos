# Caveats — running the EPM scale/chaos kit on a dev node

Hard-won operational facts from large runs (validated up to 10,000 slaves and 5
frontend nodes on an 8-core / 31 GiB node). None of these is an EPM defect — the
EPM manifest/sync/seed/prune/resilience path scales cleanly and is
cert-independent. They are properties of the surrounding SlapOS dev-node infra
that you must account for at scale.

## slapproxy werkzeug form limits (needs a reversible patch above ~1000 slaves)

Between ~400 and 1000 slaves, `slapos node instance` starts failing with
`413 REQUEST ENTITY TOO LARGE` on POST `/requestComputerPartition` (master) and
`/setComputerPartitionConnectionXml` (frontends). Modern werkzeug caps form
parsing (`max_form_memory_size` ≈ 500 KB, `max_form_parts` ≈ 1000); the slave
list / connection XML for ~1000 slaves exceeds it.

Reversible patch on this node's `slapos.core` (back up first, restore at
teardown): in `slapos/proxy/views.py`, right after `app = Flask(__name__)`, set
`MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE` / `MAX_FORM_PARTS` to `None`, and
set the same attributes on `app.request_class` (older Flask does not map the
config keys onto the request). Restart slapproxy. After the patch, 1000+ slaves
converge with zero errors. This patches infra, not Rapid.CDN — file it as an
observation, not part of the SR change.

## slapproxy per-request O(N) — converge time dominates at scale

slapproxy uses a single-writer SQLite DB; per-request cost grows with the number
of partitions. Observed: slave-request throughput degraded to ~1.4/s near 10k,
and a single master `slapos node instance` pass took ~28 min at 10k backends ×
frontends. Budget wall-clock accordingly and prefer manual convergence (below).

## Disable the per-minute crons; converge manually

At scale each `slapos node instance` / `slapos node software` pass takes minutes,
and overlapping cron passes collide (`rc=10 "another slapos process already
running"`). Back up and disable the crons in `/etc/cron.d/slapos-node` for the
duration and drive convergence by hand for deterministic timing. **Re-enable at
teardown** — the default node state is crons enabled.

## Add / remove needs a `.timestamp` reset to re-converge

slapproxy gates re-processing with a `.timestamp` file per partition. After
changing a shared-list (add/remove slaves, add a frontend), clear the relevant
`.timestamp` so the partition is picked up again; otherwise convergence is a
no-op and the change never lands.

## slapproxy cannot actually destroy a shared slave

Requesting a shared instance with `state='destroyed'` is a **no-op on slapproxy**
— a slave has no requested-state column, so `scale-remove-slave.py` will not
truly remove it there. The EPM's removed-slave prune
(`software._prune_removed_shared_overrides`) is real and is covered at unit level
and by `../test/test.py::TestErrorPageManagerRemovedSlave`; it just cannot be
driven end-to-end through slapproxy. On a real master (retention-resolved shared
list) removal works and prunes as designed.

## kedifa per-slave certificate throughput lags at scale (serving is fine)

After adding thousands of slaves, their per-slave kedifa certificates can stay
`NotReadyYet` for a while — reservation tokens are minted for all of them, but
the per-slave cert upload/settle at the kedifa-updater / caucase layer lags.
**Serving is unaffected**: Rapid.CDN frontends fall back to the master
certificate, so every slave serves over HTTPS regardless. This is a SlapOS
kedifa/caucase scaling characteristic orthogonal to the EPM; it only matters for
slaves that need their own custom cert.

## Orphaned EPM squatting the port → /sync 401

If a previous EPM process is left running and squatting the manager port, the
managed instance cannot bind it, and requests hit the orphan (with rotated
tokens) → `/sync` returns 401. Kill the orphan (match `/proc/*/cmdline` for
`error-page-manager.json`, not by `ps | grep`, to avoid self-match) so the
managed instance binds the port.

## Mixed-SR / binary cache URL form

`scale-request-mixed-cluster.py` pins the old frontend to the last released tag
via the **canonical** `https://lab.nexedi.com/nexedi/slapos/-/raw/<tag>/...`
URL. The non-canonical `/raw/` form (no `-`) is **not** in the binary cache on
this node and forces a from-source rebuild — always use the `/-/raw/` form (and,
if enforcing binary-only for released versions, guard the
`download-from-binary-cache-force-url-list` pattern against URLs missing the
leading `-`).
