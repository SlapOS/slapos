=========================
SlapOS command line usage
=========================


Note:
-----
 * Default configuration file of "Node" commands if not explicitly defined (slapos node, slapos supervisor) is:
    /etc/opt/slapos/slapos.cfg or value of SLAPOS_CONFIGURATION environment variable if exists.

 * Default configuration file of "Client" commands if not explicitly defined (slapos request, slapos supply, ...) is:
    ~/.slapos/slapos.cfg or value of SLAPOS_CLIENT_CONFIGURATION environment variable if exists.

 * Default log file for Node commands is /var/log/[slapos-node-software.log | slapos-node-instance.log | slapos-node-report.log]. This one requires working log in slapgrid, currently log/console is a total mess.

 * Default pid file for Node commands is: /var/run/[slapos-node-software.pid | slapos-node-instance.pid | slapos-node-report.pid].

 * Default SlapOS Master is http://www.vifib.net. It can be changed by altering configuration files.



General commands
----------------

slapos
~~~~~~
Display help/usage.



SlapOS Client commands
----------------------

Those commands are used by clients (as human beings or programs) to manage their own instances.

slapos request
~~~~~~~~~~~~~~
Usage:
  slapos request [slapos_configuration] <reference> <software_alias | software-url> [--node id=<computer guid>,region=<region>,network-type=<network> | location/to/node.json] [--configuration foo=value1,bar=value2 | location/to/configuration.json ] [--type type] [--slave]

Request an instance and get status and parameters of instance.

Examples:
 * Request a wordpress instance named "mybeautifulinstance" on Node named "COMP-12345":
     slapos request wordpress mybeautifulinstance --node id=COMP-12345

XXX Change in slaplib: allow to fetch instance params without changing anything. i.e we should do "slapos request myalreadyrequestedinstance" to fetch connection parameters without erasing previously defined instance parameters.


slapos search
~~~~~~~~~~~~~
Usage:
  slapos search <search parameters ex. computer region, instance reference, source_section, etc.>

Returns visible instances matching search parameters.


slapos supply
~~~~~~~~~~~~~
Usage:
   slapos supply <software | software_group> <computer_guid | commputer_group>

Ask installation of a software on a specific node or group of nodes. Nodes will then be ready to accept instances of specified software.

Examples:
 * Ask installation of wordpress Software Release on COMP-12345:
    slapos supply wordpress COMP-12345


slapos autosupply
~~~~~~~~~~~~~~~~~
Usage:
  slapos autosupply <software | software_group> <computer_guid | computer_group>

Like "slapos suppply", but on-demand. Software will be (re)installed only when at least one instance of this software is requested. When no instance of this software is deployed on the node, it will be uninstalled.


slapos console
~~~~~~~~~~~~~~
Enter in a python console with slap library imported. See "Slapconsole" section to have detailed documentation.


slapos <stop|start|destroy>
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  slapos <stop|start|destroy> <instance reference>

Ask start/stop/destruction of selected instance.

Example:
  * Ask to stop "mywordpressinstance":
      slapos stop mywordpressinstance



SlapOS Node commands
--------------------

This kind of commands are used to control the current SlapOS Node. Those commands are only useful for administrators of Nodes.
# XXX: add an environment variable for configuration file.

slapos node
~~~~~~~~~~~
Display status of Node and if not started, launch supervisor daemon.

Temporary note: equivalent of old slapgrid-supervisord + slapgrid-supervisorctl.


slapos node register
~~~~~~~~~~~~~~~~~~~~
Usage:
******
::

  slapos node register <DESIRED NODE NAME> [--login LOGIN [--password PASSWORD]] [--interface-name INTERFACE] [--master-url URL <--master-url-web URL>] [--partition-number NUMBER] [--ipv4-local-network NETWORK] [--ipv6-interface INTERFACE] [--create-tap] [--dry-run]

If login is not provided, asks for user's vifib account then password.

Node will register itself, if not already done, to the SlapOS Master defined in configuration file, and will generate SlapOS configuration file.

XXX-Cedric should be like this: If desired node name is already taken, will raise an error.
XXX-Cedric: --master-url-web url will disappear in REST API. Currently, "register" uses SlapOS master web URL to register computer, so it needs the web URL (like http://www.vifib.net)

If Node is already registered (slapos.cfg and certificate already present), issues a warning, backups original configuration and creates new one.

XXX-Cedric should check for IPv6 in selected interface

Parameters:
***********
--login LOGIN                  Your SlapOS Master login. If not provided, asks it interactively.
--password PASSWORD            Your SlapOS Master password. If not provided, asks it interactively. NOTE: giving password as parameter should be avoided for security reasons.
--interface-name INTERFACE     Use interface as primary interface. IP of Partitions will be added to it. Defaults to "eth0".
--master-url URL               URL of SlapOS Master REST API. defaults to "https://slap.vifib.com".
--master-url-web URL           URL of SlapOS Master web access. defaults to "https://www.vifib.com".
--partition-number NUMBER      Number of partitions that will have your SlapOS Node. defaults to "10".
--ipv4-local-network NETWORK   Subnetwork used to assign local IPv4 addresses. It should be a not used network in order to avoid conflicts. defaults to 10.0.0.0/16.
-t, --create-tap                   Will trigger creation of one virtual "tap" interface per Partition and attach it to primary interface. Requires primary interface to be a bridge. defaults to false. Needed to host virtual machines.
-n, --dry-run                      Don't touch to anything in the filesystem. Used to debug.

Notes:
******
  * "IPv6 interface" and "create tap" won't be put at all in the SlapOS Node configuration file if not explicitly written.

Examples:
*********
  * Register computer named "mycomputer" to vifib::

      slapos node register mycomputer

  * Register computer named "mycomputer" to vifib using br0 as primary interface, tap0 as IPv6 interface and different local ipv4 subnet::

      slapos node register mycomputer --interface-name br0 --ipv6-interface tap0 --ipv4-local-network 11.0.0.0/16

  * Register computer named "mycomputer" to another SlapOS master accessible via https://www.myownslaposmaster.com, and SLAP webservice accessible via https://slap.myownslaposmaster.com (Note that this address should be the "slap" webservice URL, not web URL)::

      slapos node register mycomputer --master-url https://slap.myownslaposmaster.com --master-url-web https://www.myownslaposmaster.com

XXX-Cedric : To be implemented
  * Register computer named "mycomputer" to vifib, and ask to create tap interface to be able to host KVMs::

      slapos node register mycomputer --create-tap


slapos node software
~~~~~~~~~~~~~~~~~~~~
Usage:
******
::

  slapos node software [--logfile LOGFILE] [--verbose | -v] [--only_sr URL]  [--all] [CONFIGURATION_FILE]

Run software installation/deletion.

Temporary note: equivalent of old slapgrid-sr.
# XXX: only_sr should be named ??? (process-only ?)
# XXX: add a "-vv", very verbose, option.

Parameters:
***********
--logfile LOGFILE              If specified, will log as well output in the file located at FILE.
--only_sr URL                  Only process one specific Software Release that has been supplied on this Computer. If not supplied: do nothing.
--all                          Process all Software Releases, even already installed.
--verbose, -v                  Be more verbose.

Return values:
**************
(Among other standard Python return values)
0        Everything went fine
1        At least one software hasn't correctly been installed.


slapos node instance
~~~~~~~~~~~~~~~~~~~~
Usage:
******
::

  slapos node instance [--logfile LOGFILE] [--verbose | -v] [--only_cp PARTITION]  [--all] [CONFIGURATION_FILE]

Temporary note: equivalent of old slapgrid-cp.

Run instances deployment.

Parameters:
***********
--logfile LOGFILE              If specified, will log as well output in the file located at FILE.
--only_cp PARTITION            Only process one specific Computer Partition, if possible.
--all                          Force processing all Computer Partitions.
--verbose, -v                 Be more verbose.

Return values:
**************
(Among other standard Python return values)
0        Everything went fine
1        At least one instance hasn't correctly been processed.
2        At least one promise has failed.


slapos node report
~~~~~~~~~~~~~~~~~~
Usage:
******
::

  slapos node report [--logfile LOGFILE] [--verbose | -v] [CONFIGURATION_FILE]

Run instance reports and garbage collection.

Temporary note: equivalent of old slapgrid-ur.

Parameters:
***********
--logfile LOGFILE              If specified, will log as well output in the file located at FILE.
--verbose, -v                 Be more verbose.

Return values:
**************
(Among other standard Python return values)
0        Everything went fine
1        At least one instance hasn't correctly been processed.


slapos node <start|stop|restart|tail|status>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  slapos node <start|stop|restart|tail|status> <instance>:[process]

Start/Stop/Restart/Show stdout/stderr of instance and/or process.

Examples:

 * Start all processes of slappart3:
     slapos node start slappart3:

 * Stop only apache in slappart1:
     slapos node stop slappart1:apache

 * Show stdout/stderr of mysqld in slappart2:
     slapos node tail slappart2:mysqld

slapos node supervisorctl
~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  slapos node supervisorctl

Enter into supervisor console.

slapos node supervisord
~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  slapos node supervisord

Launch, if not already launched, supervisor daemon.

slapos node log
~~~~~~~~~~~~~~~
Usage:
  slapos node log <software|instance|report>

Display log.
