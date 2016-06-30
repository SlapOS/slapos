kvm_frontend
=============

Introduction
------------

The ``slapos.recipe.kvm_frontend`` aims to provide proxy server to KVM instances.

It allows HTTPS IPv4/IPv6 proxying (with or without domain name), and supports
the WebSocket technology needed for VNC-in-webapplication noVNC.

It works following the master/slave instances system. A master instance is
created, containing all what is needed to run the proxy. Slave instances
are later created, adding one line in the master instance's proxy configuration
that specify the IP/port to proxy to the KVM.

The slave instance (kvm) is then accessible from
http://[masterinstanceIPorhostname]/[randomgeneratednumber]


Instance parameters
------------

Incoming master instance parameters
+++++++

``port``                - Port of server, optional, defaults to 4443.
``domain``              - domain name to use, optional, default to
                          "host.vifib.net".
``redirect_plain_http`` - if value is one of ['y', 'yes', '1', 'true'], instance
                          will try to create a simple http server on port 80
                          redirecting to the proxy. Optional.

Incoming slave instance parameters
+++++++

``host``    - KVM instance IP or hostname. Mandatory.
``port``    - KVM instance port, Mandatory.
``https``   - if value is one of ['n', 'no', '0', 'false'], will try to connect
              to target in plain http. Optional.

Connection parameters
-------------

Outgoing master connection parameters
+++++++

``domain_ipv6_address``  - Proxy IP
``site_url``             - Proxy URL

Outgoing slave connection parameters are :
+++++++

``site_url``             - URL of instance
``domain_name``          - Domain name of proxy
``port``                 - Port of proxy
