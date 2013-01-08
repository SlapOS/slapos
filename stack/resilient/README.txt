
Base resilient stack
====================

This stack is meant to be extended by SR profiles, or other stacks, that need to provide
automated backup/restore, election of backup candidates, and instance failover.

As reference implementations, both stack/lamp and stack/lapp define resilient behavior for
MySQL and Postgres respectively.

This involves three different software_types:

 * pull-backup
 * {something}_export
 * {something}_import

where 'something' is the component that needs resiliency (can be postgres, mysql, erp5, and so on).


pull-backup
-----------

This software type is defined in

    http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/stack/resilient/instance-pull-backup.cfg.in?js=1

and there should be no reason to modify or extend it.

An instance of type 'pull-backup' will receive data from an 'export' instance and immediately populate an 'import' instance.
The backup data is automatically used to build an historical, incremental archive in srv/backup/pbs.


export
------

example:
    http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/stack/lapp/postgres/instance-postgres-export.cfg.in?js=1

This is the *active* instance - the one providing live data to the application.

A backup is run via the bin/exporter script: it will
     1) run bin/{something}-backup
 and 2) notify the pull-backup instance that data is ready.

The pull-backup, upon receiving the notification, will make a copy of the data and transmit it to the 'import' instances.

You should provide the bin/{something}-exporter script, see for instance
  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/postgres/__init__.py?js=1#l207
  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/mydumper.py?js=1#l71

By default, as defined in
  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/stack/resilient/pbsready-export.cfg.in?js=1#l27
the bin/exporter script is run every 60 minutes.



import
------

example:
    http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/stack/lapp/postgres/instance-postgres-import.cfg.in?js=1

This is the *fallback* instance - the one that can be activated and thus become active.
Any number of import instances can be used. Deciding which one should take over can be done manually
or through a monitoring + election script.


You should provide the bin/{something}-importer script, see for instance

  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/postgres/__init__.py?js=1#l233
  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/mydumper.py?js=1#l71



