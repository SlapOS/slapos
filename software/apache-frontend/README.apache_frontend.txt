apache_frontend
===============

Frontend system using Apache, allowing to rewrite and proxy URLs like
myinstance.myfrontenddomainname.com to real IP/URL of myinstance.

apache_frontend works using the master instance / slave instance design.
It means that a single main instance of Apache will be used to act as frontend
for many slaves.

Software type
=============

Apache frontend is available in 3 software types:
  * default : The standard way to use the apache frontend configuring everything with a few given parameters
  * custom-personal : This software type allow each slave to edit its apache configuration file
  * custom-group : This software type use a template given as a parameter on master instance to generate apache configuration for all slaves
  * replicate : This software type is set to replicate any kind of apache

About replicate frontend
========================

Slaves of the root instance (type "replicate") are sent as a parameter to requested frontends which will process them. The only difference is that they will then return the « would-be published information » to the root instance instead of publishing it. The root instance will then do a synthesis and publish the information to its slaves. The replicate instance only use 4 type of parameters for itself and will transmit the rest to requested frontends.
These parameters are :
  * "-frontend-type" : the type to deploy frontends with. (default to 2)
  * "-frontend-quantity" : The quantity of frontends to request (default to "default")
  * "-frontend-i-state": The state of frontend i
  * "-sla-i-foo" : where "i" is the number of the concerned frontend (between 1 and "-frontend-quantity") and "foo" a sla parameter.
ex:
<parameter id="-frontend-quantity">3</parameter>
<parameter id="-frontend-type">custom-personal</parameter>
<parameter id="-frontend-2-state">stopped</parameter>
<parameter id="-sla-3-computer_guid">COMP-1234</parameter>
will request the third frontend on COMP-1234. All frontends will be of software type "custom-personal". The second frontend will be requested with the state stopped

Note: the way slaves are transformed to a parameter avoid modifying more than 3 lines in the frontend logic.
Important NOTE: The way you ask for slave to a replicate frontend is the same as the one you would use for the software given in "-frontend-quantity". Do not forget to use "replicate" for software type. XXXXX So far it is not possible to do a simple request on a replicate frontend if you do not know the software_guid or other sla-parameter of the master instance. In fact we do not know yet the software type of the "requested" frontends. TO BE IMPLEMENTED

How to deploy a frontend server
===============================

This is to deploy an entire frontend server with a public IPv4.
If you want to use an already deployed frontend to make your service available
via ipv4, switch to the "Example" parts.

First, you will need to request a "master" instance of Apache Frontend with:
  * A "domain" parameter where the frontend will be available
  * A "public-ipv4" parameter to state which public IPv4 will be used

like::
  <?xml version='1.0' encoding='utf-8'?>
  <instance>
   <parameter id="domain">moulefrite.org</parameter>
   <parameter id="public-ipv4">xxx.xxx.xxx.xxx</parameter>
  </instance>

Then, it is possible to request many slave instances
(currently only from slapconsole, UI doesn't work yet)
of Apache Frontend, like::
  instance = request(
    software_release=apache_frontend,
    partition_reference='frontend2',
    shared=True,
    partition_parameter_kw={"url":"https://[1:2:3:4]:1234/someresource"}
  )
Those slave instances will be redirected to the "master" instance,
and you will see on the "master" instance the associated RewriteRules of
all slave instances.

Finally, the slave instance will be accessible from:
https://someidentifier.moulefrite.org.

About SSL
=========
Default and custom-personal software type can handle specific ssl for one slave instance.
IMPORTANT: One apache can not serve more than One specific SSL VirtualHost and be compatible with obsolete browser (i.e.: IE8). See http://wiki.apache.org/httpd/NameBasedSSLVHostsWithSNI

#How to have custom configuration in frontend server
#===================================================
#
#In your instance directory, you, as sysadmin, can directly edit two
#configuration files that won't be overwritten by SlapOS to customize your
#instance:
#
# * $PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.custom.conf
# * $PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.virtualhost.custom.conf
#
#The first one is included in the end of the main apache configuration file.
#The second one is included in the virtualhost of the main apache configuration file.
#
#SlapOS will jsut create those two files for you, then completely forget them.
#
#Note: make sure that the UNIX user of the instance has read access to those
#files if you edit them.

Instance Parameters
===================

Master Instance Parameters
--------------------------

domain
~~~~~~
name of the domain to be used (example: mydomain.com). Subdomains of this
domain will be used for the slave instances (example:
instance12345.mydomain.com). It is then recommended to add a wildcard in DNS
for the subdomains of the chosen domain like::
  *.mydomain.com. IN A 123.123.123.123
Using the IP given by the Master Instance.
"domain" is a mandatory Parameter.

public-ipv4
~~~~~~~~~~~
Public ipv4 of the frontend (the one Apache will be indirectly listening to)

port
~~~~
Port used by Apache. Optional parameter, defaults to 4443.

plain_http_port
~~~~~~~~~~~~~~~
Port used by apache to serve plain http (only used to redirect to https).
Optional parameter, defaults to 8080.

ip-read-limit
~~~~~~~~~~~~~
Use to set IPReadLimit Parameter for antiloris.
Optional parameter, defaults to 10.

apache_custom_http (custom-group)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Jinja template for apache virtualhost http configuration. It will be used by all slaves

apache_custom_https (custom-group)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Jinja template for apache virtualhost https configuration. It will be used by all slaves


Slave Instance Parameters (default)
-----------------------------------

url
~~~
url of backend to use.
"url" is a mandatory parameter.
Example: http://mybackend.com/myresource

enable_cache
~~~~~
Specify if slave instance should use a squid to connect to backend.
Possible values: "true", "false".
"enable_cache" is an optional parameter. Defaults to "false".
Example: true

type
~~~~
Specify if slave instance will redirect to a zope backend. If specified, Apache
RewriteRule will use Zope's Virtual Host Daemon.
Possible values: "zope", "default".
"type" is an optional parameter. Defaults to "default".
Example: zope

domain (former custom_domain)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Domain name to use as frontend. The frontend will be accessible from this domain.
"domain" is an optional parameter. Defaults to
[instancereference].[masterdomain].
Example: www.mycustomdomain.com

https-only
~~~~~~~~~~
Specify if website should be accessed using https only. If so, the frontend
will redirect the user to https if accessed from http.
Possible values: "true", "false".
"https-only" is an optional parameter. Defaults to "false".
Example: true

path
~~~~
Only used if type is "zope".

Will append the specified path to the "VirtualHostRoot" of the zope's
VirtualHostMonster.

"path" is an optional parameter, ignored if not specified.
Example of value: "/erp5/web_site_module/hosting/"

Slave Instance Parameters (custom-personal)
-------------------------------------------

apache_custom_https
~~~~~~~~~~~~~~~~~~~
Raw apache configuration in python template format (i.e. write "%%" for one "%") for the slave listening to the https port. Its content will be templatified in order to access functionalities such as cache access, ssl certificates... The list is available above.
NOTE: If you want to use the cache, use the apache option "ProxyPreserveHost On"

apache_custom_http
~~~~~~~~~~~~~~~~~~
Raw apache configuration in python template format (i.e. write "%%" for one "%") for the slave listening to the http port. Its content will be templatified in order to access functionalities such as cache access, ssl certificates... The list is available above
NOTE: If you want to use the cache, use the apache option "ProxyPreserveHost On"

url
~~~
Necesarry to activate cache. url of backend to use.
"url" is an optional parameter.
Example: http://mybackend.com/myresource

domain
~~~~~~
Necesarry to activate cache. The frontend will be accessible from this domain.
"domain" is an optional parameter.
Example: www.mycustomdomain.com

enable_cache
~~~~~~~~~~~~
Necesarry to activate cache.
"enable_cache" is an optional parameter.

ssl_key, ssl_crt, ssl_ca_crt, ssl_crs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SSL certificates of the slave.
They are optional.

Functionalities for apache configuration:
In the slave apache configuration you can use parameters that will be replaced during instanciation. They should be entered as python templates parameters ex:" %(parameter)s"
  * cache_access : url of the cache. Should replace backend url in configuration to use the cache
  * error_log : path of the slave error log in order to log in a deferenciated file.
  * error_log : path of the slave access log in order to log in a deferenciated file.
  * ssl_key, ssl_crt, ssl_ca_crt, ssl_crs : path of the certificates given in slave instance parameters

Slave Instance Parameters (custom-group)
----------------------------------------

url
~~~
Necesarry to activate cache. url of backend to use.
"url" is an optional parameter.
Example: http://mybackend.com/myresource

domain
~~~~~~
Domain name to use as frontend. The frontend will be accessible from this domain.
"domain" is an optional parameter necessary to activate cache. Defaults to
[instancereference].[masterdomain].
Example: www.mycustomdomain.com

The rest of the parameters are defined by templates given to the master and accessible by the slave_parameter dict in it.


Examples
========

Here are some example of how to make your SlapOS service available through
an already deployed frontend.

Simple Example (default)
------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be
redirected and accessible from the proxy::
  instance = request(
    software_release=apache_frontend,
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
    software_release=apache_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
        "type":"zope",
    }
  )


Advanced example (default)
--------------------------

Request slave frontend instance using a Zope backend, with Varnish activated,
listening to a custom domain and redirecting to /erp5/ so that
https://[1:2:3:4:5:6:7:8]:1234/erp5/ will be redirected and accessible from
the proxy::
  instance = request(
    software_release=apache_frontend,
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

Simple Example (custom-personal)
--------------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be
  instance = request(
    software_release=apache_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",

        "apache_custom_https":'
  ServerName www.example.org
  ServerAlias example.org
  ServerAdmin geronimo@example.org
  SSLEngine on
  SSLProxyEngine on
  # Rewrite part
  ProxyVia On
  ProxyPreserveHost On
  ProxyTimeout 600
  RewriteEngine On
  RewriteRule ^/(.*) https://[1:2:3:4:5:6:7:8]:1234/$1 [L,P]',

        "apache_custom_http":'
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
  # Remove "Secure" from cookies, as backend may be https
  Header edit Set-Cookie "(?i)^(.+);secure$" "$1"
  # Not using HTTPS? Ask that guy over there.
  # Dummy redirection to https. Note: will work only if https listens
  # on standard port (443).
  RewriteRule ^/(.*) https://[1:2:3:4:5:6:7:8]:1234/$1 [L,P],
    }
  )

Simple Cache Example (custom-personal)
--------------------------------

Request slave frontend instance so that https://[1:2:3:4:5:6:7:8]:1234 will be
  instance = request(
    software_release=apache_frontend,
    software_type="RootSoftwareInstance",
    partition_reference='my frontend',
    shared=True,
    software_type="custom-personal",
    partition_parameter_kw={
        "url":"https://[1:2:3:4:5:6:7:8]:1234",
	"domain": "www.example.org",
	"enable_cache": "True",

        "apache_custom_https":'
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

        "apache_custom_http":'
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

  # Remove "Secure" from cookies, as backend may be https
  Header edit Set-Cookie "(?i)^(.+);secure$" "$1"

  # Not using HTTPS? Ask that guy over there.
  # Dummy redirection to https. Note: will work only if https listens
  # on standard port (443).
  RewriteRule ^/(.*) %(cache_access)s/$1 [L,P],
    }
  )


Advanced example (custom-personal)
----------------------------------

Request slave frontend instance using custom apache configuration, willing to use cache and ssl certificates.
listening to a custom domain and redirecting to /erp5/ so that
https://[1:2:3:4:5:6:7:8]:1234/erp5/ will be redirected and accessible from
the proxy::
  instance = request(
    software_release=apache_frontend,
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

  	"apache_custom_https":'
  ServerName www.example.org
  ServerAlias www.example.org
  ServerAdmin example.org
  SSLEngine on
  SSLProxyEngine on
  SSLProtocol -ALL +SSLv3 +TLSv1
  SSLHonorCipherOrder On
  SSLCipherSuite RC4-SHA:HIGH:!ADH
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

    "apache_custom_http":'
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
  # Remove "Secure" from cookies, as backend may be https
  Header edit Set-Cookie "(?i)^(.+);secure$" "$1"
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

Notes
=====

It is not possible with slapos to listen to port <= 1024, because process are
not run as root.

Solution 1 (IPv4 only)
----------------------

It is a good idea then to go on the node where the instance is
and set some iptables rules like (if using default ports)::

  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 443 -j DNAT --to-destination {listening_ipv4}:4443
  iptables -t nat -A PREROUTING -p tcp -d {public_ipv4} --dport 80 -j DNAT --to-destination {listening_ipv4}:8080

Where {public ip} is the public IP of your server, or at least the LAN IP to where your NAT will forward to.
{listening ip} is the private ipv4 (like 10.0.34.123) that the instance is using and sending as connection parameter.

Solution 2 (IPv6 only)
----------------------

It is also possible to directly allow the service to listen on 80 and 443 ports using the following command:

  setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$APACHE_FRONTEND_SOFTWARE_RELEASE_MD5/parts/apache-2.2/bin/httpd

Then specify in the instance parameters "port" and "plain_http_port" to be 443 and 80, respectively.
