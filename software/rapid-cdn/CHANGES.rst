===================
rapid-cdn Changelog
===================

Entries describe the net changes of each release, not its intermediate
commit history, and cite the commit(s) — and, for grouped work, the
merge request — that produced them so a reader can backtrack the source
of a change.

Unreleased
----------

Net changes since the last release (1.0.469), not yet part of a tagged
release.

Features
~~~~~~~~

* Add a CDN instance node backed by a local instance database
  (!1975, 226820cb0). A passive, transparent audit pipeline runs
  alongside the existing slave deployment: each slave's parameters are
  validated against the JSON schema and the result (valid/invalid +
  errors) is stored in a local SQLite database that operators can query
  with sqlite-web. For custom domains it performs DNS domain-ownership
  verification (an HMAC ``_slapos-challenge`` TXT record), SSL
  certificate validation, and server-alias conflict detection, running
  periodically from crontab. No slave is rejected, blocked, or modified
  by this change — it is the audit-and-notify first step of a longer
  roadmap.
* Advertise HTTP/2 via ALPN on the HTTPS frontend when
  ``enable-http2-by-default`` is set (``h2,http/1.1,http/1.0``)
  (c28d7aa47).

Bug fixes
~~~~~~~~~

* Fix backend connection-drop on HTTP/2 and HTTP/3 clients: enable L7
  retries (``retry-on conn-failure empty-response response-timeout``) so
  a reused pool connection whose upstream closed mid-keepalive returns a
  clean 502 instead of silently aborting the client stream (92953c99f).
* Preserve the URL path in ``type=redirect`` ``Location`` responses; the
  redirect target now includes the configured path (fcc8f9ecf).
* Preserve a trailing slash in backend paths when a query string is
  present (06f1879ed).
* Escape ``%`` in backend request paths so encoded octets such as
  ``%20`` are no longer interpreted as haproxy format specifiers
  (73545ea74).
* Always emit a ``Date`` response header, applied in the frontend
  defaults including the not-found backend (c28d7aa47, fixup ad00a85c2).
* Add a ``Via`` response header on https-only redirects and on the
  not-found backend, and emit ``alt-svc``/``alternate-protocol`` on the
  not-found backend when HTTP/3 is enabled (c28d7aa47).

Parameters
~~~~~~~~~~

Migration notes when upgrading from 1.0.469:

* New cluster parameter ``instance-retention-delay`` (integer seconds,
  default ``7776000`` = 90 days; ``0`` means immediate removal). Controls
  how long a disappeared instance is retained before the instance node
  removes it (introduced 226820cb0, 90-day default 3f4a3e520).
* New frontend parameter ``monitor-interface-url`` (URI); previously
  present only on the cluster and kedifa schemas (40e3afe24).
* ``dns-nameserver`` now accepts a comma-separated list, and each entry
  may carry an explicit port (``ip:port`` or ``[ipv6]:port``; default
  port 53). A single host without a port stays valid, so existing values
  need no change (ed411f684).
* Default ``monitor-interface-url`` updated to
  ``https://monitor.app.officejs.com/#page=ojsm_landing`` on the cluster,
  frontend, and kedifa schemas (40e3afe24).
* The shared slave software types ``custom-personal-slave`` and
  ``default-slave`` now declare ``serialisation: xml``; the cluster
  itself keeps ``json-in-xml`` (5b0560583).

Dependencies
~~~~~~~~~~~~

* Version up kedifa 0.0.7 to 0.0.8 (85abd167a).
* Add sqlite-web 0.7.2 and peewee 3.19.0 for the instance-node audit
  database and its web UI (226820cb0, 21cc89d1e).
* Drop the explicit ``zc.lockfile`` 1.4 pin (85abd167a) and remove a
  duplicated ``zc.lockfile`` version (6a1fd04ae).

1.0.469 (2026-03-06)
--------------------

* Move instance parameters to ``slapconfiguration.jsonschema``
  (8871f2053, fixup 642c37dd8).
* Fix passing parameters to the frontend nodes (e650ac64e).
* Shared (slave) instances no longer send an error message on bad
  parameters (8f98bfe13).
* Drop unnecessary type casting in the kedifa instance (d5d7fe42e) and
  clean up the backend haproxy caucase variables (3018a6e6a).

1.0.464 (2026-02-05)
--------------------

* Move all JSON schemas to the latest draft version (707bc5b7b).
* Drop the reject-slave promise (492a0b5a4).
* Desensitize kedifa-related promises (fa1ddd659) and make promise
  errors more explanatory (d2228fda0).
* Improve operator information on clashed domains (5f96e7a89).
* Make curl-http3 the only curl build (6c4024552).

1.0.453 (2025-11-26)
--------------------

* Revert the "Fix inconsistency" change from 1.0.446 (931bc1191, reverts
  821e25303).

1.0.448 (2025-10-28)
--------------------

* Review TrafficServer timeouts (e1741564e).

1.0.446 (2025-10-21)
--------------------

* Implement TrafficServer inspection (8d93dbb76) and allow all verbs to
  pass via TrafficServer (014785e50).
* Switch the ``ip_allow`` configuration from config to YAML (1f250d9aa).
* Apply changed parameters with a service restart (8eff44b0b).
* Assure the ``Date`` response header is present and that the backend
  always adds the header (1fbcf18e0, edee1298f).
* Add a dedicated JSON schema for slave-only deployments (30a7e8995).
* Drop a no-longer-required parameter (31ff9e042).
* Fix an inconsistency (821e25303) — later reverted in 1.0.453.

1.0.427 (2025-07-24)
--------------------

* Use HTTP/1.0 for health checks (4c036fdc3).
* Harden handling of unusual parameter values (b6fa1f2f7).
* Simplify the log split (c62b16380) and minimize produced files
  (746f9ea50).

1.0.395 (2025-02-06)
--------------------

* Implement expert SSL downgrade (498e3ad1e).
* Drop dependence on ``slave-log-directory-dict`` (0a2e149f9).
* Version up OpenSSL to 1.1.1w-0+deb11u2 (46f5a6a1b).

1.0.377 (2024-11-21)
--------------------

* Earliest release covered by this changelog.
