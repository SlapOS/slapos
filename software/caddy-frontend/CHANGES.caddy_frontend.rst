Changes
=======

Here are listed the most important changes, which might affect upgrades.

1.0.XXX XXXX-XX-XX
------------------

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
