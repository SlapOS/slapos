=========================
SlapOS command line usage
=========================


Note:
-----
 * Default configuration file of "Node" commands (slapos node, slapos supervisor) is:
    /etc/opt/slapos/slapos.cfg

 * Default configuration file of "Client" commands (slapos request, slapos supply, ...) is:
    ~/.slapos/slapos.cfg

 * Default log file for Node commands is /var/log/[slapos-node-software.log | slapos-node-instance.log | slapos-node-report.log]. This one requires working log in slapgrid, currently log/console is a total mess.

 * Default pid file for Node commands is: /var/run/[slapos-node-software.pid | slapos-node-instance.pid | slapos-node-report.pid].

 * Default SlapOS Master is http://www.vifib.net. It can be changed by altering configuration files. XXX How to ship slapos with this? Should package (.deb, ...) include slapos.cfg with only master_url inside?



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
  slapos request <reference> [software_alias | software-url] [--node id=<computer guid>,region=<region>,network-type=<newtork> | location/to/node.json] [--configuration foo=value1,bar=value2 | location/to/configuration.json ] [--type type] [--slave]

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

slapos node
~~~~~~~~~~~
Display status of Node and if not started, launch supervisor daemon.

Temporary note: equivalent of old slapgrid-supervisord + slapgrid-supervisorctl.


slapos node register
~~~~~~~~~~~~~~~~~~~~
Usage:
******
::

  slapos node register <desired node name> [--interface-name interface] [--master-url url <--master-url-web url>] [--partition-number number] [--ipv4-local-network network] [--ipv6-interface interface]

Asks for user's vifib account then password.

Node will register itself, if not already done, to the SlapOS Master defined in configuration file, and will generate SlapOS configuration file.

XXX-Cedric should be like this: If desired node name is already taken, will raise an error.
XXX-Cedric: --master-url-web url will disappear in REST API. Currently, "register" uses SlapOS master web URL to register computer, so it needs the web URL (like http://www.vifib.net)

If Node is already registered (slapos.cfg and certificate already present), issues a warning, backups original configuration and creates new one.

XXX-Cedric should check for IPv6 in selected interface

Defaults:
*********
  * --interface-name defaults to "eth0"
  * --master-url defaults to "https://slap.vifib.com"
  * --partition-number number defaults to "10"
  * --ipv4-local-network defaults to 10.0.0.0/16

Notes:
******
  * "IPv6 interface" won't be set if not explicitly written.

Examples:
*********
  * Register computer named "mycomputer" to vifib::

      slapos register mycomputer

  * Register computer named "mycomputer" to vifib using br0 as primary interface, tap0 as IPv6 interface and different local ipv4 subnet::

      slapos register mycomputer --interface-name br0 --ipv6-interface tap0 --ipv4-local-network 11.0.0.0/16

  * Register computer named "mycomputer" to another SlapOS master accessible via https://www.myownslaposmaster.com, and SLAP webservice accessible via https://slap.myownslaposmaster.com (Note that this address should be the "slap" webservice URL, not web URL)::

      slapos register mycomputer --master-url https://slap.myownslaposmaster.com --master-url-web https://www.myownslaposmaster.com


slapos node software
~~~~~~~~~~~~~~~~~~~~
Run software installation/deletion.

Temporary note: equivalent of old slapgrid-sr.


slapos node instance
~~~~~~~~~~~~~~~~~~~~
Run instance deployment

Temporary note: equivalent of old slapgrid-cp.


slapos node report
~~~~~~~~~~~~~~~~~~
Run instance reports and garbage collection.

Temporary note: equivalent of old slapgrid-cp.


slapos node <start|stop|tail|status>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Usage:
  slapos node <start|stop|tail|status> <instance>:[process]

Start/Stop/Show stdout/stderr of instance and/or process.

Examples:

 * Start all processes of slappart3:
     slapos node start slappart3:

 * Stop only apache in slappart1:
     slapos node stop slappart1:apache

 * Show stdout/stderr of mysqld in slappart2:
     slapos node tail slappart2:mysqld


slapos node log
~~~~~~~~~~~~~~~
Usage:
  slapos node log <software|instance|report>

Display log.
