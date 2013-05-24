Zabbix Agent
============

This Software Release allows to deploy a Zabbix Agent that will connect
to an existing Zabbix Server.


How to request
==============

Just request a new instance of it, with the following parameters::

  <?xml version="1.0" encoding="utf-8"?>
    <instance>
    <parameter id="server">REPLACE BY IP(v6) OF ZABBIX SERVER</parameter>
    <parameter id="hostname">REPLACE BY DESIRED HOSTNAME OF MACHINE</parameter>
  </instance>
