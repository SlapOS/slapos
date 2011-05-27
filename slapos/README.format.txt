format
======

slapformat is an application to prepare SlapOS ready node (machine).

It "formats" the machine by:

 - creating users and groups
 - creating bridge interface
 - creating needed tap interfaces
 - creating needed directories with proper ownership and permissions

In the end special report is generated and information are posted to
configured SlapOS server.

This program shall be only run by root.

Requirements
------------

Linux with IPv6, bridging and tap interface support.

Binaries:

 * brctl
 * groupadd
 * ip
 * tunctl
 * useradd
