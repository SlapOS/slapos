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
 * simplify Jijna2 syntax and drop whitespace control, as it is not needed
 * make beautiful (eg. with whitespaces and nice comments) generated files (mostly Jinja2)
 * have ``caddy-frontend`` specific parameters, with backward compatibility to ``apache-frontend`` ones (like ``apache_custom_http`` --> ``caddy_custom_http``)
