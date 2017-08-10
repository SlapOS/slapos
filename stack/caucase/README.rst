caucase - CA for Users, CA for SErvices

Slapos integration
==================

This software release library provides macros to help you integrate caucase
into your software release.

``buildout.cfg`` declares caucase dependencies.

``caucase.jinja2.library`` declares jinja2 macros to deploy client and
server components of caucase.


Remember, that importing the template has to happen with context:

``{% import "caucase" as caucase with context %}``

Software
--------

This exposes the following sections:
     
  - ``caucase-eggs``: Generate scripts to work with certificates using `caucase commands`_. In the software buildout's ``bin`` directory.
  - ``caucase-jinja2-library``: Provide macros to generate sections that will use scripts created by ``caucase-eggs`` section.

.. _`caucase commands`: https://lab.nexedi.com/nexedi/caucase/blob/master/README.rst#commands

.. note::
 ``caucase-eggs`` needs to be listed in ``parts=`` of the software buildout or referenced by another installed part. 

.. note:: ``caucase-jinja2-library`` needs to be referenced in an installed section using ``slapos.recipe.template`` from software buildout to make macros available in the the context of instance buildout. From ``software.cfg``:
  
  .. code::
    ini
    
    [instance]
    recipe = slapos.recipe.template:jinja2
    import-list =
      file caucase caucase-jinja2-library:target


Server
------

.. topic:: caucased(prefix, caucased_path, data_dir, netloc, service_auto_approve_count=0, key_len=None, promise=None)
  
  This macro produces the following sections which you will want to reference sothey get instanciated:
  
  - `<prefix>`: Creates `<caucased>` executable file to start `caucased`,
    and `<data_dir>` directory for its data storage needs.
    `caucased` will listend on `netloc`, which must be of the format
    `hostname[:port]`, where hostname may be an IPv4 (ex: `127.0.0.1`), an IPv6
    (ex: `[::1]`), or a domain name (ex: `localhost`). Port, when provided, must
    be numeric. If port is not provided, it default to `80`.

   If port is `80`, ``caucased`` will listen on `80` and `443` for given
   hostname. This is *not* the recommended usage.

   If port is not `80`, ``caucased`` will listen on it *and* its immediate next
   higher port (ex: ``[::1]:8009`` will listen on both ``[::1]:8009`` and
   ``[::1]:8010``). This is the recommended usage.
  
  - ``<prefix>-promise``: (only produced if ``<promise>`` is not None). Creates an
    executable at the path given in ``<promise>``, which will attempt to connect to
    ``caucase`` server, and fail if it detects any anomaly (port not listening,
    protocol error, certificate discrepancy...).


Client
------

.. topic:: ``rerequest(prefix, buildout_bin_directory, template, csr, key)``
  
  - ``<prefix>``: Creates ``<rerequest>`` executable file to run ``caucase-rerequest``.
  
  This script allows you to re-issue a CSR using a locally-generated private key.

.. topic:: ``updater(prefix, buildout_bin_directory, updater_path, url, data_dir, crt_path, ca_path, crl_path, key_path=None, on_renew=None, max_sleep=None, mode='service', template_csr_pem=None, openssl=None)``

  - ``<prefix>``: Creates ``<updater>`` executable file to start ``caucase-updater``, and ``<data_dir>`` directory for its data storage needs.
  
  ``caucase-updater`` will monitor a key pair, corresponding CA certificate and CRL, and renew them before expiration.
  
.. note::
  You can find more information about any argument mentioned above calling ``<command> --help <argument>``

