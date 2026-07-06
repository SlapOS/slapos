===================
rapid-cdn Changelog
===================

Entries are grouped by the audience a change impacts, determined by
which interface files it touches:

* **Operators** — ``instance-input-schema.json`` /
  ``instance-output-schema.json``.
* **Users** — ``instance-slave-input-schema.json`` /
  ``instance-slave-output-schema.json``.
* **Operators and users** — ``software.cfg.json`` (and changes spanning
  both the operator and user schemas).
* **Developers** — everything else.

Entries describe the net changes of each release, not its intermediate
commit history, and cite the commit(s) — and, for grouped work, the
merge request — that produced them so a reader can backtrack the source.

Unreleased
----------

Net changes since the last release (1.0.469), not yet part of a tagged
release.

Operators
~~~~~~~~~

* Add a CDN instance node backed by a local instance database
  (!1975, 226820cb0): a passive, transparent audit pipeline that
  validates each slave's parameters against the JSON schema and stores
  the result (valid/invalid + errors) in a local SQLite database
  operators can query with sqlite-web. For custom domains it performs
  DNS domain-ownership verification (an HMAC ``_slapos-challenge`` TXT
  record), SSL certificate validation, and server-alias conflict
  detection, running from crontab. No slave is rejected, blocked, or
  modified.
* New cluster parameter ``instance-retention-delay`` (integer seconds,
  default ``7776000`` = 90 days; ``0`` means immediate removal), which
  controls how long a disappeared instance is retained before the
  instance node removes it (introduced 226820cb0, 90-day default
  3f4a3e520).
* ``dns-nameserver`` now accepts a comma-separated list, and each entry
  may carry an explicit port (``ip:port`` or ``[ipv6]:port``; default
  port 53). A single host without a port stays valid, so existing values
  need no change (ed411f684).
* New frontend parameter ``monitor-interface-url``, and its default
  updated to ``https://monitor.app.officejs.com/#page=ojsm_landing`` on
  the cluster, frontend, and kedifa schemas (40e3afe24).

Operators and users
~~~~~~~~~~~~~~~~~~~~~

* The shared slave software types ``custom-personal-slave`` and
  ``default-slave`` now declare ``serialisation: xml``; the cluster
  itself keeps ``json-in-xml`` (5b0560583).

Developers
~~~~~~~~~~

* Fix backend connection-drop on HTTP/2 and HTTP/3 clients: enable L7
  retries (``retry-on conn-failure empty-response response-timeout``) so
  a reused pool connection whose upstream closed mid-keepalive returns a
  clean 502 instead of aborting the client stream (92953c99f).
* Preserve the URL path in ``type=redirect`` ``Location`` responses
  (fcc8f9ecf), preserve a trailing slash when a query string is present
  (06f1879ed), and escape ``%`` in backend request paths so ``%20`` is
  not read as a haproxy format specifier (73545ea74).
* Response headers: always emit ``Date``; add ``Via`` on https-only
  redirects and the not-found backend; emit ``alt-svc`` /
  ``alternate-protocol`` on the not-found backend under HTTP/3; and
  advertise HTTP/2 via ALPN when ``enable-http2-by-default`` is set
  (c28d7aa47, fixup ad00a85c2).
* Instance-node internals: move the activity-check logic into
  ``software.py`` as a promise plugin (fccfbebc9, c20acd016), allocate
  master-introspection ports via ``slapos.cookbook:free_port``
  (9d0974d2d), check its cron with the generic cron promise (3c3899068),
  preserve the row timestamp on no-op updates to stop a bang loop
  (797c1c4d9), and wire publish-file race detection (e0cd2638f).
* Dependencies: version up kedifa 0.0.7 to 0.0.8 (85abd167a); add
  sqlite-web 0.7.2 and peewee 3.19.0 for the audit database (226820cb0,
  21cc89d1e); drop the ``zc.lockfile`` pin and a duplicate (85abd167a,
  6a1fd04ae).
* Rename ``valided-`` to ``validated-`` and ``domainvalidation-`` to
  ``domain-validation-`` in the instance profiles (89c209a3a, ed93d1784);
  document the instance node in the README (da314f26f); Python 3.13 test
  compatibility and numerous test additions and fixes.

1.0.469 (2026-03-06)
--------------------

Operators
~~~~~~~~~

* Fix passing parameters to the frontend nodes (e650ac64e).

Operators and users
~~~~~~~~~~~~~~~~~~~~~

* Move instance parameters to ``slapconfiguration.jsonschema``
  (8871f2053, fixup 642c37dd8).

Developers
~~~~~~~~~~

* Shared (slave) instances no longer send an error message on bad
  parameters (8f98bfe13).
* Drop unnecessary type casting in the kedifa instance (d5d7fe42e) and
  clean up the backend haproxy caucase variables (3018a6e6a).

1.0.464 (2026-02-05)
--------------------

Operators and users
~~~~~~~~~~~~~~~~~~~~~

* Move all JSON schemas to the latest draft version (707bc5b7b).

Developers
~~~~~~~~~~

* Drop the reject-slave promise (492a0b5a4).
* Desensitize kedifa-related promises (fa1ddd659) and make promise
  errors more explanatory (d2228fda0).
* Improve operator information on clashed domains (5f96e7a89).
* Make curl-http3 the only curl build (6c4024552).

1.0.453 (2025-11-26)
--------------------

Developers
~~~~~~~~~~

* Revert the "Fix inconsistency" change from 1.0.446 (931bc1191, reverts
  821e25303).

1.0.448 (2025-10-28)
--------------------

Developers
~~~~~~~~~~

* Review TrafficServer timeouts (e1741564e).

1.0.446 (2025-10-21)
--------------------

Operators
~~~~~~~~~

* Apply changed parameters with a service restart (8eff44b0b).

Developers
~~~~~~~~~~

* Implement TrafficServer inspection and allow all verbs to pass via
  TrafficServer (8d93dbb76, 014785e50).
* Switch the ``ip_allow`` configuration from config to YAML (1f250d9aa).
* Assure the ``Date`` response header is present and that the backend
  always adds the header (1fbcf18e0, edee1298f).
* Add a dedicated JSON schema for slave-only deployments (30a7e8995).
* Drop a no-longer-required parameter (31ff9e042).
* Fix an inconsistency (821e25303) — later reverted in 1.0.453.

1.0.427 (2025-07-24)
--------------------

Users
~~~~~

* Use HTTP/1.0 for health checks (4c036fdc3).

Developers
~~~~~~~~~~

* Harden handling of unusual parameter values (b6fa1f2f7).
* Simplify the log split (c62b16380) and minimize produced files
  (746f9ea50).
* Allow starting the backend with SSL (d6722e530).

1.0.395 (2025-02-06)
--------------------

Developers
~~~~~~~~~~

* Implement expert SSL downgrade (498e3ad1e).
* Drop dependence on ``slave-log-directory-dict`` (0a2e149f9).
* Version up OpenSSL to 1.1.1w-0+deb11u2 (46f5a6a1b).

1.0.377 (2024-11-21)
--------------------

* Earliest release covered by this changelog.
