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

Replication
===========

Replication allows setting up an ERP5 instance whose data follows another
instance.

Relations between ERP5 instances in a replication graph depend in what is
supported by individual data managers (ex: a neo cluster can replicate from a
neo cluster which itself replicates from a 3rd).

Replication lag constraints (aka sync/async replication) depends on individual
data managers (ex: neo replication between clusters is always asynchronous).

Ignoring replication lag, replicated data can be strictly identical (ex:
replicating ZODB or SQL database will contain the same data as upstream), or
may imply some remaping (ex: replicating Zope logs from an instance with 2 zope
families with 2 partition of 2 zopes each to an instance with a single zope
total).

Data whose replication is supported
-----------------------------------

- neo database

Data whose replication will eventually be supported
---------------------------------------------------

- mariadb database
- zope ``zope-*-access.log`` and ``zope-*-Z2.log``
- ``mariadb-slow.log``

Data whose replication is not planned
-------------------------------------

- zeo: use neo instead

Setting up replication
----------------------

In addition to your usual parameter set, you needs to provide the following parameters::

  {
    "zope-partition-dict": {},      So no zope is instanciated
    "zodb": [
      {
        "storage-dict": {
          "upstream-masters": ...,  As published by to-become upstream ERP5 instance as "neo-masters"
        },
        "type": "neo",              The only ZODB type supporting replication
        ...
      }
      ...
    ]
    ...
  }

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
