============================
Zabbix Agent Software Release
=============================

This Software Release allows to deploy a Zabbix Agent that will connect
to an existing Zabbix Server.

Please see http://www.zabbix.com/ for more informations.


Mandatory parameters
====================

hostname
--------
Name of the machine probed by the agent.

server
------
list of Zabbix servers to connect to, comma-seperated.

Optional parameters
===================

custom-user-parameter
---------------------
Add custom UserParameter(s) lines to the Zabbix Agent configuration file.


Examples of instance parameters XML
===================================

Example 1
~~~~~~~~~

Simple request: just request a new instance of it, with the following parameters::

  <?xml version="1.0" encoding="utf-8"?>
    <instance>
    <parameter id="server">REPLACE BY IP(v6) OF ZABBIX SERVER</parameter>
    <parameter id="hostname">REPLACE BY DESIRED HOSTNAME OF MACHINE</parameter>
  </instance>

Example 2
~~~~~~~~~

Deploy a Zabbix Agent instance for machine named "mymachine" connecting to a Zabbix server accessible from 2001:41d0:1:9b1a::1::

  <?xml version="1.0" encoding="utf-8"?>
    <instance>
    <parameter id="server">2001:41d0:1:9b1a::1</parameter>
    <parameter id="hostname">mymachine</parameter>
  </instance>

Example 3
~~~~~~~~~

Deploy a Zabbix Agent instance for machine named "mymachine" connecting to a Zabbix server accessible from 2001:41d0:1:9b1a::1, with several custom parameters::

  <?xml version="1.0" encoding="utf-8"?>
  <instance>
    <parameter id="server">2001:41d0:1:9b1a::1</parameter>
    <parameter id="hostname">mymachine</parameter>
    <parameter id="custom-user-parameter">
    UserParameter=custom_random,echo $RANDOM
    UserParameter=custom_date,date
    </parameter>
  </instance>

