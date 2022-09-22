==============
Caddy Frontend
==============

Frontend system using Caddy, based on apache-frontend software release, allowing to rewrite and proxy URLs like myinstance.myfrontenddomainname.com to real IP/URL of myinstance.

Caddy Frontend works using the master instance / slave instance design. It means that a single main instance of Caddy will be used to act as frontend for many slaves.

This documentation covers only specific scenarios. Most of the parameters are described in `software.cfg.json <software.cfg.json>`_.

Software type
=============

Caddy frontend is available in 4 software types:
  * ``default`` : The standard way to use the Caddy frontend configuring everything with a few given parameters
  * ``custom-personal`` : This software type allow each slave to edit its Caddy configuration file
  * ``default-slave`` : XXX
  * ``custom-personal-slave`` : XXX


About frontend replication
==========================

Slaves of the root instance are sent as a parameter to requested frontends which will process them. The only difference is that they will then return the would-be published information to the root instance instead of publishing it. The root instance will then do a synthesis and publish the information to its slaves. The replicate instance only use 5 type of parameters for itself and will transmit the rest to requested frontends.

These parameters are:

  * ``-frontend-type`` : the type to deploy frontends with. (default to "default")
  * ``-frontend-quantity`` : The quantity of frontends to request (default to "1")
  * ``-frontend-i-state``: The state of frontend i
  * ``-frontend-i-software-release-url``: Software release to be used for frontends, default to the current software release
  * ``-frontend-config-i-foo``: Frontend i will be requested with parameter foo
  * ``-sla-i-foo`` : where "i" is the number of the concerned frontend (between 1 and "-frontend-quantity") and "foo" a sla parameter.

For example::

  <parameter id="-frontend-quantity">3</parameter>
  <parameter id="-frontend-type">custom-personal</parameter>
  <parameter id="-frontend-2-state">stopped</parameter>
  <parameter id="-sla-3-computer_guid">COMP-1234</parameter>
  <parameter id="-frontend-3-software-release-url">https://lab.nexedi.com/nexedi/slapos/raw/someid/software/caddy-frontend/software.cfg</parameter>


will request the third frontend on COMP-1234 and with SR https://lab.nexedi.com/nexedi/slapos/raw/someid/software/caddy-frontend/software.cfg. All frontends will be of software type ``custom-personal``. The second frontend will be requested with the state stopped.

*Note*: the way slaves are transformed to a parameter avoid modifying more than 3 lines in the frontend logic.

**Important NOTE**: The way you ask for slave to a replicate frontend is the same as the one you would use for the software given in "-frontend-quantity". Do not forget to use "replicate" for software type. XXXXX So far it is not possible to do a simple request on a replicate frontend if you do not know the software_guid or other sla-parameter of the master instance. In fact we do not know yet the software type of the "requested" frontends. TO BE IMPLEMENTED

XXX Should be moved to specific JSON File

Extra-parameter per frontend with default::

  ram-cache-size = 1G
  disk-cache-size = 8G

How to deploy a frontend server
===============================

This is to deploy an entire frontend server with a public IPv4.  If you want to use an already deployed frontend to make your service available via ipv4, switch to the "Example" parts.

First, you will need to request a "master" instance of Caddy Frontend with:

  * A ``domain`` parameter where the frontend will be available

like::

  <?xml version='1.0' encoding='utf-8'?>
  <instance>
   <parameter id="domain">moulefrite.org</parameter>
  </instance>

Then, it is possible to request many slave instances (currently only from slapconsole, UI doesn't work yet) of Caddy Frontend, like::

  instance = request(
    software_release=caddy_frontend,
    partition_reference='frontend2',
    shared=True,
    partition_parameter_kw={"url":"https://[1:2:3:4]:1234/someresource"}
  )

Those slave instances will be redirected to the "master" instance, and you will see on the "master" instance the associated proper directives of all slave instances.

Finally, the slave instance will be accessible from: https://someidentifier.moulefrite.org.

About SSL and SlapOS Master Zero Knowledge
==========================================

**IMPORTANT**: One Caddy can not serve more than one specific SSL site and be compatible with obsolete browser (i.e.: IE8). See http://wiki.apache.org/httpd/NameBasedSSLVHostsWithSNI

SSL keys and certificates are directly send to the frontend cluster in order to follow zero knowledge principle of SlapOS Master.

*Note*: Until master partition or slave specific certificate is uploaded each slave is served with fallback certificate.  This fallback certificate is self signed, does not match served hostname and results with lack of response on HTTPs.

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
Port used by Caddy. Optional parameter, defaults to 4443.

plain_http_port
~~~~~~~~~~~~~~~
Port used by Caddy to serve plain http (only used to redirect to https).
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

Thanks to using health-check it's possible to configure failover system. By providing `health-check-failover-url` or `health-check-failover-https-url` some special backend can be used to reply in case if original backend replies with error (codes like `5xx`). As a note one can setup this failover URL like `https://failover.example.com/?p=` so that the path from the incoming request will be passed as parameter. Additionally authentication to failover URL is supported with `health-check-authenticate-to-failover-backend` and SSL Proxy verification with `health-check-failover-ssl-proxy-verify` and `health-check-failover-ssl-proxy-ca-crt`.

Examples
========

Here are some example of how to make your SlapOS service available through an already deployed frontend.

Simple Example (default)
------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be
redirected and accessible from the proxy::

  instance = request(
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
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
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
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
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
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
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",

Simple Cache Example - XXX - to be written
------------------------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be::

  instance = request(
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
	"domain": "www.example.org",
	"enable_cache": "True",

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

  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 443 -j DNAT --to-destination {listening_ipv4}:4443
  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 80 -j DNAT --to-destination {listening_ipv4}:8080
  ip6tables -t nat -A PREROUTING -p tcp -d {public_ipv6} --dport 443 -j DNAT --to-destination {listening_ipv6}:4443
  ip6tables -t nat -A PREROUTING -p tcp -d {public_ipv6} --dport 80 -j DNAT --to-destination {listening_ipv6}:8080

Where ``{public_ipv[46]}`` is the public IP of your server, or at least the LAN IP to where your NAT will forward to, and ``{listening_ipv[46]}`` is the private ipv4 (like 10.0.34.123) that the instance is using and sending as connection parameter.

Additionally in order to access the server by itself such entries are needed in ``OUTPUT`` chain (as the internal packets won't appear in the ``PREROUTING`` chain)::

  iptables -t nat -A OUTPUT -p tcp -d {public_ipv4} --dport 443 -j DNAT --to {listening_ipv4}:4443
  iptables -t nat -A OUTPUT -p tcp -d {public_ipv4} --dport 80 -j DNAT --to {listening_ipv4}:8080
  ip6tables -t nat -A OUTPUT -p tcp -d {public_ipv6} --dport 443 -j DNAT --to {listening_ipv6}:4443
  ip6tables -t nat -A OUTPUT -p tcp -d {public_ipv6} --dport 80 -j DNAT --to {listening_ipv6}:8080

Solution 2 (network capability)
-------------------------------

It is also possible to directly allow the service to listen on 80 and 443 ports using the following command::

  setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$CADDY_FRONTEND_SOFTWARE_RELEASE_MD5/go.work/bin/caddy
  setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$CADDY_FRONTEND_SOFTWARE_RELEASE_MD5/parts/6tunnel/bin/6tunnel

Then specify in the master instance parameters:

 * set ``port`` to ``443``
 * set ``plain_http_port`` to ``80``

Authentication to the backend
=============================

The cluster generates CA served by caucase, available with ``backend-client-caucase-url`` return parameter.

Then, each slave configured with ``authenticate-to-backend`` to true, will use a certificate signed by this CA while accessing https backend.

This allows backends to:

 * restrict access only from some frontend clusters
 * trust values (like ``X-Forwarded-For``) sent by the frontend

Technical notes
===============

Profile development guidelines
------------------------------

Keep the naming in instance profiles:

 * ``software_parameter_dict`` for values coming from software
 * ``instance_parameter_dict`` for **local** values generated by the instance, except ``configuration``
 * ``slapparameter_dict`` for values coming from SlapOS Master

Instantiated cluster structure
------------------------------

Instantiating caddy-frontend results with a cluster in various partitions:

 * master (the controlling one)
 * kedifa (contains kedifa server)
 * frontend-node-N which contains the running processes to serve sites - this partition can be replicated by ``-frontend-quantity`` parameter

It means sites are served in ``frontend-node-N`` partition, and this partition is structured as:

 * Caddy serving the browser [client-facing-caddy]
 * (optional) Apache Traffic Server for caching [ats]
 * Haproxy as a way to communicate to the backend [backend-facing-haproxy]
 * some other additional tools (6tunnel, monitor, etc)

In case of slaves without cache (``enable_cache = False``) the request will travel as follows::

  client-facing-caddy --> backend-facing-haproxy --> backend

In case of slaves using cache (``enable_cache = True``) the request will travel as follows::

  client-facing-caddy --> ats --> backend-facing-haproxy --> backend

Usage of Haproxy as a relay to the backend allows much better control of the backend, removes the hassle of checking the backend from Caddy and allows future developments like client SSL certificates to the backend or even health checks.

Kedifa implementation
---------------------

`Kedifa <https://lab.nexedi.com/nexedi/kedifa>`_ server runs on kedifa partition.

Each `frontend-node-N` partition downloads certificates from the kedifa server.

Caucase (exposed by ``kedifa-caucase-url`` in master partition parameters) is used to handle certificates for authentication to kedifa server.

If ``automatic-internal-kedifa-caucase-csr`` is enabled (by default it is) there are scripts running on master partition to simulate human to sign certificates for each frontend-node-N node.

Support for X-Real-Ip and X-Forwarded-For
-----------------------------------------

X-Forwarded-For and X-Real-Ip are transmitted to the backend, but only for IPv4 access to the frontend. In case of IPv6 access, the provided IP will be wrong, because of using 6tunnel.

Automatic Internal Caucase CSR
------------------------------

Cluster is composed on many instances, which are landing on separate partitions, so some way is needed to bootstrap trust between the partitions.

There are two ways to achieve it:

 * use default, Automatic Internal Caucase CSR used to replace human to sign CSRs against internal CAUCASEs automatic bootstrap, which leads to some issues, described later
 * switch to manual bootstrap, which requires human to create and manage user certificate (with caucase-updater) and then sign new frontend nodes appearing in the system

The issues during automatic bootstrap are:

 * rouge or hacked SlapOS Master can result with adding rouge frontend nodes to the cluster, which will be trusted, so it will be possible to fetch all certificates and keys from Kedifa or to login to backends
 * when new node is added there is short window, when rouge person is able to trick automatic signing, and have it's own node added

In both cases promises will fail on node which is not able to get signed, but in case of Kedifa the damage already happened (certificates and keys are compromised). So in case if cluster administrator wants to stay on the safe side, both automatic bootstraps shall be turned off.

How the automatic signing works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Having in mind such structure:

 * instance with caucase: ``caucase-instance``
 * N instances which want to get their CSR signed: ``csr-instance``

In ``caucase-instance`` CAUCASE user is created by automatically signing one user certificate, which allows to sign service certificates.

The ``csr-instance`` creates CSR, extracts the ID of the CSR, exposes it via HTTP and ask caucase on ``caucase-instance`` to sign it. The ``caucase-instance`` checks that exposed CSR id matches the one send to caucase and by using created user to signs it.
