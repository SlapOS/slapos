===================
rapid-cdn Changelog
===================

A functional changelog for CDN **operators** and **users**. Each entry
is a short description of a behaviour or parameter change, tagged with
the audience it affects — **[operator]**, **[user]**, or
**[operator, user]** — according to which interface files changed:

* **operator** — ``instance-input-schema.json`` /
  ``instance-output-schema.json``
* **user** — ``instance-slave-input-schema.json`` /
  ``instance-slave-output-schema.json``
* **operator, user** — ``software.cfg.json``, or a change spanning both
  the operator and user schemas

Purely internal / developer changes are omitted, as are releases with
no functional change. Entries describe net changes (not commit history)
and cite the commit(s) — and, for grouped work, the merge request — that
produced them. The changelog covers releases from 1.0.377 onward.

Unreleased
----------

**[operator]** *CDN instance node with a local audit database.*
rapid-cdn now ships a CDN instance node that adds a passive, transparent
audit layer alongside the existing slave deployment: every slave's
parameters are validated against the JSON schema and the outcome
(valid/invalid, with the specific errors) is written to a local SQLite
database an operator can browse with sqlite-web. For custom domains the
node also proves domain ownership (an HMAC ``_slapos-challenge`` DNS TXT
record), verifies the SSL certificate matches and is not expired, and
flags server-alias conflicts between slaves — all from a crontab,
independently of the deployment cycle. Nothing is rejected or altered
yet; this is the audit-and-notify first step. Two new cluster parameters
arrive with it: ``instance-retention-delay`` (integer seconds; default
``7776000`` = 90 days, ``0`` = remove immediately) sets how long a
disappeared instance is kept before the node removes it, and
``dns-nameserver`` now accepts a comma-separated list in which each
entry may pin an explicit resolver port (``ip:port`` or ``[ipv6]:port``,
default 53) — a bare host still works unchanged.
(!1975, 226820cb0, 3f4a3e520, ed411f684)

**[operator]** *Dedicated monitoring-interface URL.* The monitoring web
interface gained a dedicated ``monitor-interface-url`` parameter on the
frontend, and its default across the cluster, frontend, and kedifa now
points at ``https://monitor.app.officejs.com/#page=ojsm_landing``.
(40e3afe24)

**[operator, user]** *Explicit slave parameter serialisation.* The
shared slave software types ``custom-personal-slave`` and
``default-slave`` now declare ``serialisation: xml`` explicitly, while
the cluster itself stays on ``json-in-xml``. This governs how slave
request parameters are encoded. (5b0560583)

1.0.469 (2026-03-06)
--------------------

**[operator, user]** *Parameters moved to slapconfiguration.jsonschema.*
Both cluster and slave parameters are now declared and validated through
``slapconfiguration.jsonschema``, unifying how they are read from their
JSON schemas. (8871f2053)

**[operator]** *Reliable parameter passing to frontend nodes.* Fixed the
propagation of parameters to the frontend nodes, so cluster-level
configuration reliably reaches each frontend. (e650ac64e)

1.0.464 (2026-02-05)
--------------------

**[operator, user]** *JSON schemas upgraded to the latest draft.* All
JSON parameter schemas were moved to the latest draft version, changing
how both cluster and slave parameters are described and validated.
(707bc5b7b)

1.0.446 (2025-10-21)
--------------------

**[operator]** *Parameter changes applied with a service restart.*
Changed cluster parameters are now applied by restarting the affected
service, so configuration updates take effect reliably. (8eff44b0b)

1.0.427 (2025-07-24)
--------------------

**[user]** *HTTP/1.0 for backend health checks.* Backend health checks
now use HTTP/1.0, improving compatibility with simple origin servers.
This is driven by the per-slave health-check configuration. (4c036fdc3)
