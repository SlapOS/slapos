zimbra-kvm
==========

Introduction
------------

Zimbra single-machine deployment inside of a virtual machine.


Internals
---------

The following ports are reachable from the outside world:
22 -> 2222
443 -> 443
80 -> 80
25 -> 25

For each port, KVM does a NAT redirection from the VM to the local ipv4. Then, 6tunnel is called to redirect it to the outside world using ipv6.


Hostnames configuration
-----------------------

Here, zimbra.memi.slapos.org is an example. You can replace it by whatever you own (www.mydomain.com).

# HTTP reverse proxy
zimbra.memi.slapos.org 10800 IN A 5.135.166.224
zimbra.memi.slapos.org 10800 IN AAAA 2001:67c:1254:e:b::418
# MX
zimbra.memi.slapos.org 10800 IN MX 10 mail.zimbra.memi.slapos.org.
# SMTP reverse inbound synchronous proxy
mail.zimbra.memi.slapos.org 10800 IN A 5.135.166.224
mail.zimbra.memi.slapos.org 10800 IN AAAA 2001:67c:1254:9:bde1:7e1e:45b3:b189


Important note about architecture
---------------------------------

the Zimbra inside of the KVM doesn't have any connection to the internet
except a tunnel to the external MTA on the frontend machine.
Any outgoing mail uses this tunnel.


Deployment
----------

To deploy a new Zimbra service:

 * Install the SR, and run the commands to allow non-root users to run kvm with ports listening <1024::

   setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$SRMD5/parts/kvm/bin/qemu-system-x86_64
   setcap 'cap_net_bind_service=+ep' /opt/slapgrid/$SRMD5/parts/6tunnel/bin/6tunnel

 * Deploy an instance of zimbra-kvm with parameters, replacing by your informations::

   <?xml version='1.0' encoding='utf-8'?>
   <instance>
   <parameter id="domain">zimbra.memi.slapos.org</parameter>
   <parameter id="ram-size">30000</parameter>
   <parameter id="relay-mta-ipv6">2001:67c:1254:e:b::1</parameter>
   </instance>

 * Connect to VNC and install a ubuntu server 12.04 in it.

 * Then from raw Ubuntu 12.04:

   1/ Populate /etc/hosts::

     127.0.0.1 zimbra.memi.slapos.org

   2/ Setup hostname::

     hostname zimbra.memi.slapos.org
     echo "zimbra.memi.slapos.org"> /etc/hostname

   3/ Setup /etc/resolv.conf::

     echo "nameserver 127.0.0.1" > /etc/resolvconf/resolv.conf.d/base
     echo "nameserver 127.0.0.1" > /etc/resolv.conf

   4/ Setup bind by following http://wiki.zimbra.com/index.php?title=Split_dns, and disable dnssec checking in named.conf.options with::

      dnssec-enable no; dnssec-validation no;

   5/ Add automatic security upgrades::

     ln -s $(which unattended-upgrade) /etc/cron.daily


   6/ Download Zimbra Community edition 8.0.x and install it the standard way, selecting packages by default and setting password.

   6bis/ There are chances you need to add zimbra start at boot::

     update-rc.d zimbra defaults

   7/ In Zimbra admin web interface: Configure -> Server -> MTA -> MTA realy: put local IPv4 of your slapos instance.


Todo
----

 * SMTP master/slave design implemented
 * Automatically download the proper boot disk image
 * Unify smtp frontend and web frontend
