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
 * have ``caddy-frontend`` specific parameters, with backward compatibility to ``apache-frontend`` ones:

  * ``caddy_custom_http`` and ``caddy_custom_https``
  * ``apache-ca-certificate``
  * ``apache-certificate`` and ``apache-key``

 * change ``switch-softwaretype`` to way how ``software/erp5`` does, which will help with dropping jinja2 template for ``caddy-wrapper``, which is workaround for current situation https://lab.nexedi.com/nexedi/slapos/merge_requests/312#note_62678
 * use `slapos!326 <https://lab.nexedi.com/nexedi/slapos/merge_requests/326>`_, and especially `note about complex restart scenarios <https://lab.nexedi.com/nexedi/slapos/merge_requests/326#note_60198>`_, instead of self-developed graceful restart scripts
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
 * check, and if needed apply, Apache-like SSL configuration switches::

    # SSL Configuration
    SSLProtocol all -SSLv2 -SSLv3
    SSLCipherSuite ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:HIGH:!aNULL:!MD5
    SSLHonorCipherOrder on
    <FilesMatch "\.(cgi|shtml|phtml|php)$">
          SSLOptions +StdEnvVars
    </FilesMatch>
 * reduce the time of configuration validation (in ``instance-apache-frontend.cfg`` sections ``[configtest]``, ``[caddy-configuration]``, ``[nginx-configuration]``), as it is not scalable on frontend with 2000+ slaves (takes few minutes instead of few, < 5, seconds), issue posted `upstream <https://github.com/mholt/caddy/issues/2220>`_
 * drop ``6tunnel`` and use ``bind`` in Caddy configuration, as soon as multiple binds will be possible, tracked in upstream `bind: support multiple values <https://github.com/mholt/caddy/pull/2128>`_ and `ipv6: does not bind on ipv4 and ipv6 for sites that resolve to both <https://github.com/mholt/caddy/issues/864>`_
 * use caddy-frontend in `standalone style playbooks <https://lab.nexedi.com/nexedi/slapos.package/tree/master/playbook/roles/standalone-shared>`_
 * ensure `QUIC <https://en.wikipedia.org/wiki/QUIC>`_ is used by caddy

Things which can't be implemented:

 * use certificates valid forever in tests using `cryptography <https://pypi.org/project/cryptography/>`_, with `available example <https://lab.nexedi.com/nexedi/caucase/blob/1c9b9b6dfb062551549566d9792a1608f5e0c2d9/caucase/ca.py#L460-552>`_

   * **REASON**: it is impossible to generate certificate without `Not Valid After`, even with `cryptography <https://pypi.org/project/cryptography/>`_
