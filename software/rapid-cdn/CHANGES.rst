===================
rapid-cdn Changelog
===================

A functional changelog for CDN operators (**[operator]**) and users
(**[user]**).

The changelog covers releases from 1.0.377 onward.

Unreleased
--------------------

CDN instance node with a local audit database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator, user]**

rapid-cdn now ships a CDN instance node that adds a passive, transparent
audit layer alongside the existing slave deployment: every slave's
parameters are validated against the JSON schema and the outcome
(valid/invalid, with the specific errors) is written to a local SQLite
database an operator can browse through a new password-protected
sqlite-web interface, whose URL is published as
``publish-slave-sqlite-validation-database``. For custom domains the
node also proves domain ownership (an HMAC ``_slapos-challenge`` DNS TXT
record), verifies the SSL certificate matches and is not expired, and
flags server-alias conflicts between slaves — all from a per-minute
crontab (with dedicated promises and its own ``cdn-instance-node.log``),
independently of the deployment cycle. Nothing is rejected or altered
yet; this is the audit-and-notify first step.

Two new cluster parameters arrive with it. ``instance-retention-delay``
(integer seconds; default ``7776000`` = 90 days, ``0`` = remove
immediately) sets how long a disappeared instance is kept before the
node removes it. ``dns-nameserver`` now accepts a comma-separated list
in which each entry may pin an explicit resolver port (``ip:port`` or
``[ipv6]:port``, default 53) — a bare host still works unchanged.

For users, custom-domain slaves are now subject to this audit: owners
will be asked to prove domain ownership by publishing a
``_slapos-challenge`` DNS TXT record. It stays advisory for now — no
slave is rejected — and the audit outcome is currently visible only to
operators (the local database), not surfaced in the slave's own
published parameters (``request-error-list`` / ``warning-list`` still
come from the pre-existing rejection flow).

(`!1975 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1975>`__, `226820cb0 <https://lab.nexedi.com/nexedi/slapos/-/commit/226820cb0>`__, `3f4a3e520 <https://lab.nexedi.com/nexedi/slapos/-/commit/3f4a3e520>`__, `ed411f684 <https://lab.nexedi.com/nexedi/slapos/-/commit/ed411f684>`__, `9d0974d2d <https://lab.nexedi.com/nexedi/slapos/-/commit/9d0974d2d>`__, `3c3899068 <https://lab.nexedi.com/nexedi/slapos/-/commit/3c3899068>`__)

Dedicated monitoring-interface URL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The cluster gained a dedicated ``monitor-interface-url`` parameter on
the frontend input schema (it already existed on the cluster and kedifa
schemas). Its default, on all three, was updated from
``https://monitor.app.officejs.com`` to
``https://monitor.app.officejs.com/#page=ojsm_landing``. (`40e3afe24 <https://lab.nexedi.com/nexedi/slapos/-/commit/40e3afe24>`__)

Explicit slave parameter serialisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator, user]**

In ``software.cfg.json`` the shared slave software types
``custom-personal-slave`` and ``default-slave`` now declare
``serialisation: xml`` explicitly, while the cluster itself stays on
``json-in-xml``. This governs how slave request parameters are encoded.
(`5b0560583 <https://lab.nexedi.com/nexedi/slapos/-/commit/5b0560583>`__)

Response headers, redirects and HTTP/2 / HTTP/3 behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Several changes affect how the CDN serves slave sites. Response headers:
the ``Date`` header is always emitted, a ``Via`` header is added on
https-only redirects and on the not-found backend, HTTP/2 is advertised
via ALPN (when ``enable-http2-by-default`` is set), and an HTTP/3
``alt-svc`` is advertised on the not-found backend. Redirects of
``type=redirect`` now preserve the backend path in the ``Location``
response; a trailing slash is kept when a query string is present; and
``%`` is escaped in backend request paths so encoded octets such as
``%20`` are handled correctly. Backend connection-drops on HTTP/2 and
HTTP/3 clients are fixed with haproxy L7 retries, returning a clean 502
instead of aborting the client stream.

(`c28d7aa47 <https://lab.nexedi.com/nexedi/slapos/-/commit/c28d7aa47>`__, `fcc8f9ecf <https://lab.nexedi.com/nexedi/slapos/-/commit/fcc8f9ecf>`__, `06f1879ed <https://lab.nexedi.com/nexedi/slapos/-/commit/06f1879ed>`__, `73545ea74 <https://lab.nexedi.com/nexedi/slapos/-/commit/73545ea74>`__, `92953c99f <https://lab.nexedi.com/nexedi/slapos/-/commit/92953c99f>`__)

1.0.469 (2026-03-06)
--------------------

Boolean parameters migrated to slapconfiguration.jsonschema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator, user]**

Cluster and slave parameters are now declared and validated through
``slapconfiguration.jsonschema``. As part of this, boolean-style
parameters that were previously typed as the string enum ``"true"`` /
``"false"`` were reworked.

For operators, the following cluster parameters became native JSON
booleans (pass ``true`` / ``false`` instead of ``"true"`` / ``"false"``):
``authenticate-to-backend``, ``enable-http2-by-default``,
``enable-http3``, ``automatic-internal-backend-client-caucase-csr``, and
``automatic-internal-kedifa-caucase-csr``.

For users, the ``"true"`` / ``"false"`` enum constraint was dropped from
the boolean-style slave parameters (they remain string-typed):
``authenticate-to-backend``, ``disable-via-header``, ``enable-http2``,
``enable-http3``, ``enable_cache``, ``health-check``,
``health-check-authenticate-to-failover-backend``,
``health-check-failover-ssl-proxy-verify``, ``https-only``,
``prefer-gzip-encoding-to-backend``, ``ssl-proxy-verify``,
``strict-transport-security-preload``, and
``strict-transport-security-sub-domains``. (`8871f2053 <https://lab.nexedi.com/nexedi/slapos/-/commit/8871f2053>`__)

Reliable parameter passing to frontend nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The indexed per-frontend parameter, previously restricted to
``-frontend-config-N-ram-cache-size``, was generalised to
``-frontend-config-N-<key>`` (pattern ``^-frontend-config-[0-9]+-.+$``).
Operators can now pass any per-frontend config key through to a specific
frontend node (for example ``ram-cache-size`` or
``expert-backend-allow-downgrade-ssl``), not only the RAM cache size.
(`e650ac64e <https://lab.nexedi.com/nexedi/slapos/-/commit/e650ac64e>`__)

1.0.464 (2026-02-05)
--------------------

JSON schemas upgraded to the latest draft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator, user]**

All parameter schemas were moved from JSON Schema ``draft-07`` to
``draft/2020-12`` (the ``$schema`` declaration). Parameter names and
meanings are unchanged, but validation tooling and editor forms may
behave differently. (`707bc5b7b <https://lab.nexedi.com/nexedi/slapos/-/commit/707bc5b7b>`__)

1.0.446 (2025-10-21)
--------------------

Some parameter changes now restart the service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Because some Apache TrafficServer settings only take effect on restart,
changing the affected cluster parameters now triggers a TrafficServer
service restart. The ``request-timeout`` parameter (title "HTTP Request
timeout in seconds") is documented with this warning; expect a brief
service restart when you change it. (`8eff44b0b <https://lab.nexedi.com/nexedi/slapos/-/commit/8eff44b0b>`__)

1.0.427 (2025-07-24)
--------------------

Backend health checks fixed to HTTP/1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The per-slave ``health-check-http-version`` parameter (an enum of
``HTTP/1.1`` / ``HTTP/1.0``, default ``HTTP/1.1``) was removed, and
health checks now always use HTTP/1.0. rapid-cdn sends no Host header on
health-check requests, which HTTP/1.1 origins (e.g. nginx) answered with
status 400 — marking healthy backends as down. If you set
``health-check-http-version``, drop it: the parameter no longer exists.
(`4c036fdc3 <https://lab.nexedi.com/nexedi/slapos/-/commit/4c036fdc3>`__)
