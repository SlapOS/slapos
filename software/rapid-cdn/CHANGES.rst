===================
rapid-cdn Changelog
===================

Unreleased
----------

Net changes since the last release (1.0.469), not yet part of a tagged
release. Entries describe the current state of the software release, not
its intermediate commit history.

Features
~~~~~~~~

* Add a CDN instance node backed by a local instance database (!1975).
  A passive, transparent audit pipeline runs alongside the existing
  slave deployment: each slave's parameters are validated against the
  JSON schema and the result (valid/invalid + errors) is stored in a
  local SQLite database that operators can query with sqlite-web. For
  custom domains it performs DNS domain-ownership verification (an HMAC
  ``_slapos-challenge`` TXT record), SSL certificate validation, and
  server-alias conflict detection, running periodically from crontab.
  No slave is rejected, blocked, or modified by this change — it is the
  audit-and-notify first step of a longer roadmap.
* Advertise HTTP/2 via ALPN on the HTTPS frontend when
  ``enable-http2-by-default`` is set (``h2,http/1.1,http/1.0``).

Bug fixes
~~~~~~~~~

* Fix backend connection-drop on HTTP/2 and HTTP/3 clients: enable L7
  retries (``retry-on conn-failure empty-response response-timeout``) so
  a reused pool connection whose upstream closed mid-keepalive returns a
  clean 502 instead of silently aborting the client stream.
* Preserve the URL path in ``type=redirect`` ``Location`` responses; the
  redirect target now includes the configured path.
* Preserve a trailing slash in backend paths when a query string is
  present.
* Escape ``%`` in backend request paths so encoded octets such as
  ``%20`` are no longer interpreted as haproxy format specifiers.
* Always emit a ``Date`` response header (applied in the frontend
  defaults, including the not-found backend).
* Add a ``Via`` response header on https-only redirects and on the
  not-found backend, and emit ``alt-svc``/``alternate-protocol`` on the
  not-found backend when HTTP/3 is enabled.

Parameters
~~~~~~~~~~

Migration notes when upgrading from 1.0.469:

* New cluster parameter ``instance-retention-delay`` (integer seconds,
  default ``7776000`` = 90 days; ``0`` means immediate removal). Controls
  how long a disappeared instance is retained before the instance node
  removes it.
* New frontend parameter ``monitor-interface-url`` (URI); previously
  present only on the cluster and kedifa schemas.
* ``dns-nameserver`` now accepts a comma-separated list, and each entry
  may carry an explicit port (``ip:port`` or ``[ipv6]:port``; default
  port 53). A single host without a port stays valid, so existing values
  need no change.
* Default ``monitor-interface-url`` updated to
  ``https://monitor.app.officejs.com/#page=ojsm_landing`` (cluster,
  frontend, and kedifa schemas).
* The shared slave software types ``custom-personal-slave`` and
  ``default-slave`` now declare ``serialisation: xml``; the cluster
  itself keeps ``json-in-xml``.

Dependencies
~~~~~~~~~~~~

* Version up kedifa 0.0.7 to 0.0.8.
* Add sqlite-web 0.7.2 and peewee 3.19.0 for the instance-node audit
  database and its web UI.
* Drop the explicit ``zc.lockfile`` 1.4 pin.
