===================
rapid-cdn Changelog
===================

A functional changelog for CDN operators (**[operator]**) and users
(**[user]**). Each entry targets a single audience; a change that
affects both is written as a separate **[operator]** entry and
**[user]** entry.

Releases
========

.. contents::
   :local:
   :depth: 1
   :backlinks: none

Unreleased
--------------------

Changes on ``master`` since 1.0.469 (`compare <https://lab.nexedi.com/nexedi/slapos/-/compare/1.0.469...master>`__).

Error Page Manager software type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The Software Release now exposes a new ``error-page-manager``
software type, allocated automatically as an additional partition of
each rapid-cdn cluster. The cluster publishes
``error-page-manager-operator-url`` for cluster-wide error-page
overrides. See ``README.rst`` for details. (`!1958 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1958>`__)

Per-site custom error pages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Each shared instance now receives ``shared-error-page-information``,
a new published parameter carrying a per-slave ``upload-url`` for
custom 502/503/504 pages. See ``README.rst`` for the upload API and
web UI. (`!1958 <https://lab.nexedi.com/nexedi/slapos/-/merge_requests/1958>`__)

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

Tag `1.0.453 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.453>`__.

Backend empty-path behaviour restored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Reverts the 1.0.446 change: an empty backend path is again forwarded as
an empty string, not as ``/``. (`931bc1191 <https://lab.nexedi.com/nexedi/slapos/-/commit/931bc1191>`__)

1.0.448 (2025-10-28)
--------------------

Tag `1.0.448 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.448>`__.

TrafficServer connection and transfer timeouts extended
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Apache TrafficServer timeouts were greatly extended to permit long-lived
connections and streams: keep-alive 120s → 3600s, active transaction
900s → 2 days, and the no-activity / net-inactivity timeouts likewise.
(`e1741564e <https://lab.nexedi.com/nexedi/slapos/-/commit/e1741564e>`__)

1.0.446 (2025-10-21)
--------------------

Tag `1.0.446 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.446>`__.

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

Its default is now empty, and the re6st connectivity promise is installed
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

First rapid-cdn release. Between caddy-frontend
1.0.298 and this release the frontend / TLS terminator was rewritten
from Caddy to HAProxy (the backend was already HAProxy) and the Software
Release was renamed ``caddy-frontend`` → ``rapid-cdn`` — both landed at
tag 1.0.299. (`643457a37 <https://lab.nexedi.com/nexedi/slapos/-/commit/643457a37>`__)

Slave sites served through HAProxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

From this release slave sites are served by HAProxy instead of Caddy;
response and redirect behaviour follows HAProxy semantics onward.

1.0.298 (2023-01-09, caddy-frontend)
------------------------------------

Tag `1.0.298 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.298>`__. Last caddy-frontend release before the rename to rapid-cdn.

Per-frontend cache sizing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

New cluster parameters ``ram-cache-size`` and ``disk-cache-size`` size
the Apache TrafficServer cache; the ``global-disable-http2`` switch was
dropped. (`81c528e13 <https://lab.nexedi.com/nexedi/slapos/-/commit/81c528e13>`__, `4141b8118 <https://lab.nexedi.com/nexedi/slapos/-/commit/4141b8118>`__)

Master Introspection Frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

A new password-protected Master Introspection Frontend exposes cluster
internals to operators, and the published node values were renamed
``caddy-frontend-N-*`` → ``frontend-node-N-*``. (`7498ab60f <https://lab.nexedi.com/nexedi/slapos/-/commit/7498ab60f>`__, `0a0bb6cbb <https://lab.nexedi.com/nexedi/slapos/-/commit/0a0bb6cbb>`__)

Parameter schema files renamed to stable names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The parameter schemas were renamed to their generic names —
``instance-caddy-input-schema.json`` → ``instance-input-schema.json``
and ``instance-slave-caddy-input-schema.json`` →
``instance-slave-input-schema.json`` — carrying the same parameters.
(`419df6b78 <https://lab.nexedi.com/nexedi/slapos/-/commit/419df6b78>`__)

Failover URL cached; simplified slave schema retired
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The failover URL is now covered by the cache, and the separate
"simplified" slave request schema
(``instance-slave-caddy-simplified-input-schema.json``) was removed —
use the standard slave schema. (`238008f62 <https://lab.nexedi.com/nexedi/slapos/-/commit/238008f62>`__, `419df6b78 <https://lab.nexedi.com/nexedi/slapos/-/commit/419df6b78>`__)

1.0.266 (2022-08-22, caddy-frontend)
------------------------------------

Tag `1.0.266 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.266>`__.

Header handling on HTTPS backends and HTTP/2 endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The backend ``Via`` header is fixed for HTTPS backends, and ALPN
(HTTP/2) is now set on the special endpoints too. (`87bac5c07 <https://lab.nexedi.com/nexedi/slapos/-/commit/87bac5c07>`__, `0ee8f7bea <https://lab.nexedi.com/nexedi/slapos/-/commit/0ee8f7bea>`__)

Kedifa auth-generation promise
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

A new promise checks Kedifa authentication generation. (`7f26a9ace <https://lab.nexedi.com/nexedi/slapos/-/commit/7f26a9ace>`__)

1.0.240 (2022-04-07, caddy-frontend)
------------------------------------

Tag `1.0.240 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.240>`__.

Backend netloc lists and hostname handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

New slave parameters ``url-netloc-list``, ``https-url-netloc-list``,
``health-check-failover-url-netloc-list`` and
``health-check-failover-https-url-netloc-list`` let a backend be
addressed by an explicit set of netlocs; backends whose hostname does
not resolve are now supported; the ``Via`` header was improved and the
origin ``Server`` header is kept intact; a double-slash bug for
``type:zope`` was fixed. (`a9d98dd18 <https://lab.nexedi.com/nexedi/slapos/-/commit/a9d98dd18>`__, `14d90bcdc <https://lab.nexedi.com/nexedi/slapos/-/commit/14d90bcdc>`__, `d45e9cdf1 <https://lab.nexedi.com/nexedi/slapos/-/commit/d45e9cdf1>`__, `3d6af70d1 <https://lab.nexedi.com/nexedi/slapos/-/commit/3d6af70d1>`__, `8e03e8309 <https://lab.nexedi.com/nexedi/slapos/-/commit/8e03e8309>`__)

1.0.207 (2021-09-13, caddy-frontend)
------------------------------------

Tag `1.0.207 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.207>`__.

eventsource frontend type removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

The ``eventsource`` slave ``type`` was removed. (`db4d05e51 <https://lab.nexedi.com/nexedi/slapos/-/commit/db4d05e51>`__)

1.0.201 (2021-06-15, caddy-frontend)
------------------------------------

Tag `1.0.201 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.201>`__.

Backend health checks and failover
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

A full backend health-check suite was added — ``health-check`` plus
``health-check-http-method`` / ``-http-path`` / ``-http-version`` /
``-timeout`` / ``-interval`` / ``-rise`` / ``-fall`` — together with a
failover backend (``health-check-failover-url`` and the
``health-check-failover-*`` family). (`20c1b3262 <https://lab.nexedi.com/nexedi/slapos/-/commit/20c1b3262>`__, `482463e47 <https://lab.nexedi.com/nexedi/slapos/-/commit/482463e47>`__)

HTTP Strict-Transport-Security (HSTS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

New slave parameters ``strict-transport-security``,
``strict-transport-security-sub-domains`` and
``strict-transport-security-preload``. (`b71cf56ed <https://lab.nexedi.com/nexedi/slapos/-/commit/b71cf56ed>`__)

Query string supported in the backend URL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

``url`` and ``https-url`` now support a query string (the characters
after ``?``). (`1593304e7 <https://lab.nexedi.com/nexedi/slapos/-/commit/1593304e7>`__)

Unused cluster parameters dropped
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The unused cluster parameters ``nginx-domain``, ``public-ipv4`` and
``private-ipv4`` were removed. (`3d0cc5e8d <https://lab.nexedi.com/nexedi/slapos/-/commit/3d0cc5e8d>`__)

1.0.164 (2020-09-24, caddy-frontend)
------------------------------------

Tag `1.0.164 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.164>`__.

Serve stale content when the origin is down
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

A stale cached result is served for up to one day when the origin
server is unreachable, and wildcard-domain slaves now match the correct
hostname. (`865bc5d47 <https://lab.nexedi.com/nexedi/slapos/-/commit/865bc5d47>`__, `65c9c4cb6 <https://lab.nexedi.com/nexedi/slapos/-/commit/65c9c4cb6>`__)

Per-node software release and slave introspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

The software release can be set per node instead of for the whole
cluster; slave introspection (log access) now goes through the real
frontend; and a Kedifa reloading bug (access denied after a while) was
fixed. (`4865135af <https://lab.nexedi.com/nexedi/slapos/-/commit/4865135af>`__, `3373e99d6 <https://lab.nexedi.com/nexedi/slapos/-/commit/3373e99d6>`__, `6c8432334 <https://lab.nexedi.com/nexedi/slapos/-/commit/6c8432334>`__)

1.0.160 (2020-08-25, caddy-frontend)
------------------------------------

Tag `1.0.160 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.160>`__.

Backend access reliability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

haproxy was updated (2.0.15 → 2.0.17) to fix an issue accessing
unavailable backends.

1.0.159 (2020-07-30, caddy-frontend)
------------------------------------

Tag `1.0.159 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.159>`__.

Frontend and backend logs available to slaves
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

Logs are ensured available in the slave's ``log-access-url``, and the
backend HAProxy logs are also made available to slaves. (`657002847 <https://lab.nexedi.com/nexedi/slapos/-/commit/657002847>`__, `a4a2555b9 <https://lab.nexedi.com/nexedi/slapos/-/commit/a4a2555b9>`__)

1.0.158 (2020-07-24, caddy-frontend)
------------------------------------

Tag `1.0.158 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.158>`__.

HAProxy is the gateway to backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[operator]**

HAProxy is now used as the gateway to backends (Caddy no longer connects
to the backend): ``proxy-try-duration`` / ``proxy-try-interval`` were
dropped in favour of ``backend-connect-timeout`` /
``backend-connect-retries``; ``automatic-internal-backend-client-caucase-csr``
controls backend-client CSR signing; and ``backend-client-caucase-url``
is returned so backends can fetch the cluster CA. QUIC was dropped
(``enable-quic`` removed) in favour of HTTP/3, and the unused
``-frontend-authorized-slave-string`` master parameter was removed.
(`ec3d4ae9d <https://lab.nexedi.com/nexedi/slapos/-/commit/ec3d4ae9d>`__, `3be5f4ce0 <https://lab.nexedi.com/nexedi/slapos/-/commit/3be5f4ce0>`__, `5b024d04f <https://lab.nexedi.com/nexedi/slapos/-/commit/5b024d04f>`__)

Per-slave backend controls and stricter URL validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**[user]**

``request-timeout`` and ``authenticate-to-backend`` (default ``false``)
became per-slave. Backend ``url`` / ``https-url`` validation is
stricter: empty values are rejected and whitespace is supported. The
unused manual-customisation slave keys (``apache_custom_http`` /
``apache_custom_https`` / ``caddy_custom_http`` / ``caddy_custom_https``)
and ``re6st-optimal-test`` were removed. (`cf57840de <https://lab.nexedi.com/nexedi/slapos/-/commit/cf57840de>`__, `2c4227e23 <https://lab.nexedi.com/nexedi/slapos/-/commit/2c4227e23>`__, `409a68232 <https://lab.nexedi.com/nexedi/slapos/-/commit/409a68232>`__)

1.0.149 (2020-05-05, caddy-frontend)
------------------------------------

Tag `1.0.149 <https://lab.nexedi.com/nexedi/slapos/-/tags/1.0.149>`__.

Earliest release covered
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the earliest release in this changelog. The Software Release
descends from **apache-frontend** (the original, from 2012):
caddy-frontend began in 2018 as a copy of apache-frontend, which was
obsoleted in 2020. apache-frontend kept no changelog of its own.
