Changes
=======

Here are listed the most important changes, which might affect upgrades.

1.0.XXX (XXXX-XX-XX)
--------------------

 * fix: exposed log file names are stabilised
 * feature: in case of not found instance more information are provided
 * feature: telemetry is fully disabled
 * feature: Apache Traffic Server 8.0 is used
 * feature: backend-haproxy statistic for haproxy's frontend is available
 * fix: slave publication has been fixed in case of mixed case slave reference
 * feature: running test/test.py resolves with starting backend used in tests
 * fix: automatic caucase-updater usage has been fixed
 * fix/workaround: reconnect to backend-haproxy from Caddy and Apache Traffic Server
 * fix/feature: use explicitly Apache Traffic Server simulation of stale-if-error, as in reality Apache Traffic Server does not support it
 * feature: dropped not used parameters
 * feature: Strict-Transport-Security aka HSTS
 * fix: use kedifa with with for file with multiple CAs
 * feature: support query string (the characters after ? in the url) in url and https-url
 * fix: by having unique acl names fix rare bug of directing traffic to https-url instead of url or otherwise
 * feature: failover backend

1.0.164 (2020-09-24)
--------------------

 * feature: serve a stale result up to 1 day if the origin server is down
 * feature: request real frontend for slave introspection (aka log access)
 * fix: Kedifa reloading, it was resulting with kedifa server disallowing access after some time
 * feature: allow to set software release for each node, instead for the whole cluster
 * fix: haproxy matches correct hostname in case of wildcards, instead of using wildcard host instead of the specific one

1.0.160 (2020-08-25)
--------------------

 * haproxy updated from 2.0.15 to 2.0.17 in order to fix issue while accessing inaccessible backends

1.0.159 (2020-07-30)
--------------------

 * logs are ensured to be available in slave's ``log-access-url``
 * logs from backend Haproxy are also available to slaves

1.0.158 (2020-07-24)
--------------------

 * manual customisation of profiles has been dropped, as not used, dropped keys are ``apache_custom_http``, ``apache_custom_https``, ``caddy_custom_http``, ``caddy_custom_https`` from slaves and ``-frontend-authorized-slave-string`` from master
 * ``re6st-optimal-test`` has been dropped from slave
 * QUIC is dropped, as was not used and has been superseded by HTTP/3, dropped key is ``enable-quic`` from master
 * haproxy is used as a gateway to backends:

   * ``automatic-internal-backend-client-caucase-csr`` switch for master is introduced to control it CSR signing
   * ``proxy-try-duration`` and ``proxy-try-interval`` has been dropped, as Caddy is not used anymore to connect to the backend, and instead ``backend-connect-timeout`` and ``backend-connect-retries`` is used, as it comes from Haproxy
   * ``backend-client-caucase-url`` is returned in master and slave, so that backends can use caucase to fetch CA from frontend cluster
   * ``request-timeout`` is supported per slave, as now it became possible
   * ``authenticate-to-backend`` is added for master and slave, defaulting to False, to have control over cluster default authentication, and make it possible to do it per slave

1.0.149 (2020-05-05)
--------------------

 * no changes noted
