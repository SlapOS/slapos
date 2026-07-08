===================
rapid-cdn Changelog
===================

A functional changelog for CDN operators (**[operator]**) and users
(**[user]**). Each entry targets a single audience; a change that
affects both is written as a separate **[operator]** entry and
**[user]** entry.

The changelog covers releases from 1.0.377 onward. rapid-cdn does not
use Semantic Versioning: it ships with the shared, monotonic SlapOS
``1.0.<n>`` release tags, and releases with no rapid-cdn change are
omitted.

Unreleased
--------------------

Changes on ``master`` since 1.0.469 (`compare <https://lab.nexedi.com/nexedi/slapos/-/compare/1.0.469...master>`__).

CDN instance node with a local audit database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

rapid-cdn now ships a CDN instance node: a passive audit layer that
validates every slave's parameters against the JSON schema and, for
custom domains, checks DNS domain-ownership, the SSL certificate, and
server-alias conflicts. Results are written to a local SQLite database
the operator browses through a new password-protected sqlite-web
interface, whose URL is published as
``publish-slave-sqlite-validation-database``. It runs from a per-minute
crontab with dedicated promises and its own ``cdn-instance-node.log``;
nothing is rejected yet.

Two new cluster parameters arrive with it. ``instance-retention-delay``
(integer seconds; default ``7776000`` = 90 days, ``0`` = remove
immediately) sets how long a disappeared instance is kept before the
node removes it. ``dns-nameserver`` now accepts a comma-separated list
in which each entry may pin an explicit resolver port (``ip:port`` or
``[ipv6]:port``, default 53) — a bare host still works unchanged.

(`!1975 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1975>`__, `226820cb0 <https://lab.nexedi.com/nexedi/slapos/-/commit/226820cb0>`__, `3f4a3e520 <https://lab.nexedi.com/nexedi/slapos/-/commit/3f4a3e520>`__, `ed411f684 <https://lab.nexedi.com/nexedi/slapos/-/commit/ed411f684>`__, `9d0974d2d <https://lab.nexedi.com/nexedi/slapos/-/commit/9d0974d2d>`__, `3c3899068 <https://lab.nexedi.com/nexedi/slapos/-/commit/3c3899068>`__)

Custom-domain slaves are now audited
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The new CDN instance node audits each slave's parameters. For custom
domains you will be asked to prove domain ownership by publishing a
``_slapos-challenge`` DNS TXT record; the SSL certificate and
server-alias conflicts are checked too. It is advisory for now — no
slave is rejected — and the outcome is currently visible only to
operators, not surfaced in your slave's published parameters
(``request-error-list`` / ``warning-list`` still come from the
pre-existing rejection flow).

(`!1975 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1975>`__, `226820cb0 <https://lab.nexedi.com/nexedi/slapos/-/commit/226820cb0>`__, `ed411f684 <https://lab.nexedi.com/nexedi/slapos/-/commit/ed411f684>`__)

Dedicated monitoring-interface URL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The cluster gained a dedicated ``monitor-interface-url`` parameter on
the frontend input schema (it already existed on the cluster and kedifa
schemas). Its default, on all three, was updated from
``https://monitor.app.officejs.com`` to
``https://monitor.app.officejs.com/#page=ojsm_landing``. (`40e3afe24 <https://lab.nexedi.com/nexedi/slapos/-/commit/40e3afe24>`__)

Explicit slave parameter serialisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

In ``software.cfg.json`` the shared slave software types
``custom-personal-slave`` and ``default-slave`` now declare
``serialisation: xml`` explicitly, while the cluster itself stays on
``json-in-xml``. (`5b0560583 <https://lab.nexedi.com/nexedi/slapos/-/commit/5b0560583>`__)

Slave parameters serialised as XML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Requests for the ``custom-personal`` and ``default`` slave types now
encode their parameters as XML (``serialisation: xml``) rather than
inheriting the cluster's ``json-in-xml``. (`5b0560583 <https://lab.nexedi.com/nexedi/slapos/-/commit/5b0560583>`__)

Response headers, redirects and HTTP/2 / HTTP/3 behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

Tag `1.0.469 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.469>`__.

Cluster boolean parameters became native JSON booleans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

**Breaking:** cluster parameters are now declared and validated through
``slapconfiguration.jsonschema``. The following boolean cluster
parameters became native JSON booleans (pass ``true`` / ``false``
instead of ``"true"`` / ``"false"``): ``authenticate-to-backend``,
``enable-http2-by-default``, ``enable-http3``,
``automatic-internal-backend-client-caucase-csr``, and
``automatic-internal-kedifa-caucase-csr``. (`8871f2053 <https://lab.nexedi.com/nexedi/slapos/-/commit/8871f2053>`__)

Slave boolean parameters no longer enum-constrained
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Slave parameters are now declared and validated through
``slapconfiguration.jsonschema``. The ``"true"`` / ``"false"`` enum
constraint was dropped from the boolean-style slave parameters (they
remain string-typed): ``authenticate-to-backend``,
``disable-via-header``, ``enable-http2``, ``enable-http3``,
``enable_cache``, ``health-check``,
``health-check-authenticate-to-failover-backend``,
``health-check-failover-ssl-proxy-verify``, ``https-only``,
``prefer-gzip-encoding-to-backend``, ``ssl-proxy-verify``,
``strict-transport-security-preload``, and
``strict-transport-security-sub-domains``. (`8871f2053 <https://lab.nexedi.com/nexedi/slapos/-/commit/8871f2053>`__)

Reliable parameter passing to frontend nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

Tag `1.0.464 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.464>`__.

Cluster JSON schemas upgraded to the latest draft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The cluster / master parameter schemas moved from JSON Schema
``draft-07`` to ``draft/2020-12`` (the ``$schema`` declaration).
Parameter names and meanings are unchanged, but validation tooling and
editor forms may behave differently. (`707bc5b7b <https://lab.nexedi.com/nexedi/slapos/-/commit/707bc5b7b>`__)

Slave JSON schemas upgraded to the latest draft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The slave parameter schemas moved from JSON Schema ``draft-07`` to
``draft/2020-12`` (the ``$schema`` declaration). Parameter names and
meanings are unchanged, but validation tooling and editor forms may
behave differently. (`707bc5b7b <https://lab.nexedi.com/nexedi/slapos/-/commit/707bc5b7b>`__)

1.0.446 (2025-10-21)
--------------------

Tag `1.0.446 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.446>`__.

Some parameter changes now restart the service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Because some Apache TrafficServer settings only take effect on restart,
changing the affected cluster parameters now triggers a TrafficServer
service restart. The ``request-timeout`` parameter (title "HTTP Request
timeout in seconds") is documented with this warning; expect a brief
service restart when you change it. (`8eff44b0b <https://lab.nexedi.com/nexedi/slapos/-/commit/8eff44b0b>`__)

1.0.427 (2025-07-24)
--------------------

Tag `1.0.427 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.427>`__.

Backend health checks fixed to HTTP/1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

**Breaking:** the per-slave ``health-check-http-version`` parameter (an enum of
``HTTP/1.1`` / ``HTTP/1.0``, default ``HTTP/1.1``) was removed, and
health checks now always use HTTP/1.0. rapid-cdn sends no Host header on
health-check requests, which HTTP/1.1 origins (e.g. nginx) answered with
status 400 — marking healthy backends as down. If you set
``health-check-http-version``, drop it: the parameter no longer exists.
(`4c036fdc3 <https://lab.nexedi.com/nexedi/slapos/-/commit/4c036fdc3>`__)
