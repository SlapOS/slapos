===================
rapid-cdn Changelog
===================

A functional changelog for CDN operators (**[operator]**) and users
(**[user]**). Each entry targets a single audience; a change that
affects both is written as a separate **[operator]** entry and
**[user]** entry.

The changelog covers the rapid-cdn Software Release from its first
deployed release, 1.0.309 (renamed from ``caddy-frontend``; the
Caddy-to-HAProxy frontend rewrite landed just before, at 1.0.299).
rapid-cdn does not use Semantic Versioning: it ships with the shared,
monotonic SlapOS ``1.0.<n>`` release tags. Every tag that reached the
clusters is listed — including ones later cancelled or reverted, marked
as such, since they are part of the history; only tags with no rapid-cdn
change are omitted.

.. contents:: Releases
   :depth: 1
   :backlinks: none

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
crontab with dedicated promises and its own ``cdn-instance-node.log``.
It is entirely operator-facing for now: nothing is rejected, and nothing
is published or surfaced to slaves/users — operators act on the audit
results manually (automated user notification and enforcement are later
steps).

Two new cluster parameters arrive with it. ``instance-retention-delay``
(integer seconds; default ``7776000`` = 90 days, ``0`` = remove
immediately) sets how long a disappeared instance is kept before the
node removes it. ``dns-nameserver`` now accepts a comma-separated list
in which each entry may pin an explicit resolver port (``ip:port`` or
``[ipv6]:port``, default 53) — a bare host still works unchanged.

(`!1975 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1975>`__, `226820cb0 <https://lab.nexedi.com/nexedi/slapos/-/commit/226820cb0>`__, `3f4a3e520 <https://lab.nexedi.com/nexedi/slapos/-/commit/3f4a3e520>`__, `ed411f684 <https://lab.nexedi.com/nexedi/slapos/-/commit/ed411f684>`__, `9d0974d2d <https://lab.nexedi.com/nexedi/slapos/-/commit/9d0974d2d>`__, `3c3899068 <https://lab.nexedi.com/nexedi/slapos/-/commit/3c3899068>`__)

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

Cluster parameters formalised via slapconfiguration.jsonschema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

**Breaking:** cluster parameters are now declared and validated through
``slapconfiguration.jsonschema``. Boolean cluster parameters became
native JSON booleans — pass ``true`` / ``false``, not ``"true"`` /
``"false"`` (``authenticate-to-backend``, ``enable-http2-by-default``,
``enable-http3``, ``automatic-internal-backend-client-caucase-csr``,
``automatic-internal-kedifa-caucase-csr``). Unknown cluster parameters
are now rejected (``additionalProperties: false``). New software types
``single-custom-personal`` and ``kedifa`` are offered, with new frontend
and kedifa input schemas. (`8871f2053 <https://lab.nexedi.com/nexedi/slapos/-/commit/8871f2053>`__)

Slave parameter validation formalised
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Slave parameters are now validated through
``slapconfiguration.jsonschema``. Boolean-style slave parameters now
accept case-insensitive ``yes`` / ``no`` / ``y`` / ``n`` / ``1`` / ``0``
/ ``true`` / ``false`` (previously only ``"true"`` / ``"false"``). URL,
path and ``websocket-path-list`` patterns were tightened and numeric
bounds / integer defaults were added across the slave schema.
(`8871f2053 <https://lab.nexedi.com/nexedi/slapos/-/commit/8871f2053>`__)

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

The cluster input and output schemas moved to JSON Schema
``draft/2020-12`` (from ``draft-07`` and ``draft-04`` respectively).
Parameter names and meanings are unchanged, but validation tooling and
editor forms may behave differently. (`707bc5b7b <https://lab.nexedi.com/nexedi/slapos/-/commit/707bc5b7b>`__)

Slave JSON schemas upgraded to the latest draft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The slave input and output schemas moved to JSON Schema
``draft/2020-12``. Parameter names and meanings are unchanged.
(`707bc5b7b <https://lab.nexedi.com/nexedi/slapos/-/commit/707bc5b7b>`__)

Operator promises and monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The reject-slave promise was dropped — a rejected slave no longer raises
a cluster anomaly, it stays listed at ``rejected-slave-url``. The
clashed-domain promise now lists the conflicting slaves. Kedifa-related
promises were desensitised (they retry before alarming, so the instance
keeps processing). A slave-list promise error message was made clearer.
(`492a0b5a4 <https://lab.nexedi.com/nexedi/slapos/-/commit/492a0b5a4>`__, `5f96e7a89 <https://lab.nexedi.com/nexedi/slapos/-/commit/5f96e7a89>`__, `fa1ddd659 <https://lab.nexedi.com/nexedi/slapos/-/commit/fa1ddd659>`__, `d2228fda0 <https://lab.nexedi.com/nexedi/slapos/-/commit/d2228fda0>`__)

1.0.453 (2025-11-26)
--------------------

Tag `1.0.453 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.453>`__. Deployed.

Backend empty-path behaviour restored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Reverts the 1.0.446 change: an empty backend path is again forwarded as
an empty string, not as ``/``. (`931bc1191 <https://lab.nexedi.com/nexedi/slapos/-/commit/931bc1191>`__)

1.0.448 (2025-10-28)
--------------------

Tag `1.0.448 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.448>`__. Deployed, then reverted from the clusters.

TrafficServer connection and transfer timeouts extended
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Apache TrafficServer timeouts were greatly extended to permit long-lived
connections and streams: keep-alive 120s → 3600s, active transaction
900s → 2 days, and the no-activity / net-inactivity timeouts likewise.
(`e1741564e <https://lab.nexedi.com/nexedi/slapos/-/commit/e1741564e>`__)

1.0.446 (2025-10-21)
--------------------

Tag `1.0.446 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.446>`__. Cancelled — never deployed.

request-timeout changes now restart the service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Because some Apache TrafficServer settings only take effect on restart,
changing the affected cluster parameters now triggers a TrafficServer
service restart. The ``request-timeout`` parameter title documents this;
expect a brief service restart when you change it. (`8eff44b0b <https://lab.nexedi.com/nexedi/slapos/-/commit/8eff44b0b>`__)

TrafficServer inspection interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

A basic-auth-protected per-frontend
``frontend-node-N-trafficserver-introspection-url`` is published,
exposing the ATS Cache / HostDB / HTTP / NET inspectors. (`8d93dbb76 <https://lab.nexedi.com/nexedi/slapos/-/commit/8d93dbb76>`__)

Slave-only software type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

A new ``software_slave_only.cfg.json`` offers a node that exposes only
the slave request schema. (`30a7e8995 <https://lab.nexedi.com/nexedi/slapos/-/commit/30a7e8995>`__)

Date response header assured
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The backend now sets a ``Date`` response header when the origin omits
one, and ``Date`` / ``Via`` are emitted on all responses, including
haproxy-generated ones. (`1fbcf18e0 <https://lab.nexedi.com/nexedi/slapos/-/commit/1fbcf18e0>`__, `edee1298f <https://lab.nexedi.com/nexedi/slapos/-/commit/edee1298f>`__)

All HTTP verbs pass through TrafficServer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Apache TrafficServer now allows all HTTP verbs; previously PURGE, PUSH,
DELETE and TRACE were denied. (`014785e50 <https://lab.nexedi.com/nexedi/slapos/-/commit/014785e50>`__)

Backend empty path forwarded as slash
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

An empty backend path is forwarded as ``/``. (Later reverted in
1.0.453.) (`821e25303 <https://lab.nexedi.com/nexedi/slapos/-/commit/821e25303>`__)

1.0.427 (2025-07-24)
--------------------

Tag `1.0.427 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.427>`__.

Backend health checks fixed to HTTP/1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

**Breaking:** the per-slave ``health-check-http-version`` parameter (an
enum of ``HTTP/1.1`` / ``HTTP/1.0``, default ``HTTP/1.1``) was removed,
and health checks now always use HTTP/1.0. rapid-cdn sends no Host header
on health-check requests, which HTTP/1.1 origins (e.g. nginx) answered
with status 400 — marking healthy backends as down. If you set
``health-check-http-version``, drop it: the parameter no longer exists.
(`4c036fdc3 <https://lab.nexedi.com/nexedi/slapos/-/commit/4c036fdc3>`__)

1.0.395 (2025-02-06)
--------------------

Tag `1.0.395 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.395>`__.

Expert SSL downgrade to the backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

A new master parameter ``expert-backend-allow-downgrade-ssl`` (default
``false``, requires a node restart) re-enables legacy OpenSSL ciphers
when negotiating SSL to origins that cannot present a modern
certificate. It is documented in the README and is not part of the input
schema. (`498e3ad1e <https://lab.nexedi.com/nexedi/slapos/-/commit/498e3ad1e>`__)

1.0.377 (2024-11-21)
--------------------

Tag `1.0.377 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.377>`__.

Default software type is now ``default``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Requesting the frontend master without an explicit software type now
resolves to ``default``; the old ``RootSoftwareInstance`` request still
works. (`54ff69a8d <https://lab.nexedi.com/nexedi/slapos/-/commit/54ff69a8d>`__)

re6st-verification-url is now optional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Its default is now empty, and the re6st connectivity promise is deployed
only when the parameter is set. (`895dd80c1 <https://lab.nexedi.com/nexedi/slapos/-/commit/895dd80c1>`__)

Logging improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

Apache TrafficServer access-log retention now follows ``rotate-num``
(default raised from 365 to 4000 days), and long request lines are no
longer truncated in the haproxy logs. (`5b2556a13 <https://lab.nexedi.com/nexedi/slapos/-/commit/5b2556a13>`__, `ea0da24ac <https://lab.nexedi.com/nexedi/slapos/-/commit/ea0da24ac>`__)

Cluster domain validated as idn-hostname
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The cluster ``domain`` parameter is validated as ``idn-hostname``
(accepting internationalised names) instead of a restrictive regex.
(`113361909 <https://lab.nexedi.com/nexedi/slapos/-/commit/113361909>`__)

Custom domain validated as idn-hostname
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The slave ``custom_domain`` parameter is validated as ``idn-hostname``
instead of a restrictive regex. (`113361909 <https://lab.nexedi.com/nexedi/slapos/-/commit/113361909>`__)

Redirects fixed for standard ports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

``type=redirect`` no longer appends the standard port (80 / 443) to the
``Location``. (`a0d10c844 <https://lab.nexedi.com/nexedi/slapos/-/commit/a0d10c844>`__)

1.0.344 (2023-11-03)
--------------------

Tag `1.0.344 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.344>`__.

Backend path, wildcard-domain and websocket fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

No needless trailing slash is sent to the backend; wildcard domains are
handled correctly; and ``websocket-path-list`` is hardened against
invalid values. (`45c2762dd <https://lab.nexedi.com/nexedi/slapos/-/commit/45c2762dd>`__, `a039c8cf1 <https://lab.nexedi.com/nexedi/slapos/-/commit/a039c8cf1>`__, `7b5b19676 <https://lab.nexedi.com/nexedi/slapos/-/commit/7b5b19676>`__)

1.0.319 (2023-04-24)
--------------------

Tag `1.0.319 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.319>`__.

HTTP/3 support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

HTTP/3 becomes a first-class citizen, with new cluster parameters
``enable-http3`` and ``http3-port``. (`e8faa79ff <https://lab.nexedi.com/nexedi/slapos/-/commit/e8faa79ff>`__)

HTTP/3 per slave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

New slave parameter ``enable-http3`` serves a slave over HTTP/3.
(`e8faa79ff <https://lab.nexedi.com/nexedi/slapos/-/commit/e8faa79ff>`__)

Per-slave frontend log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The frontend HAProxy log is split out from the access log and made
available per slave. (`cde4559a7 <https://lab.nexedi.com/nexedi/slapos/-/commit/cde4559a7>`__)

1.0.309 (2023-02-20)
--------------------

Tag `1.0.309 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.309>`__.

Renamed from caddy-frontend; frontend rewritten Caddy to HAProxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

First rapid-cdn release deployed to the CDN. Between caddy-frontend
1.0.298 and this release the frontend / TLS terminator was rewritten
from Caddy to HAProxy (the backend was already HAProxy) and the Software
Release was renamed ``caddy-frontend`` → ``rapid-cdn`` — both landed at
tag 1.0.299. (`643457a37 <https://lab.nexedi.com/nexedi/slapos/-/commit/643457a37>`__)

Slave sites served through HAProxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

From this release slave sites are served by HAProxy instead of Caddy;
response and redirect behaviour follows HAProxy semantics onward.
