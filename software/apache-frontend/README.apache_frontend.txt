apache_frontend
===============

Frontend system using Apache, allowing to rewrite and proxy URLs like
myinstance.myfrontenddomainname.com to real IP/URL of myinstance.

apache_frontend works using the master instance / slave instance design.
It means that a single main instance of Apache will be used to act as frontend
for many slaves.


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


How to have custom configuration in frontend server
===================================================

In your instance directory, you, as sysadmin, can directly edit two
configuration files that won't be overwritten by SlapOS to customize your
instance:

 * $PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.custom.conf
 * $PARTITION_PATH/srv/srv/apache-conf.d/apache_frontend.virtualhost.custom.conf

The first one is included in the end of the main apache configuration file.
The second one is included in the virtualhost of the main apache configuration file.

SlapOS will jsut create those two files for you, then completely forget them.

Note: make sure that the UNIX user of the instance has read access to those
files if you edit them.

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

port
~~~~
Port used by Apache. Optional parameter, defaults to 4443.

plain_http_port
~~~~~~~~~~~~~~~
Port used by apache to serve plain http (only used to redirect to https).
Optional parameter, defaults to 8080.

Slave Instance Parameters
-------------------------

url
~~~
url of backend to use.
"url" is a mandatory parameter.
Example: http://mybackend.com/myresource

enable_cache
~~~~~
Specify if slave instance should use a varnish / stunnel to connect to backend.
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

custom_domain
~~~~~~~~~~~~~
Domain name to use as frontend. The frontend will be accessible from this domain.
"custom_domain" is an optional parameter. Defaults to
[instancereference].[masterdomain].
Example: www.mycustomdomain.com

path
~~~~
Only used if type is "zope".

Will append the specified path to the "VirtualHostRoot" of the zope's
VirtualHostMonster.

"path" is an optional parameter, ignored if not specified.
Example of value: "/erp5/web_site_module/hosting/"

Examples
========

Here are some example of how to make your SlapOS service available through
an already deployed frontend.

Simple Example
--------------

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


Zope Example
------------

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


Advanced example
----------------

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
        "custom_domain":"mycustomdomain.com",
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
