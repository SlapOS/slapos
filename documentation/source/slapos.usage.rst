=========================
SlapOS command line usage
=========================


Notes
-----

* Default SlapOS Master is https://slap.vifib.com. It can be changed by altering configuration files or with the ``--master-url``
  argument for commands that support it.

* Most commands take a configuration file parameter, provided as ``--cfg /path/to/file.cfg``.

  If no such argument is provided:
  
  * "node" commands read configuration from :file:`/etc/opt/slapos/slapos.cfg`, or the file referenced by the
    ``SLAPOS_CONFIGURATION`` environment variable.

  * likewise, "client" commands (request, supply...) use :file:`~/.slapos/slapos.cfg`, or the ``SLAPOS_CLIENT_CONFIGURATION`` variable.



..
  XXX TODO software_group?, computer_group?



Common options
--------------

Without arguments, the ``slapos`` program lists all the available commands and common options.

.. program-output:: python slapos


The ``-q`` and ``-v`` options control the verbosity of console output (``-v``: DEBUG, default: INFO, ``-q``: WARNING).

Output to a logfile is not affected, and is the same as ``-v``.



SlapOS Client commands
----------------------

These commands are used by clients (as human beings or programs) to manage their own instances.

request
~~~~~~~

.. program-output:: python slapos help request

Examples

* Request a wordpress instance named "mybeautifulinstance" on Node named "COMP-12345"::

    $ slapos request mybeautifulinstance wordpress --node id=COMP-12345

* Request a kvm instance named "mykvm" on Node named "COMP-12345", specifying nbd-host and nbd-ip parameters::

    $ slapos request mykvm kvm --node id=COMP-12345 --configuration \
        nbd-host=debian.nbd.vifib.net nbd-port=1024

* Request a kvm instance specifying the full URL, with default settings::

    $ slapos request mykvm \
        http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/tags/slapos-0.156:/software/kvm/software.cfg

In these examples, ``wordpress`` and ``kvm`` are aliases for the full URL, and are defined in :file:`slapos-client.cfg`.


..
  XXX Change in slaplib: allow to fetch instance params without changing anything.
      i.e we should do "slapos request myalreadyrequestedinstance" to fetch connection parameters
      without erasing previously defined instance parameters.


..
  search
  ~~~~~~
  Note: Not yet implemented.
  Usage:
    slapos search <search parameters ex. computer region, instance reference, source_section, etc.>
  
  Returns visible instances matching search parameters.


supply
~~~~~~

.. program-output:: python slapos help supply

Ask installation of a software on a specific node or group of nodes.
Nodes will then be ready to accept instances of specified software.

Examples

* Ask installation of wordpress Software Release on COMP-12345::

    $ slapos supply wordpress COMP-12345

In this example, ``wordpress`` is an alias for the full URL, and is defined in :file:`slapos-client.cfg`.

remove
~~~~~~

.. program-output:: python slapos help remove

Ask removal of a software from a specific node or group of nodes. Existing instances won't work anymore.

..
  XXX "slapos autounsupply a.k.a slapos cleanup"

Examples

* Ask installation of wordpress Software Release on COMP-12345::

    $ slapos supply wordpress COMP-12345

In this example, ``wordpress`` is an alias for the full URL, and is defined in :file:`slapos-client.cfg`.

..
  autosupply
  ~~~~~~~~~~
  Note: Not yet implemented.
  Usage:
    slapos autosupply <software | software_group> <computer_guid | computer_group>
  
  Like "slapos suppply", but on-demand. Software will be (re)installed only when at least one instance
  of this software is requested. When no instance of this software is deployed on the node, it will be uninstalled.


console
~~~~~~~

.. program-output:: python slapos help console



..
  <stop|start|destroy>
  ~~~~~~~~~~~~~~~~~~~~
  Note: Not yet implemented.
  Usage:
    slapos <stop|start|destroy> <instance reference>
  
  Ask start/stop/destruction of selected instance.
  
  Example:
  
    * Ask to stop "mywordpressinstance"::
  
        $ slapos stop mywordpressinstance



SlapOS Node commands
--------------------

This group of commands is used to control the current SlapOS Node. They are only useful to Node administrators.

node, node status
~~~~~~~~~~~~~~~~~

These are both aliases for ``node supervisorctl status``.
It displays the status of the node, also running the supervisor daemon if needed.

.. program-output:: python slapos help node supervisorctl status


node register
~~~~~~~~~~~~~

.. program-output:: python slapos help node register


This will register the current node, and generate the SlapOS configuration file.

The command requires an authentication token, either provided as an argument,
or given at the interactive prompt.
Go to the SlapOS Master web page, click ``My Space``, then ``My Account``, then
``Generate a computer security token``.
A token is valid for a single ``node resister`` command and will expire after one day.

The deprecated ``--login`` and ``--password`` options can be used with old SlapOS servers
that have no support for the token.


..
  XXX-Cedric should be like this: If desired node name is already taken, will raise an error.
  XXX-Cedric: --master-url-web url will disappear in REST API. Currently, "register" uses
              SlapOS master web URL to register computer, so it needs the web URL (like http://www.slapos.org)

If the Node is already registered (:file:`slapos.cfg` and certificate are already present), the command
issues a warning, backups the original configuration and creates a new one.

..
  XXX-Cedric should check for IPv6 in selected interface


Notes:
******

* "IPv6 interface" and "create tap" won't be put at all in the SlapOS Node configuration file if not explicitly written.

Examples

* Register computer named "mycomputer" to SlapOS Master::

    $ slapos node register mycomputer

* Register computer named "mycomputer" to SlapOS Master using br0 as primary interface,
  tap0 as IPv6 interface and different local ipv4 subnet::

    $ slapos node register mycomputer --interface-name br0 --ipv6-interface tap0 \
        --ipv4-local-network 11.0.0.0/16

* Register computer named "mycomputer" to another SlapOS master accessible via https://www.myownslaposmaster.com,
  and SLAP webservice accessible via https://slap.myownslaposmaster.com (note that this address should be the
  "slap" webservice URL, not web URL)::

    $ slapos node register mycomputer --master-url https://slap.myownslaposmaster.com \
        --master-url-web https://www.myownslaposmaster.com

* Register computer named "mycomputer" to SlapOS Master, and ask to create tap interface to be able to host KVMs::

    $ slapos node register mycomputer --create-tap


node software
~~~~~~~~~~~~~

.. program-output:: python slapos help node software


Return values:
**************

(among other standard Python return values)

* 0    Everything went fine.
* 1    At least one software was not correctly installed.


node instance
~~~~~~~~~~~~~

.. program-output:: python slapos help node instance


Return values:
**************

(among other standard Python return values)

* 0    Everything went fine.
* 1    At least one instance was not correctly processed.
* 2    At least one promise has failed.


node report
~~~~~~~~~~~

.. program-output:: python slapos help node report



Return values:
**************

(among other standard Python return values)

* 0    Everything went fine.
* 1    At least one instance hasn't correctly been processed.


node start|stop|restart|tail|status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 usage: slapos node <start|stop|restart|tail|status> [-h] [--cfg CFG] <instance>:[process]

 Start/Stop/Restart/Show stdout/stderr of instance and/or process.

 optional arguments:
  -h, --help       show this help message and exit
  --cfg CFG        SlapOS configuration file (default: $SLAPOS_CONFIGURATION
                   or /etc/opt/slapos/slapos.cfg)


Examples

* Start all processes of slappart3::

    $ slapos node start slappart3:

* Stop only apache in slappart1::

    $ slapos node stop slappart1:apache

* Show stdout/stderr of mysqld in slappart2::

    $ slapos node tail slappart2:mysqld



node supervisorctl
~~~~~~~~~~~~~~~~~~

.. program-output:: python slapos help node supervisorctl


node supervisord
~~~~~~~~~~~~~~~~

.. program-output:: python slapos help node supervisord



..
  node log
  ~~~~~~~~
  Note: Not yet implemented.
  Usage:
    slapos node log <software|instance|report>
  
  Display log.





SlapOS Miscellaneous commands
-----------------------------

configure client
~~~~~~~~~~~~~~~~

.. program-output:: python slapos help configure client


This creates a client configuration file, and downloads a certificate + key pair
from the SlapOS Master. They will be used for all the "slapos client" commands.

The command requires an authentication token, either provided as an argument,
or given at the interactive prompt.

Go to the SlapOS Master web page, click ``My Space``, then ``My Account``, then
``Generate a credential security token``.
A token is valid for a single ``configure client`` command and will expire after one day.


cache lookup
~~~~~~~~~~~~

.. program-output:: python slapos help cache lookup


Examples

* See if the wordpress Software Release is available in precompiled format for our distribution::

    $ slapos cache lookup http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/tags/slapos-0.156:/software/kvm/software.cfg
    Software URL: http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/tags/slapos-0.156:/software/kvm/software.cfg
    MD5:          4410088e11f370503e9d78db4cfa4ec4
    -------------
    Available for: 
    distribution     |   version    |       id       | compatible?
    -----------------+--------------+----------------+-------------
    CentOS           |          6.3 |     Final      | no
    Fedora           |           17 | Beefy Miracle  | no
    Ubuntu           |        12.04 |    precise     | yes
    debian           |        6.0.6 |                | no
    debian           |          7.0 |                | no

You can also use the corresponding hash value in place of the URL.



