Generally things to be done with ``caddy-frontend``:

 * ``apache-ca-certificate`` shall be merged with ``apache-certificate``
 * (new) ``type:websocket`` slave
 * ``type:eventsource``:

   * **Jérome Perrin**: *For event source, if I understand https://github.com/mholt/caddy/issues/1355 correctly, we could use caddy as a proxy in front of nginx-push-stream . If we have a "central shared" caddy instance, can it handle keeping connections opens for many clients ?*
 * ``ssl_ca_crt``
 * ``prefer-gzip-encoding-to-backend`` (requires writing middleware plugin for Caddy)::

    RequestHeader edit Accept-Encoding "(^gzip,.*|.*, gzip,.*|.*, gzip$|^gzip$)" "gzip"
 * ``disabled-cookie-list`` (requires writing middleware plugin for Caddy)::

    RequestHeader edit Cookie "(^%(disabled_cookie)s=[^;]*; |; %(disabled_cookie)s=[^;]*|^%(disabled_cookie)s=[^;]*$)" ""' % dict(disabled_cookie=disabled_cookie)  }}
 * ``ssl_proxy_ca_crt`` for ``ssl_proxy_verify``, this is related to bug https://github.com/mholt/caddy/issues/1550, proposed solution `just adding your CA to the system's trust store`
 * ``check-error-on-caddy-log`` like ``check-error-on-apache-log``
 * cover test suite like resilient tests for KVM and prove it works the same way as Caddy
 * make beautiful (eg. with whitespaces and nice comments) generated files (mostly Jinja2)
 * have ``caddy-frontend`` specific parameters, with backward compatibility to ``apache-frontend`` ones (like ``apache_custom_http`` --> ``caddy_custom_http``)
 * change ``switch-softwaretype`` to way how ``software/erp5`` does, which will help with dropping jinja2 template for ``caddy-wrapper``, which is workaround for current situation https://lab.nexedi.com/nexedi/slapos/merge_requests/312#note_62678
 * use `slapos!326 <https://lab.nexedi.com/nexedi/slapos/merge_requests/326>`_ instead of self-developed graceful restart scripts
 * move out `test/utils.py` and use it from shared python distribution
 * provide various tricks for older browsers::

    # The following directives modify normal HTTP response behavior to
    # handle known problems with browser implementations.

    BrowserMatch "Mozilla/2" nokeepalive
    BrowserMatch ".*MSIE.*" nokeepalive ssl-unclean-shutdown \
                            downgrade-1.0 force-response-1.0
    BrowserMatch "RealPlayer 4\.0" force-response-1.0
    BrowserMatch "Java/1\.0" force-response-1.0
    BrowserMatch "JDK/1\.0" force-response-1.0
    # The following directive disables redirects on non-GET requests for
    # a directory that does not include the trailing slash.  This fixes a
    # problem with Microsoft WebFolders which does not appropriately handle
    # redirects for folders with DAV methods.
    # Same deal with Apple's DAV filesystem and Gnome VFS support for DAV.
    BrowserMatch "Microsoft Data Access Internet Publishing Provider" redirect-carefully
    BrowserMatch "MS FrontPage" redirect-carefully
    BrowserMatch "^WebDrive" redirect-carefully
    BrowserMatch "^WebDAVFS/1.[0123]" redirect-carefully
    BrowserMatch "^gnome-vfs" redirect-carefully
    BrowserMatch "^XML Spy" redirect-carefully
    BrowserMatch "^Dreamweaver-WebDAV-SCM1" redirect-carefully
 * Implement gzip/defalte on resources::

    # Deflate
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/x-javascript application/javascript
    BrowserMatch ^Mozilla/4 gzip-only-text/html
    BrowserMatch ^Mozilla/4\.0[678] no-gzip
    BrowserMatch \bMSIE !no-gzip !gzip-only-text/html
 * check, and if needed apply, Apache-like SSL configuration switches::

    # SSL Configuration
    SSLProtocol all -SSLv2 -SSLv3
    SSLCipherSuite ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:HIGH:!aNULL:!MD5
    SSLHonorCipherOrder on
    <FilesMatch "\.(cgi|shtml|phtml|php)$">
          SSLOptions +StdEnvVars
    </FilesMatch>


Things which can't be implemented:

 * use certificates valid forever in tests using `cryptography <https://pypi.org/project/cryptography/>`_, with `available example <https://lab.nexedi.com/nexedi/caucase/blob/1c9b9b6dfb062551549566d9792a1608f5e0c2d9/caucase/ca.py#L460-552>`_

   * **REASON**: it is impossible to generate certificate without `Not Valid After`, even with `cryptography <https://pypi.org/project/cryptography/>`_
