Generally things to be done with ``caddy-frontend``:

 * ``apache-ca-certificate`` shall be merged with ``apache-certificate``
 * (new) ``type:websocket`` slave
 * ``type:eventsource`` https://lab.nexedi.com/nexedi/slapos/merge_requests/312#note_58483
 * ``ssl_ca_crt``
 * ``prefer-gzip-encoding-to-backend`` (requires writing middleware plugin for Caddy)
 * ``disabled-cookie-list`` (requires writing middleware plugin for Caddy)
 * ``ssl_proxy_ca_crt`` for ``ssl_proxy_verify``, this is related to bug https://github.com/mholt/caddy/issues/1550, proposed solution `just adding your CA to the system's trust store`
 * ``check-error-on-caddy-log`` like ``check-error-on-apache-log``
 * cover test suite like resilient tests for KVM and prove it works the same way as Caddy
 * make beautiful (eg. with whitespaces and nice comments) generated files (mostly Jinja2)
 * have ``caddy-frontend`` specific parameters, with backward compatibility to ``apache-frontend`` ones (like ``apache_custom_http`` --> ``caddy_custom_http``)
 * change ``switch-softwaretype`` to way how ``software/erp5`` does, which will help with dropping jinja2 template for ``caddy-wrapper``, which is workaround for current situation https://lab.nexedi.com/nexedi/slapos/merge_requests/312#note_62678
 * use `slapos!326 <https://lab.nexedi.com/nexedi/slapos/merge_requests/326>`_ instead of self-developed graceful restart scripts
 * move out `test/utils.py` and use it from shared python distribution

Things which can't be implemented:

 * use certificates valid forever in tests using `cryptography <https://pypi.org/project/cryptography/>`_, with `available example <https://lab.nexedi.com/nexedi/caucase/blob/1c9b9b6dfb062551549566d9792a1608f5e0c2d9/caucase/ca.py#L460-552>`_

   * **REASON**: it is impossible to generate certificate without `Not Valid After`, even with `cryptography <https://pypi.org/project/cryptography/>`_
