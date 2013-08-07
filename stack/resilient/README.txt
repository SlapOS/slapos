
Base resilient stack
====================

This stack is meant to be extended by SR profiles, or other stacks, that need to provide
automated backup/restore, election of backup candidates, and instance failover.

As reference implementations, both stack/lamp and stack/lapp define resilient behavior for
MySQL and Postgres respectively.

This involves three different software_types:

 * pull-backup
 * {mysoftware}_export
 * {mysoftware}_import

where 'mysoftware' is the component that needs resiliency (can be postgres, mysql, erp5, and so on).


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
     1) run bin/{mysoftware}-backup
 and 2) notify the pull-backup instance that data is ready.

The pull-backup, upon receiving the notification, will make a copy of the data and transmit it to the 'import' instances.

You should provide the bin/{mysoftware}-exporter script, see for instance
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


You should provide the bin/{mysoftware}-importer script, see for instance

  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/postgres/__init__.py?js=1#l233
  http://git.erp5.org/gitweb/slapos.git/blob/HEAD:/slapos/recipe/mydumper.py?js=1#l71




In practice
-----------

Add resilience to your software

Let's say you already have a file instance-mysoftware.cfg.in that instantiates your
software. In which there is a part [mysoftware] where there is the main recipe
that instantiates the program.

You need to create two new files, instance-mysoftware-import.cfg.in and
instance-mysoftware-export.cfg.in, following this layout:


IMPORT:

[buildout]
extends = ${instance-mysoftware:output}
          ${pbsready-import:output}

parts +=
    mysoftware
    import-on-notification

[importer]
recipe = YourImportRecipe
wrapper = $${rootdirectory:bin}/$${slap-parameter:namebase}-importer
backup-directory = $${directory:backup}
...



EXPORT:

[buildout]
extends = ${instance-mysoftware:output}
          ${pbsready-export:output}

parts +=
    mysoftware
    cron-entry-backup

[exporter]
recipe = YourExportRecipe
wrapper = $${rootdirectory:bin}/$${slap-parameter:namebase}-exporter
backup-directory = $${directory:backup}
...


In the [exporter] / [importer] part, you are free to do whatever you want, but
you need to dump / import your data from $${directory:backup} and specify a
wrapper. I suggest you only add options and specify your export/import recipe.




Checking that it works
----------------------

To check that your software instance is resilient you can proceed this way:
Once all instances are successfully deployed, go to your export instance, connect as the instance user and run:
$ ~/bin/exporter
It is the script responsible for triggering the resiliency stack on your instance. After doing a backup of your data, it will notify the pull-backup instances of a new backup, triggering the transfer of this data to the import instances.

Once this script is run successfully, go to your import instance, connect as its instance user and check ~/srv/backup/"your sofwtare"/, the location of the data you wanted to receive. The last part of the resiliency is up to your import script.

DEBUGGING:
Here is a partial list of things you can check to understand what is causing the problem:

- Check that your import script does not fail and successfully places your data in ~/srv/backup/"your software" (as the import instance user) by runnig:
$ ~/bin/"your software"-exporter
- Check the export instance script is run successfully as this instance user by running:
$ ~/bin/exporter
- Check the pull-instance system did its job by going to one of your pull-backup instance, connect as its user and check the log : ~/var/log/equeue.log


-----------------------------------------------------------------------------------------

Finally, instance-mysoftware-import.cfg.in and
instance-mysoftware-export.cfg.in need to be downloaded and accessible by
switch_softwaretype, and you need to extend stack/resilient/buildout.cfg and
stack/resilient/switchsoftware.cfg to download the whole resiliency bundle.

Here is how it's done in the mariadb case for the lamp stack:



 ** buildout.cfg **

extends =
   ../resilient/buildout.cfg

[instance-mariadb-import]
recipe = slapos.recipe.template
url = ${:_profile_base_location_}/mariadb/instance-mariadb-import.cfg.in
output = ${buildout:directory}/instance-mariadb-import.cfg
md5sum = ...
mode = 0644

[instance-mariadb-export]
recipe = slapos.recipe.template
url = ${:_profile_base_location_}/mariadb/instance-mariadb-export.cfg.in
output = ${buildout:directory}/instance-mariadb-export.cfg
md5sum = ...
mode = 0644



 ** instance.cfg.in **

extends =
  ../resilient/switchsoftware.cfg

[switch-softwaretype]
...
mariadb = ${instance-mariadb:output}
mariadb-import = ${instance-mariadb-import:output}
mariadb-export = ${instance-mariadb-export:output}
...



Then, in the .cfg file where you want to instantiate your software, you can do, instead of requesting your software

 * template-resilient.cfg.in *

[buildout]
...
parts +=
  {{ parts.replicate("Name","3") }}
  ...

[...]
...
[ArgLeader]
...

[ArgBackup]
...

{{ replicated.replicate("Name", "3",
                        "mysoftware-export", "mysoftware-import",
                        "ArgLeader","ArgBackup", slapparameter_dict=slapparameter_dict) }}

and it'll expend into the sections require to request Name0, Name1 and Name2,
backuped and resilient. The leader will expend the section [ArgLeader], backups
will expend [ArgBackup]. slapparameter_dict is the dict containing the parameters given to the instance. If you don't need to specify any options, you can
omit the last three arguments in replicate().

Since you will compile your template with jinja2, there should be no $${},
because it is not yet possible to use jinja2 -> buildout template.

To compile with jinja2, see jinja2's recipe.


Deploying your resilient software
---------------------------------
You can provide sla parameters to each request you make (a lot: for export, import and pbs).

example:
Here is a small example of parameters you can provide to control the deployment (case of a runner):
<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="-sla-1-computer_guid">COMP-GRP1</parameter>
  <parameter id="-sla-pbs1-computer_guid">COMP-PBS1</parameter>
  <parameter id="-sla-2-computer_guid">COMP-GROUP2</parameter>
  <parameter id="-sla-runner2-computer_guid">COMP-RUN2</parameter>
  <parameter id="-sla-2-network_guid">NET-2</parameter>
  <parameter id="-sla-runner0-computer_guid">COMP-RUN0</parameter>
</instance>
Consequence on sla parameters by request:
  * runner0: computer_guid = COMP-RUN0 (provided directly)
  * runner1: computer_guid = COMP-GRP1 (provided by group 1)
  * runner2: computer_guid = COMP-RUN2 (provided by group 2 but overided directly)
             network_guid  = NET-2 (provided by group 2)
  * PBS 1:   computer_guid = COMP-PBS1 (provided by group 1 but overided directly)
  * PBS 2:   computer_guid = COMP-GRP2 (provided by group 2)
             network_guid  = NET-2 (provided by group 2)


Parameters are analysed this way:
 * If it starts with "-sla-" it is not transmitted to requested instance and is used to do the request as sla.
 * -sla-foo-bar=example (foo being a magic key) will be use for each request considering "foo" as a key to use and the sla parameter is "bar". So for each group using the "foo" key, sla parameter "bar" is used with value "example"
About magic keys:
We can find 2 kinds of magic keys:
 * id : example, in "-sla-2-foo" 2 is the magic key and the parameter will be used for each request with id 2 (in case of kvm: kvm2 and PBS 2)
 * nameid : example, in "-sla-kvm2-foo", foo will be used for kvm2 request. Name for pbs is "pbs" -> "-sla-pbs2-foo".
IMPORTANT NOTE: in case the same foo parameter is asked for the group, the nameid key prevail
