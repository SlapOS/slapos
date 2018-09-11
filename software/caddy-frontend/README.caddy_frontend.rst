==============
Caddy Frontend
==============

Frontend system using Caddy, based on apache-frontend software release, allowing to rewrite and proxy URLs like myinstance.myfrontenddomainname.com to real IP/URL of myinstance.

Caddy Frontend works using the master instance / slave instance design.  It means that a single main instance of Caddy will be used to act as frontend for many slaves.

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

These parameters are :

  * ``-frontend-type`` : the type to deploy frontends with. (default to 2)
  * ``-frontend-quantity`` : The quantity of frontends to request (default to "default")
  * ``-frontend-i-state``: The state of frontend i
  * ``-frontend-config-i-foo``: Frontend i will be requested with parameter foo
  * ``-frontend-software-release-url``: Software release to be used for frontends, default to the current software release
  * ``-sla-i-foo`` : where "i" is the number of the concerned frontend (between 1 and "-frontend-quantity") and "foo" a sla parameter.

ex::

  <parameter id="-frontend-quantity">3</parameter>
  <parameter id="-frontend-type">custom-personal</parameter>
  <parameter id="-frontend-2-state">stopped</parameter>
  <parameter id="-sla-3-computer_guid">COMP-1234</parameter>
  <parameter id="-frontend-software-release-url">https://lab.nexedi.com/nexedi/slapos/raw/someid/software/caddy-frontend/software.cfg</parameter>


will request the third frontend on COMP-1234. All frontends will be of software type ``custom-personal``. The second frontend will be requested with the state stopped

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
  * A ``public-ipv4`` parameter to state which public IPv4 will be used

like::

  <?xml version='1.0' encoding='utf-8'?>
  <instance>
   <parameter id="domain">moulefrite.org</parameter>
   <parameter id="public-ipv4">xxx.xxx.xxx.xxx</parameter>
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

About SSL
=========

``default`` and ``custom-personl`` software type can handle specific ssl for one slave instance.

**IMPORTANT**: One Caddy can not serve more than one specific SSL site and be compatible with obsolete browser (i.e.: IE8). See http://wiki.apache.org/httpd/NameBasedSSLVHostsWithSNI

How to have custom configuration in frontend server - XXX - to be written
=========================================================================

In your instance directory, you, as sysadmin, can directly edit two
configuration files that won't be overwritten by SlapOS to customize your
instance:

 * ``$PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.custom.conf``
 * ``$PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.virtualhost.custom.conf``

The first one is included in the end of the main apache configuration file.
The second one is included in the virtualhost of the main apache configuration file.

SlapOS will just create those two files for you, then completely forget them.

*Note*: make sure that the UNIX user of the instance has read access to those
files if you edit them.

Instance Parameters
===================

Master Instance Parameters
--------------------------

The parameters for instances are described at `instance-caddy-input-schema.json <instance-caddy-input-schema.json>`_.

Here some additional informations about the parameters listed, below:

domain
~~~~~~

Name of the domain to be used (example: mydomain.com). Sub domains of this domain will be used for the slave instances (example: instance12345.mydomain.com). It is then recommended to add a wild card in DNS for the sub domains of the chosen domain like::

  *.mydomain.com. IN A 123.123.123.123

Using the IP given by the Master Instance.  "domain" is a mandatory Parameter.

public-ipv4
~~~~~~~~~~~
Public ipv4 of the frontend (the one Caddy will be indirectly listening to)

port
~~~~
Port used by Caddy. Optional parameter, defaults to 4443.

plain_http_port
~~~~~~~~~~~~~~~
Port used by Caddy to serve plain http (only used to redirect to https).
Optional parameter, defaults to 8080.


Slave Instance Parameters
-------------------------

The parameters for instances are described at `instance-slave-caddy-input-schema.json <instance-slave-caddy-input-schema.json>`_.

Here some additional informations about the parameters listed, below:

path
~~~~
Only used if type is "zope".

Will append the specified path to the "VirtualHostRoot" of the zope's VirtualHostMonster.

"path" is an optional parameter, ignored if not specified.
Example of value: "/erp5/web_site_module/hosting/"

caddy_custom_https
~~~~~~~~~~~~~~~~~~
Raw Caddy configuration in python template format (i.e. write "%%" for one "%") for the slave listening to the https port. Its content will be templatified in order to access functionalities such as cache access, ssl certificates... The list is available above.

*Note*: The system will reject slaves which does not pass validation of caddy configuration, despite them being in ``-frontend-authorized-slave-string``, as otherwise this will lead to the whole frontend to fail.

caddy_custom_http
~~~~~~~~~~~~~~~~~
Raw Caddy configuration in python template format (i.e. write "%%" for one "%") for the slave listening to the http port. Its content will be templatified in order to access functionalities such as cache access, ssl certificates... The list is available above

*Note*: The system will reject slaves which does not pass validation of caddy configuration, despite them being in ``-frontend-authorized-slave-string``, as otherwise this will lead to the whole frontend to fail.

url
~~~
Necessary to activate cache. ``url`` of backend to use.

``url`` is an optional parameter.

Example: http://mybackend.com/myresource

domain
~~~~~~

Necessary to activate cache.

The frontend will be accessible from this domain.

``domain`` is an optional parameter.

Example: www.mycustomdomain.com

enable_cache
~~~~~~~~~~~~

Necessary to activate cache.

``enable_cache`` is an optional parameter.

ssl_key, ssl_crt, ssl_ca_crt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SSL certificates of the slave.

They are optional.

Functionalities for Caddy configuration
---------------------------------------

In the slave Caddy configuration you can use parameters that will be replaced during instantiation. They should be entered as python templates parameters ex: ``%(parameter)s``:

  * ``cache_access`` : url of the cache. Should replace backend url in configuration to use the cache
  * ``access_log`` : path of the slave error log in order to log in a file.
  * ``error_log`` : path of the slave access log in order to log in a file.
  * ``ssl_key``, ``ssl_crt``, ``ssl_ca_crt``, ``ssl_crs`` : paths of the certificates given in slave instance parameters


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

        "caddy_custom_https":'
  https://www.example.com:%(https_port)s, https://example.com:%(https_port)s {
    bind %(local_ipv4)s
    tls %(ssl_crt)s %(ssl_key)s

    log / %(access_log)s {combined}
    errors %(error_log)s

    proxy / https://[1:2:3:4:5:6:7:8]:1234 {
      transparent
      timeout 600s
      insecure_skip_verify
    }
  }
        "caddy_custom_http":'
  http://www.example.com:%(http_port)s, http://example.com:%(http_port)s {
    bind %(local_ipv4)s
    log / %(access_log)s {combined}
    errors %(error_log)s
  
    proxy / https://[1:2:3:4:5:6:7:8]:1234/ {
      transparent
      timeout 600s
      insecure_skip_verify
    }
  }

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

        "caddy_custom_https":'
  ServerName www.example.org
  ServerAlias www.example.org
  ServerAlias example.org
  ServerAdmin geronimo@example.org
  SSLEngine on
  SSLProxyEngine on
  # Rewrite part
  ProxyVia On
  ProxyPreserveHost On
  ProxyTimeout 600
  RewriteEngine On
  RewriteRule ^/(.*) %(cache_access)s/$1 [L,P]',

        "caddy_custom_http":'
  ServerName www.example.org
  ServerAlias www.example.org
  ServerAlias example.org
  ServerAdmin geronimo@example.org
  SSLProxyEngine on
  # Rewrite part
  ProxyVia On
  ProxyPreserveHost On
  ProxyTimeout 600
  RewriteEngine On

  # Not using HTTPS? Ask that guy over there.
  # Dummy redirection to https. Note: will work only if https listens
  # on standard port (443).
  RewriteRule ^/(.*) %(cache_access)s/$1 [L,P],
    }
  )


Advanced example - XXX - to be written
--------------------------------------

Request slave frontend instance using custom apache configuration, willing to use cache and ssl certificates.
Listening to a custom domain and redirecting to /erp5/ so that
https://[1:2:3:4:5:6:7:8]:1234/erp5/ will be redirected and accessible from
the proxy::

  instance = request(
    software_release=caddy_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
        "enable_cache":"true",
        "type":"zope",
        "path":"/erp5",
        "domain":"example.org",

  	"caddy_custom_https":'
  ServerName www.example.org
  ServerAlias www.example.org
  ServerAdmin example.org
  SSLEngine on
  SSLProxyEngine on
  SSLProtocol all -SSLv2 -SSLv3
  SSLCipherSuite ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:HIGH:!aNULL:!MD5
  SSLHonorCipherOrder on
  # Use personal ssl certificates
  SSLCertificateFile %(ssl_crt)s
  SSLCertificateKeyFile %(ssl_key)s
  SSLCACertificateFile %(ssl_ca_crt)s
  SSLCertificateChainFile %(ssl_ca_crt)s
  # Configure personal logs
  ErrorLog "%(error_log)s"
  LogLevel info
  LogFormat "%%h %%l %%{REMOTE_USER}i %%t \"%%r\" %%>s %%b \"%%{Referer}i\" \"%%{User-Agent}i\" %%D" combined
  CustomLog "%(access_log)s" combined
  # Rewrite part
  ProxyVia On
  ProxyPreserveHost On
  ProxyTimeout 600
  RewriteEngine On
  # Redirect / to /index.html
  RewriteRule ^/$ /index.html [R=302,L]
  # Use cache
  RewriteRule ^/(.*) %(cache_access)s/VirtualHostBase/https/www.example.org:443/erp5/VirtualHostRoot/$1 [L,P]',

    "caddy_custom_http":'
  ServerName www.example.org
  ServerAlias www.example.org
  ServerAlias example.org
  ServerAdmin geronimo@example.org
  SSLProxyEngine on
  # Rewrite part
  ProxyVia On
  ProxyPreserveHost On
  ProxyTimeout 600
  RewriteEngine On
  # Configure personal logs
  ErrorLog "%(error_log)s"
  LogLevel info
  LogFormat "%%h %%l %%{REMOTE_USER}i %%t \"%%r\" %%>s %%b \"%%{Referer}i\" \"%%{User-Agent}i\" %%D" combined
  CustomLog "%(access_log)s" combined
  # Not using HTTPS? Ask that guy over there.
  # Dummy redirection to https. Note: will work only if https listens
  # on standard port (443).
  RewriteRule ^/(.*)$ https://%%{SERVER_NAME}%%{REQUEST_URI}',

    "ssl_key":"-----BEGIN RSA PRIVATE KEY-----
  XXXXXXX..........XXXXXXXXXXXXXXX
  -----END RSA PRIVATE KEY-----",
      "ssl_crt":'-----BEGIN CERTIFICATE-----
  XXXXXXXXXXX.............XXXXXXXXXXXXXXXXXXX
  -----END CERTIFICATE-----',
      "ssl_ca_crt":'-----BEGIN CERTIFICATE-----
  XXXXXXXXX...........XXXXXXXXXXXXXXXXX
  -----END CERTIFICATE-----',
      "ssl_csr":'-----BEGIN CERTIFICATE REQUEST-----
  XXXXXXXXXXXXXXX.............XXXXXXXXXXXXXXXXXX
  -----END CERTIFICATE REQUEST-----',
    }
  )

QUIC Protocol
=============

Experimental QUIC available in Caddy is not configurable, thus it is required to open port ``udp:11443`` on the machine, like::

  iptables -I INPUT -p udp --dport 11443 --destination ${ip} -j ACCEPT

where ``${ip}`` is the IP of the partition with running caddy process.


Notes
=====

It is not possible with slapos to listen to port <= 1024, because process are
not run as root.

Solution 1 (IPv4 only)
----------------------

It is a good idea then to go on the node where the instance is
and set some ``iptables`` rules like (if using default ports)::

  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 443 -j DNAT --to-destination {listening_ipv4}:4443
  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 80 -j DNAT --to-destination {listening_ipv4}:8080

Where ``{public ip}`` is the public IP of your server, or at least the LAN IP to where your NAT will forward to, and ``{listening ip}`` is the private ipv4 (like 10.0.34.123) that the instance is using and sending as connection parameter.

Solution 2 (IPv6 only)
----------------------

It is also possible to directly allow the service to listen on 80 and 443 ports using the following command::

  setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$CADDY_FRONTEND_SOFTWARE_RELEASE_MD5/go.work/bin/caddy

Then specify in the instance parameters ``port`` and ``plain_http_port`` to be ``443`` and ``80``, respectively.
