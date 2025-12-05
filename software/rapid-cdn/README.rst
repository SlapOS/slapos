=========
Rapid.CDN
=========

Software release which provides CDN - Content Delivery Network. It has a lot of features like:

 * provides cluster of exposed nodes in various regions
 * handles zero knowledge for SSL certificates
 * by using concept of SlapOS Master slaves allows user to request frontends with specific configuration
 * provides various frontend types

This documentation is fully minimalistict, as `software.cfg.json <software.cfg.json>`_ contains most of explanations.

Contributor and developer documentation is in `CONTRIBUTE.rst <CONTRIBUTE.rst>`_.

About frontend replication
==========================

Slaves of the root instance are sent as a parameter to requested frontends which will process them. The only difference is that they will then return the would-be published information to the root instance instead of publishing it. The root instance will then do a synthesis and publish the information to its slaves. The replicate instance only use 5 type of parameters for itself and will transmit the rest to requested frontends.

These parameters are:

  * ``-frontend-quantity`` : The quantity of frontends to request (defaults to "1")
  * ``-frontend-i-state``: The state of frontend i
  * ``-frontend-i-software-release-url``: Software release to be used for frontends, defaults to the current software release
  * ``-frontend-config-i-foo``: Frontend i will be requested with parameter foo. Those parameters will lead to service restart. Supported parameters are:
    * ``ram-cache-size``
    * ``disk-cache-size``
    * ``enable-http3``
    * ``http3-port``
    * ``expert-backend-allow-downgrade-ssl``
  * ``-sla-i-foo`` : where "i" is the number of the concerned frontend (between 1 and "-frontend-quantity") and "foo" a sla parameter.

For example::

  <parameter id="-frontend-quantity">3</parameter>
  <parameter id="-frontend-2-state">stopped</parameter>
  <parameter id="-sla-3-computer_guid">COMP-1234</parameter>
  <parameter id="-frontend-3-software-release-url">https://lab.nexedi.com/nexedi/slapos/raw/someid/software/rapid-cdn/software.cfg</parameter>


will request the third frontend on COMP-1234 and with SR https://lab.nexedi.com/nexedi/slapos/raw/someid/software/rapid-cdn/software.cfg. All frontends will be of software type ``custom-personal``. The second frontend will be requested with the state stopped.

*Note*: the way slaves are transformed to a parameter avoid modifying more than 3 lines in the frontend logic.

How to deploy a frontend server
===============================

This is to deploy an entire frontend server with a public IPv4.  If you want to use an already deployed frontend to make your service available via ipv4, switch to the "Example" parts.

First, you will need to request a "master" instance of Rapid.CDN with:

  * A ``domain`` parameter where the frontend will be available

like::

  <?xml version='1.0' encoding='utf-8'?>
  <instance>
   <parameter id="domain">moulefrite.org</parameter>
  </instance>

Then, it is possible to request many slave instances (currently only from slapconsole, UI doesn't work yet) of Rapid.CDN , like::

  instance = request(
    software_release=rapid_cdn,
    partition_reference='frontend2',
    shared=True,
    partition_parameter_kw={"url":"https://[1:2:3:4]:1234/someresource"}
  )

Those slave instances will be redirected to the "master" instance, and you will see on the "master" instance the associated proper directives of all slave instances.

Finally, the slave instance will be accessible from: https://someidentifier.moulefrite.org.

About SSL and SlapOS Master Zero Knowledge
==========================================

**IMPORTANT**: Old browsers, like Internet Explorer 8, which do not supporting `SNI <http://wiki.apache.org/httpd/NameBasedSSLVHostsWithSNI>`_ might not be able to use SSL based endpoints (https).

*Note*: Until master partition or slave specific certificate is uploaded each slave is served with fallback certificate. This fallback certificate is self signed, does not match served hostname and results with lack of response on HTTPs.

Obtaining CA for KeDiFa
-----------------------

KeDiFa uses caucase and so it is required to obtain caucase CA certificate used to sign KeDiFa SSL certificate, in order to be sure that certificates are sent to valid KeDiFa.

The easiest way to do so is to use caucase.

On some secure and trusted box which will be used to upload certificate to master or slave frontend partition install caucase https://pypi.org/project/caucase/

Master and slave partition will return key ``kedifa-caucase-url``, so then create and start a ``caucase-updater`` service::

  caucase-updater \
    --ca-url "${kedifa-caucase-url}" \
    --cas-ca "${frontend_name}.caucased.ca.crt" \
    --ca "${frontend_name}.ca.crt" \
    --crl "${frontend_name}.crl"

where ``frontend_name`` is a frontend cluster to which you will upload the certificate (it can be just one slave).

Make sure it is automatically started when trusted machine reboots: you want to have it running so you can forget about it. It will keep KeDiFa's CA certificate up to date when it gets renewed so you know you are still talking to the same service as when you previously uploaded the certificate, up to the original upload.

Master partition
----------------

After requesting master partition it will return ``master-key-generate-auth-url`` and ``master-key-upload-url``.

Doing HTTP GET on ``master-key-generate-auth-url`` will return authentication token, which is used to communicate with ``master-key-upload-url``. This token shall be stored securely.

By doing HTTP PUT to ``master-key-upload-url`` with appended authentication token it is possible to upload PEM bundle of certificate, key and any accompanying CA certificates to the master.

Example sessions is::

  request(...)

  curl -g -X GET --cacert "${frontend_name}.ca.crt" --crlfile "${frontend_name}.crl" master-key-generate-auth-url
  > authtoken

  cat certificate.pem ca.pem key.pem > bundle.pem

  curl -g --upload-file bundle.pem --cacert "${frontend_name}.ca.crt" --crlfile "${frontend_name}.crl" master-key-upload-url+authtoken

This replaces old request parameters:

 * ``apache-certificate``
 * ``apache-key``
 * ``apache-ca-certificate``

(*Note*: They are still supported for backward compatibility, but any value send to the ``master-key-upload-url`` will supersede information from SlapOS Master.)

Slave partition
---------------

After requesting slave partition it will return ``key-generate-auth-url`` and ``key-upload-url``.

Doing HTTP GET on ``key-generate-auth-url`` will return authentication token, which is used to communicate with ``key-upload-url``. This token shall be stored securely.

By doing HTTP PUT to ``key-upload-url`` with appended authentication token it is possible to upload PEM bundle of certificate, key and any accompanying CA certificates to the master.

Example sessions is::

  request(...)

  curl -g -X GET --cacert "${frontend_name}.ca.crt" --crlfile "${frontend_name}.crl" key-generate-auth-url
  > authtoken

  cat certificate.pem ca.pem key.pem > bundle.pem

  curl -g --upload-file bundle.pem --cacert "${frontend_name}.ca.crt" --crlfile "${frontend_name}.crl" key-upload-url+authtoken

This replaces old request parameters:

 * ``ssl_crt``
 * ``ssl_key``
 * ``ssl_ca_crt``

(*Note*: They are still supported for backward compatibility, but any value send to the ``key-upload-url`` will supersede information from SlapOS Master.)


Instance Parameters
===================

Master Instance Parameters
--------------------------

The parameters for instances are described at `instance-input-schema.json <instance-input-schema.json>`_.

Here some additional informations about the parameters listed, below:

domain
~~~~~~

Name of the domain to be used (example: mydomain.com). Sub domains of this domain will be used for the slave instances (example: instance12345.mydomain.com). It is then recommended to add a wild card in DNS for the sub domains of the chosen domain like::

  *.mydomain.com. IN A 123.123.123.123

Using the IP given by the Master Instance.  "domain" is a mandatory Parameter.

port
~~~~
Port used by Rapid.CDN. Optional parameter, defaults to 4443.

plain_http_port
~~~~~~~~~~~~~~~
Port used by Rapid.CDN to serve plain http (only used to redirect to https).
Optional parameter, defaults to 8080.


Slave Instance Parameters
-------------------------

The parameters for instances are described at `instance-slave-input-schema.json <instance-slave-input-schema.json>`_.

Here some additional informations about the parameters listed, below:

path
~~~~
Only used if type is "zope".

Will append the specified path to the "VirtualHostRoot" of the zope's VirtualHostMonster.

"path" is an optional parameter, ignored if not specified.
Example of value: "/erp5/web_site_module/hosting/"

url
~~~
URL of the backend to use, optional but will result with non functioning slave.

Example: http://mybackend.com/myresource

enable_cache
~~~~~~~~~~~~

Enables HTTP cache, optional.


health-check-*
~~~~~~~~~~~~~~

This set of parameters is used to control the way how the backend checks will be done. Such active checks can be really useful for `stale-if-error` caching technique and especially in case if backend is very slow to reply or to connect to.

`health-check-http-method` can be used to configure the HTTP method used to check the backend. Special method `CONNECT` can be used to check only for connection attempt.

Please be aware that the `health-check-timeout` is really short by default, so in case if `/` of the backend is slow to reply configure proper path with `health-check-http-path` to not mark such backend down too fast, before increasing the check timeout.

Thanks to using health-check it's possible to configure failover system. By providing `health-check-failover-url` some special backend can be used to reply in case if original backend replies with error (codes like `5xx`). As a note one can setup this failover URL like `https://failover.example.com/?p=` so that the path from the incoming request will be passed as parameter. Additionally authentication to failover URL is supported with `health-check-authenticate-to-failover-backend` and SSL Proxy verification with `health-check-failover-ssl-proxy-verify` and `health-check-failover-ssl-proxy-ca-crt`.

**Note**: It's important to correctly configure failover URL response, especially in case if it's expected to use `stale-if-error` simulation available while `enable_cache` is used. In order to serve pages from cache the failover URL have to return error HTTP code (like 503 SERVICE_UNAVAILABLE), so that in such case cached page will have precedence over the reply from failover URL.

Examples
========

Here are some example of how to make your SlapOS service available through an already deployed frontend.

Simple Example (default)
------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be
redirected and accessible from the proxy::

  instance = request(
    software_release=rapid_cdn,
    software_type="default",
    partition_reference='my frontend',
    shared=True,
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
    }
  )


Zope Example (default)
----------------------

Request slave frontend instance using a Zope backend so that
https://[1:2:3:4:5:6:7:8]:1234 will be redirected and accessible from the
proxy::

  instance = request(
    software_release=rapid_cdn,
    software_type="default",
    partition_reference='my frontend',
    shared=True,
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
        "type":"zope",
    }
  )


Advanced example 
-----------------

Request slave frontend instance using a Zope backend, with Varnish activated,
listening to a custom domain and redirecting to /erp5/ so that
https://[1:2:3:4:5:6:7:8]:1234/erp5/ will be redirected and accessible from
the proxy::

  instance = request(
    software_release=rapid_cdn,
    software_type="default",
    partition_reference='my frontend',
    shared=True,
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
        "enable_cache":"true",
        "type":"zope",
        "path":"/erp5",
        "domain":"mycustomdomain.com",
    }
  )

Simple Example 
---------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be::

  instance = request(
    software_release=rapid_cdn,
    software_type="default",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",

Promises
========

Note that in some cases promises will fail:

 * not possible to request frontend slave for monitoring (monitoring frontend promise)
 * no slaves present (configuration promise and others)
 * no cached slave present (configuration promise and others)

This is known issue and shall be tackled soon.

KeDiFa
======

Additional partition with KeDiFa (Key Distribution Facility) is by default requested on the same computer as master frontend partition.

By adding to the request keys like ``-sla-kedifa-<key>`` it is possible to provide SLA information for kedifa partition. Eg to put it on computer ``couscous`` it shall be ``-sla-kedifa-computer_guid: couscous``.

Also ``-kedifa-software-release-url`` can be used to override the software release for kedifa partition.

Notes
=====

It is not possible with slapos to listen to port <= 1024, because process are
not run as root.

Solution 1 (iptables)
---------------------

It is a good idea then to go on the node where the instance is
and set some ``iptables`` rules like (if using default ports)::

  iptables -t nat -A PREROUTING -p tcp -d ${public_ipv4} --dport 443 -j DNAT --to-destination ${listening_ipv4}:4443
  iptables -t nat -A PREROUTING -p udp -d ${public_ipv4} --dport 443 -j DNAT --to-destination ${listening_ipv4}:4443
  iptables -t nat -A PREROUTING -p tcp -d ${public_ipv4} --dport 80 -j DNAT --to-destination ${listening_ipv4}:8080
  ip6tables -t nat -A PREROUTING -p tcp -d ${public_ipv6} --dport 443 -j DNAT --to-destination ${listening_ipv6}:4443
  ip6tables -t nat -A PREROUTING -p tcp -d ${public_ipv6} --dport 80 -j DNAT --to-destination ${listening_ipv6}:8080

Where ``{public_ipv[46]}`` is the public IP of your server, or at least the LAN IP to where your NAT will forward to, and ``{listening_ipv[46]}`` is the private ipv4 (like 10.0.34.123) that the instance is using and sending as connection parameter.

Additionally in order to access the server by itself such entries are needed in ``OUTPUT`` chain (as the internal packets won't appear in the ``PREROUTING`` chain)::

  iptables -t nat -A OUTPUT -p tcp -d ${public_ipv4} --dport 443 -j DNAT --to ${listening_ipv4}:4443
  iptables -t nat -A OUTPUT -p udp -d ${public_ipv4} --dport 443 -j DNAT --to ${listening_ipv4}:4443
  iptables -t nat -A OUTPUT -p tcp -d ${public_ipv4} --dport 80 -j DNAT --to ${listening_ipv4}:8080
  ip6tables -t nat -A OUTPUT -p tcp -d ${public_ipv6} --dport 443 -j DNAT --to ${listening_ipv6}:4443
  ip6tables -t nat -A OUTPUT -p tcp -d ${public_ipv6} --dport 80 -j DNAT --to ${listening_ipv6}:8080

**Note regarding ports**:

 * the port seen by application in case of IPv4 TCP will be "correct" - the ``443`` or ``80``
 * the port seen by application in case of IPv6 and IPv4 UDP will be "incorrect" - the ``4443`` or ``8080``


Solution 2 (network capability)
-------------------------------

It is also possible to directly allow the service to listen on 80 and 443 ports using the following command::

  setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$RAPID_CDN_SOFTWARE_RELEASE_MD5/parts/haproxy/sbin/haproxy

Then specify in the master instance parameters:

 * set ``port`` to ``443``
 * set ``plain_http_port`` to ``80``

**Note regarding securitry**:

 * such configuration results with all partitions being able to bind to low ports using this binary

Authentication to the backend
=============================

The cluster generates CA served by caucase, available with ``backend-client-caucase-url`` return parameter.

Then, each slave configured with ``authenticate-to-backend`` to true, will use a certificate signed by this CA while accessing https backend.

This allows backends to:

 * restrict access only from some frontend clusters
 * trust values (like ``X-Forwarded-For``) sent by the frontend

Error Page Management
=====================

The Error Page Manager (EPM) allows to customize error pages sent by
the CDN to the clients.

Roles and access
----------------

* **CDN Operator** -- receives ``error-page-manager-operator-url`` in the
  master partition connection parameters.
* **Shared instance user** -- receives ``error-page-upload-url``
  in the shared-instance connection parameters. Can write and reset
  502, 503, and 504 for their own site to override cluster default.

Supported error codes
---------------------

.. list-table::
   :header-rows: 1
   :widths: 5 80 18

   * - Code
     - CDN code description
     - Customizable by

   * - 400
     - **Bad Request** -- the frontend HAProxy could not parse the
       incoming HTTP request.
     - CDN Operator

   * - 404
     - **Not Found** -- the request's ``Host`` header did not match
       any shared instance configured in this cluster.  Only such
       "unknown domain" 404s come from the EPM; a 404 produced by a
       backend itself (a site responding with 404 for an unknown
       path on its own service) is forwarded to the client unchanged.
     - CDN Operator

   * - 408
     - **Request Timeout** -- the client opened a connection but did
       not send a complete request within the cluster's request
       timeout.
     - CDN Operator

   * - 500
     - **Internal Server Error** -- the CDN infrastructure itself
       failed to process the request.
     - CDN Operator

   * - 502
     - **Bad Gateway** -- the backend HAProxy reached the backend
       server, but the response is unparseable.
     - CDN Operator, Shared instance user

   * - 503
     - **Service Unavailable** -- the backend HAProxy has no healthy
       backend to serve the request.
     - CDN Operator, Shared instance user

   * - 504
     - **Gateway Timeout** -- the backend connection was established
       and the HTTP request was sent, but the backend did not
       produce a complete response within CDN timeout.
     - CDN Operator, Shared instance user


Web management interface
------------------------

Open the operator URL or the shared-instance upload URL in a browser.
The page shows one row per editable error code with a text area for
the HTML body and two buttons:

* **Save** -- stores the HTML and immediately regenerates the HAProxy
  error files served to CDN users.
* **Reset** -- removes the custom page; the CDN falls back to the
  built-in default page (or to the operator's page in the case of a
  shared-instance reset).

The operator UI exposes all seven supported codes; the shared-instance
UI exposes only codes 502, 503, and 504, scoped to the site owner's
own files.  Both screens share the same look and the same Save / Reset
semantics.


REST API
--------

Both the operator URL and the shared-instance URL accept the same REST
shape; only the URL prefix differs.  ``CODE`` is one of the supported
codes from the table above.

Retrieve current HTML
~~~~~~~~~~~~~~~~~~~~~

::

    GET BASE_URL/CODE         # operator only

Returns the stored HTML document (``text/html``) or an empty 200
response if no custom page is set.  The shared-instance variant of GET
is intentionally not exposed.

Example::

    curl https://example.com/operator/TOKEN/503

Upload a custom HTML document
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    PUT BASE_URL/CODE

Request body: a complete HTML document (UTF-8, max 2 MB).  Response:
``204 No Content`` on success.  The change is applied immediately -- no
restart is needed.

Operator example::

    curl -X PUT \
         -H 'Content-Type: text/html' \
         --data-binary @my-503.html \
         https://example.com/operator/TOKEN/503

Site-owner example::

    curl -X PUT \
         -H 'Content-Type: text/html' \
         --data-binary @my-503.html \
         "https://example.com/shared/TOKEN/503"

Any lines at the very top of the uploaded document beginning with ``#``
are silently dropped before HAProxy framing.  This syntax is
**reserved** for a possible future feature that allows declaring custom
response headers; no header support is implemented in this version.
Treating ``#``-prefix lines as reserved now means files written today
will keep behaving correctly if header support is added later.

Reset to default
~~~~~~~~~~~~~~~~

::

    DELETE BASE_URL/CODE

Response: ``204 No Content``.  For the operator, the built-in default
is restored for every site that had not set its own override.  For a
site owner, the operator's page (or the built-in default if none) is
restored for that site only.

Example::

    curl -X DELETE \
         https://example.com/operator/TOKEN/503


Override precedence
-------------------

For each error code and each hosted site the page shown to end users is
chosen as follows:

1. Site-owner override for that site (if set)
2. Operator custom page (if set)
3. Built-in default page

Uploading a new operator page immediately re-generates the HAProxy
error files for all sites that do **not** have their own override.
Site-owner uploads only affect that one site.


Custom error page HTML and multi language support
-------------------------------------------------

Each uploaded page is a complete, self-contained HTML document.  The
EPM wraps it in a minimal HTTP/1.0 response envelope that HAProxy
requires; there is no server-side templating.

As the result languages can be shipped in the same file and let the
visitor's browser pick the right one with a small piece of inline JavaScript.

The recipe:

1. Wrap each translation in a ``<section data-lang="...">`` block, with
   a matching ``lang=`` attribute for accessibility.
2. Mark one section ``data-default`` -- the fallback when nothing else
   matches.
3. CSS hides every ``[data-lang]`` by default and reveals only the one
   tagged ``.active``.
4. A ``<noscript>`` block flips the rule so clients without JavaScript
   see the ``data-default`` section instead of a blank page.
5. A tiny inline script reads ``navigator.languages`` (already sorted
   by browser preference, equivalent to ``Accept-Language`` with
   q-values applied), tries each preference as an exact match and then
   a primary-language fallback (e.g. ``fr-CA`` -> ``fr``), and adds
   ``.active`` to the matching section.

The **built-in default pages** bundled with this software release follow
this pattern with five languages (English, French, Japanese, German,
Polish) and are the recommended starting point -- download one,
adjust the visible text, and upload:

* `503.html <templates/error-pages/503.html>`_ -- Service Unavailable
* `502.html <templates/error-pages/502.html>`_ -- Bad Gateway
* `504.html <templates/error-pages/504.html>`_ -- Gateway Timeout
* `500.html <templates/error-pages/500.html>`_ -- Internal Server Error
* `404.html <templates/error-pages/404.html>`_ -- Not Found
* `408.html <templates/error-pages/408.html>`_ -- Request Timeout
* `400.html <templates/error-pages/400.html>`_ -- Bad Request

Add or remove ``<section data-lang="...">`` blocks as needed.  The same
JavaScript handles any number of languages without modification -- it
discovers the list from the DOM at runtime.  A single-language page is
also fine; just keep one ``data-lang`` / ``data-default`` section and
the switcher will pick it unconditionally.

HAProxy serves the file via the ``errorfile`` directive, which loads
the whole file into a single buffer.  Rapid.CDN raises
``tune.bufsize`` to **64 KiB** to accommodate multilingual error pages
with comfortable headroom.  If you ship many languages or long
localised copy you should still keep the per-page total under 64 KiB.


Security headers and Content-Security-Policy
--------------------------------------------

The HTTP envelope generated for error files sets ``X-Content-Type-Options:
nosniff`` and an explicit ``Content-Type: text/html; charset=utf-8``;
nothing else security-relevant is added.  In particular, **no
Content-Security-Policy is emitted** for error responses.  Inline
JavaScript and inline CSS in uploaded pages execute by default, which
is how the built-in multilingual switcher works.

If your cluster deploys a CSP at the HAProxy layer that also applies
to error responses (for example via ``http-after-response set-header
Content-Security-Policy ...``), you have three options:

1. **Allow inline content on error responses.**  The simplest path --
   ``script-src 'unsafe-inline'; style-src 'unsafe-inline'`` on the
   error-response CSP only.  Acceptable because the error-page HTML is
   under your control (either shipped by the operator at SR build time,
   or uploaded via PUT), so there is no untrusted-input path.

2. **Allow only the known SHA-256 hashes** of the inline blocks shipped
   in the built-in pages.  These are stable across all seven codes::

       Content-Security-Policy:
         script-src 'sha256-kd4gNDpn2kShafbtEoOkHmUNMKotywb7hR2o4124F88=';
         style-src  'sha256-LHlcrzszQdddVhDnsD/EHYrGUNlsv/Dye8VaQITP9gI='
                    'sha256-46ncLRPYE5GJAkUBe2ZUGES+FfmgO/M1KpwH8fS62iQ='

   The hashes will need updating if the inline script or styles are
   customised -- modern browsers print the correct value in the
   developer console when the policy blocks the resource.

3. **Compute hashes per upload.**  If you maintain your own custom
   pages, allowlist their hashes the same way.

Avoid the worst-case combination ``script-src 'self'`` (no
``'unsafe-inline'``, no matching ``'sha256-...'``) **with** an inline
``<style>`` block allowed.  In that configuration the CSS will hide
all language sections, the script that would have shown one is blocked,
and the visitor sees a blank page -- the ``<noscript>`` fallback does
not engage because the browser does have JavaScript, it just denied
execution.

Technical notes
===============

Instantiated cluster structure
------------------------------

Instantiating Rapid.CDN results with a cluster in various partitions:

 * master (the controlling one)
 * kedifa (contains kedifa server)
 * frontend-node-N which contains the running processes to serve sites - this partition can be replicated by ``-frontend-quantity`` parameter

It means sites are served in ``frontend-node-N`` partition, and this partition is structured as:

 * Haproxy serving the browser [client-facing-haproxy]
 * (optional) Apache Traffic Server for caching [ats]
 * Haproxy as a way to communicate to the backend [backend-facing-haproxy]
 * some other additional tools (monitor, etc)

In case of slaves without cache (``enable_cache = False``) the request will travel as follows::

  client-facing-haproxy --> backend-facing-haproxy --> backend

In case of slaves using cache (``enable_cache = True``) the request will travel as follows::

  client-facing-haproxy --> ats --> backend-facing-haproxy --> backend

Usage of Haproxy as a relay to the backend allows much better control of the backend, removes the hassle of checking the backend from frontend Haproxy and allows future developments like client SSL certificates to the backend or even health checks.

Instance Node
-------------

The master partition is an *instance node* and as such run one locally to validates each slave.
It validates against the JSON schema and, for slaves with a custom ``domain``, checks DNS ownership via an HMAC-signed ``_slapos-challenge`` TXT record. 
SSL certificate validity and server-alias conflicts between slaves are also checked. 

Validation is passive: no slave is rejected, blocked, or modified. Results are stored in a local SQLite database so operators can review them. 

The recipes involved:

 * ``slapos.recipe.slapconfiguration`` (``JsonSchemaWithDB`` variants):
   validates each slave and records ``valid`` / ``invalid`` plus errors
   in the instance database.
 * ``slapos.recipe.cdninstancenode``: CDN-specific checks (DNS ownership,
   SSL, server-alias conflict).

So on slapos node instance run, the recipe stores the slave instance list in a local database for processing by the instance node and it reads the results from another one.

Validation is asynchronous as some validation like DNS check doesn't depend on slapos node instance parameters. 
The instance node runs from cron on the master partition, independently of slapgrid, so DNS challenges are re-checked between slapgrid cycles.
When validation state changes the master partition is banged so slapgrid reprocesses it.

The instance database is served by ``sqlite-web`` on the master-introspection frontend and is returned by the master partition as ``publish-slave-sqlite-validation-database``.

``instance-retention-delay`` (seconds, default 90 days) sets how long a slave stays in the database after disappearing from the master; ``0`` removes it immediately.
Before that a slave instance in stopped/destroyed state would disappear and validation would be lost, now we stop serving the instance like before but the validation result is kept for the retention delay. 

Kedifa implementation
---------------------

`Kedifa <https://lab.nexedi.com/nexedi/kedifa>`_ server runs on kedifa partition.

Each `frontend-node-N` partition downloads certificates from the kedifa server.

Caucase (exposed by ``kedifa-caucase-url`` in master partition parameters) is used to handle certificates for authentication to kedifa server.

If ``automatic-internal-kedifa-caucase-csr`` is enabled (by default it is) there are scripts running on master partition to simulate human to sign certificates for each frontend-node-N node.

Support for X-Real-Ip and X-Forwarded-For
-----------------------------------------

X-Forwarded-For and X-Real-Ip are transmitted to the backend.

Automatic Internal Caucase CSR
------------------------------

Cluster is composed on many instances, which are landing on separate partitions, so some way is needed to bootstrap trust between the partitions.

There are two ways to achieve it:

 * use default, Automatic Internal Caucase CSR used to replace human to sign CSRs against internal CAUCASEs automatic bootstrap, which leads to some issues, described later
 * switch to manual bootstrap, which requires human to create and manage user certificate (with caucase-updater) and then sign new frontend nodes appearing in the system

The issues during automatic bootstrap are:

 * rogue or hacked SlapOS Master can result with adding rogue frontend nodes to the cluster, which will be trusted, so it will be possible to fetch all certificates and keys from Kedifa or to login to backends
 * when new node is added there is a short window during which rogue person is able to trick automatic signing, and have it's own node added

In both cases promises will fail on node which is not able to get signed, but in case of Kedifa the damage already happened (certificates and keys are compromised). So in case if cluster administrator wants to stay on the safe side, both automatic bootstraps shall be turned off.

How the automatic signing works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Having in mind such structure:

 * instance with caucase: ``caucase-instance``
 * N instances which want to get their CSR signed: ``csr-instance``

In ``caucase-instance`` CAUCASE user is created by automatically signing one user certificate, which allows to sign service certificates.

The ``csr-instance`` creates CSR, extracts the ID of the CSR, exposes it via HTTP and ask caucase on ``caucase-instance`` to sign it. The ``caucase-instance`` checks that exposed CSR id matches the one send to caucase and by using created user to signs it.

Content-Type header
~~~~~~~~~~~~~~~~~~~

The ``Content-Type`` header is not modified by the CDN at all. Previous implementation based on Caddy software tried to guess it.

Date header
~~~~~~~~~~~

The ``Date`` is added only if not sent by the backend. It's done on backend-facing component and kept in caching component as is. Previous implementation was adding this header in the cache component.

websocket
~~~~~~~~~

All frontends are websocket aware now, and ``type:websocket`` parameter became optional. It's required if support for ``websocket-path-list`` or ``websocket-transparent`` is required.

Accept-Encoding normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared instances default to ``normalize-accept-encoding: true``: the client-facing haproxy collapses the long tail of browser-specific ``Accept-Encoding`` strings to a small canonical set before forwarding to the origin. This replaces the gzip-only ``prefer-gzip-encoding-to-backend`` parameter from earlier releases. Set ``normalize-accept-encoding: false`` on a shared instance to forward the client's ``Accept-Encoding`` verbatim.

Why
"""

Without normalization, every browser variant of ``Accept-Encoding`` (``gzip, deflate``; ``gzip, deflate, br``; ``gzip, deflate, br, zstd``; ``br, zstd, gzip``; ...) becomes a separate cache key under ``Vary: Accept-Encoding``. The cache fragments and hit ratio drops while the origin keeps re-encoding the same response.

Mapping
"""""""

================================ ===================================
Client ``Accept-Encoding``       Forwarded to origin
================================ ===================================
``gzip, deflate, br, zstd``      ``zstd, br, gzip, deflate``
``gzip, deflate, br``            ``br, gzip, deflate``
``gzip, deflate``                ``gzip, deflate``
``gzip``                         ``gzip, deflate``
``gzip, weirdcoding, deflate``   ``gzip, deflate``
``weirdcoding, deflate``         ``deflate``
``deflate``                      ``deflate``
``identity``                     ``identity``   (no recognised token)
``weirdcoding``                  ``weirdcoding`` (no recognised token)
``*``                            ``*``          (no recognised token)
(header absent)                  (header absent)
================================ ===================================

Deviations from a strict reading of RFC 9110 §12.5.3
""""""""""""""""""""""""""""""""""""""""""""""""""""

Two deviations are deliberate and match real implementations:

1. **Widening of acceptable codings.** When the client lists only a stronger encoding (e.g. ``gzip``, ``br``, ``zstd``), we append weaker ones (``gzip`` → ``gzip, deflate``; ``br`` → ``br, gzip, deflate``; ...). Strictly, §12.5.3 says any unlisted coding is "not acceptable", so we are claiming acceptance the client did not give. In practice every client that advertises a modern coding also handles all weaker ones, so this is a non-event.

2. **Dropping unrecognised tokens that appear alongside a recognised one** (``gzip, weirdcoding, deflate`` → ``gzip, deflate``). This is a forward-compatibility hazard: when a new encoding emerges (br in 2015, zstd in 2020), normalize-AE will demote clients that advertise it alongside known codings until the haproxy ACL chain is extended to recognise the new token.

q-values are silently stripped. Per §12.5.3, ``gzip;q=0`` means "I refuse gzip" -- rewriting it to ``gzip, deflate`` flips a refusal into an acceptance. No mainstream browser emits q=0, so this is a paper risk; bespoke clients (curl scripts, embedded devices) should not rely on this CDN to honour it.

Enforced Accept-Encoding compression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``enforced-compression`` is controls enforcing the compression to backend with Accept-Encoding header.

Trigger
"""""""

When the client sends no ``Accept-Encoding`` header at all, or sends the explicit wildcard ``Accept-Encoding: *`` -- both of which mean "any encoding is acceptable" per RFC 9110 §12.5.3 -- the client-facing haproxy substitutes the canonical form for the shared instance's effective ``enforced-compression`` value before forwarding upstream. When the client sent any concrete ``Accept-Encoding`` (including ``identity`` or an unknown coding), the rewrite does nothing.

Mapping
"""""""

============== ==========================================
Effective value Forwarded to origin
============== ==========================================
``none``        (rewrite disabled, header forwarded as-is)
``deflate``     ``deflate``
``gzip``        ``gzip, deflate``
``br``          ``br, gzip, deflate``
``zstd``        ``zstd, br, gzip, deflate``
============== ==========================================

The canonical forms match exactly what ``normalize-accept-encoding`` emits, so the two features compose with no special-case interaction: when both are on, normalize-AE re-emits the same string, which is a no-op.
