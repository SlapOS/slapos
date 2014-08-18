zimbra-kvm
==========

Introduction
------------

Zimbra single-machine deployment inside of a virtual machine.


Internals
---------

The following ports are reachable from the outside world:
22 -> 2222
443 -> 4443
Others?

For each port, KVM does a NAT redirection from the VM to the local ipv4. Then, 6tunnel is called to redirect it to the outside world using ipv6.


Deployment
----------

To deploy a new Zimbra service, you just need to request a new instance of it,
then connect the the machine using ssh with root:zimbra credentials, reconfigure
Zimbra to use another domain name, and change root password.

Disk Image content
------------------

Ubuntu 12.04, Zimbra install from official packages, 8.0.3
admin password: Cedric de Saint Martin has it.
bind9: http://wiki.zimbra.com/index.php?title=Split_dns
resolv.conf: http://askubuntu.com/questions/30942/why-does-my-resolv-conf-file-get-regenerated-every-time


Todo
----

 * SMTP master/slave design implemented
 * Reverse proxy for web works
 * Automatically download the proper boot disk image.
 * Have two virtual disks: one for system/zimbra, one for data.
 * Unify smtp frontend and web frontend

