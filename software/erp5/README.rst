Available ``software-type`` values
==================================

- ``default``

  Recommended for production use.
  
- ``create-erp5-site``

  Automated creation of ERP5Site instance, for easy deployment.
  Usage in production discouraged due to the increased risk of data loss.

Notes
=====

This software release is not intended to be accessed directly, but through a
front-end instance which is expected to contains the RewriteRules_ (or
equivalent) needed to relocate Zope's urls via its VirtualHostMonster_. See the
``frontend`` erp5 instance parameter.

Included cloudooo partition is **deprecated**. It is not recommended for
intensive usage. See the ``cloudooo`` Software Release to setup a cloudooo
cluster, more suitable for intensive usage.

Port ranges
===========

This software release assigns the following port ranges by default:

  ====================  ==========
  Partition type        Port range
  ====================  ==========
  memcached-persistent  2000-2009
  memcached-volatile    2010-2019
  cloudooo              2020-2024
  smtp                  2025-2029
  neo (admin & master)  2050-2051
  mariadb               2099
  zeo                   2100-2149
  balancer              2150-2199
  zope                  2200-*
  jupyter               8888
  ====================  ==========

Non-zope partitions are unique in an ERP5 cluster, so you shouldn't have to
care about them as a user (but a Software Release developer needs to know
them).

Zope partitions should be assigned port ranges starting at 2200, incrementing
by some value which depends on how many zope process you want per partition
(see the ``port-base`` parameter in ``zope-partition-dict``).

Notes to the Software Release developper: These ranges are not strictly
defined. Not each port is actually used so one may reduce alread-assigned
ranges if needed (ex: memcached partitions use actually fewer ports). There
should be enough room for evolution (as between smtp and mariadb types). It is
important to not allocate any port after 2200 as user may have assigned ports
to his zope processes.

.. _RewriteRules: http://httpd.apache.org/docs/current/en/mod/mod_rewrite.html#rewriterule
.. _VirtualHostMonster: http://docs.zope.org/zope2/zope2book/VirtualHosting.html
