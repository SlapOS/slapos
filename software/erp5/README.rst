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

Included cloudooo partition is not recommended for intensive usage, and will
eventually be dropped. See the ``cloudooo`` software type to setup a cloudooo
cluster, more suitable for intensive usage.

.. _RewriteRules: http://httpd.apache.org/docs/current/en/mod/mod_rewrite.html#rewriterule
.. _VirtualHostMonster: http://docs.zope.org/zope2/zope2book/VirtualHosting.html
