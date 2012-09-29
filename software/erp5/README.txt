Software types
==============
Which software type is an entry point and can be used for root software
instance.

Parameters are expected to be passed as of *.serialised recipes expect them::

```
<?xml version='1.0' encoding='utf-8'?>
<instance>
  <parameter id="_">...</parameter>
</instance>
```

where `...` is a json expression (typically a dict).

common
------
Parameters which are available to all software types.

'test-database-amount' (int, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Number of test databases to generate in addition of requested databases.
A test database, if it were provided as a database-list entry, would look like:
  {'name': 'erp5_test_0', 'user': 'testuser_0', 'password': 'testpassword0'}
with '0' being all numbers from 0 to test-database-amount - 1.
Defaults to 0.

'mariadb-binlogs' (dict, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enable writing data-modifying requests to binlogs. Useful to restore data
further after latest available full backup.
Defaults to {'expire-days': 0} (binlogs are disabled).
Possible keys and associated value types:
'expire-days' (int, optional)
  The number of days binlogs will be kept.
  If 0, binlogs are disabled.
  If -1, binlogs are never expired.
  Defaults to 7.

'database-list' (list, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Define the list of databases mariadb must provide, and the user having entire
access to each database. Each entry in the list is a dict, with these possible
keys and associated value types:
'name' (str, mandatory)
  Database name
'user' (str, mandatory)
  User login
'password' (str, mandatory)
  User password
Defaults to: [{'name': 'erp5', 'user': 'user', 'password': 'insecure'}]

'innodb-buffer-size' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
See mariadb documentation for innodb_buffer_pool_size configuration parameter.
Value is used verbatim in configuration file.
Empty string means unconfigured (ie, bail out to mariadb's default).
Defaults to "".

'innodb-log-file-size' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
See mariadb documentation for innodb_log_file_size configuration parameter.
Value is used verbatim in configuration file.
Empty string means unconfigured (ie, bail out to mariadb's default).
Defaults to "".

'innodb-log-buffer-size' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
See mariadb documentation for innodb_log_buffer_size configuration parameter.
Value is used verbatim in configuration file.
Empty string means unconfigured (ie, bail out to mariadb's default).
Defaults to "".

'mariadb-relaxed-writes' (int, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Controls relaxed writes, which improves performances at the cost of data
safety. DO NOT ENABLE THIS ON PRODUCTION. It's fine for unit tests and may be
acceptable for development instances. Set to 1 to enable.
Default: 0

single (default)
----------------
This creates an ERP5 instance suited for small needs/resources, or local
development. A minimal ERP5 site is created when instance is started.

frontend-software-url
~~~~~~~~~~~~~~~~~~~~~
Software URL of an existing frontend.
XXX: meaning should change (or it will go away) in order to be resilient to
software updates - as they are visible at software-url level.
If it is not provided, no frontend will be requested.

frontend-instance-guid
~~~~~~~~~~~~~~~~~~~~~~
GUID of frontend instance.
Not perfect yet: if that instance is replaced, slaves have to be reconfigured.
Mandatory only if frontend-software-url is also provided.
XXX: should be complemented (or replaced) by more flexible and precise
criteria.

frontend-software-type (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Frontend software type as defined by the software relase at
frontend-software-url.

frontend-domain (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Domain name frontend must recognise as belonging to this instance.

cluster
-------
This creates a massive ERP5 instance suited for high-demanding production
setups - which also have a lot of available resources (several machines,
several CPUs per machine, GBs of ram, several machines...).

For each available key in the outmost dict are described below.
Publishes a dict in which each entry is the URL to a balancer entry point
(apache listening socket), witht the same keys as zope-partition-dict.

'zodb-software-type' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Storage mechanism to use. To know the list of supported values, see all keys in
instance.cfg.in's section [switch-softwaretype] which start with "zodb-".
Defaults to 'zeo'.

'zodb-dict' (dict, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Describes ZODBs to create and use in the instance. At least one entry is
required to achieve anything sensible with the instance.
key (str)
  Zope internal name for this ZODB. Used to tell mountpoints apart in the ZMI
  when populating them.
value (dict)
  key (str)
    Possible keys and associated value types:
    'storage-family' (str, optional)
      Storage family. All zodbs requested with the same value are provided
      by the same service (ex: same ZEO process). Might not be supported by
      all zodb-software-type, silently ignored if so (ie, each ZODB gets its
      own family).
      Defaults to 'default'.
    'mount-point' (str, optional)
      Storage mount point.
      Defaults to '/'.
    'cache-size' (int, optional)
      Storage ZODB cache size (aka 'Connection cache'), in objects. No value
      is specified when negative is provided (ie, uses ZODB's default).
      Defaults to -1.
    'storage-dict' (dict, optional)
      Storage-type-specific parameters. For example, it can be used to tell where
      a ZEO filestorage database is located.
      When zodb-software-type is 'zeo', the following keys are supported:
      'path' (string, optional)
        FileStorage file path. Occurrences of '%(zodb)s' are replaced with the
        path to partition's srv/zodb directory.
        Defaults to '%(zodb)s/', Zope's internal name for this ZODB, and '.fs'.
      'client' (dict, optional)
        Client(=Zope)-side settings. 'server' and 'storage' keys will be
        overwritten. Keys and values are expected to be strings, and map
        directly to options in the resulting <zeoclient> section.
        Defaults to {}.

'tidstorage-dict' (dict, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Backup parameters for tidstorage-related backup scripts.
TIDStorage is not deployed if not provided.
key (str)
  Possible keys and associated value types:
  'zodb-dict' (dict, optional)
    key (str)
      (same as zodb-dict)
    value (str, optional)
      Path to store backups of this zodb into. Occurrences of '%(backup)s' are
      replaced with the path to partition's srv/backup/zodb directory.
    Defaults to {}.
    If an item is missing compared to zodb-dict, value defaults to
    '%(backup)s/' + key.
  'timestamp-path' (str, optional)
    Path to backup timestamp file.
    Occurrences of '%(backup)s' are replaced with the path to partition's
    srv/backup/tidstorage directory.
    Defaults to '%(backup)s/repozo_tidstorage_timestamp.log'.

'zope-partition-dict' (dict, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
key (str)
  Instance name.
value (dict)
  Possible keys and associated value types:
  'family' (str, optional)
    The family this partition is part of. For example: 'public', 'admin',
    'backoffice', 'web-service'... Each family gets its own frontend
    (=client-facing ip & port). It has no special meaning as far as
    buildout is concerned.
    Defaults to 'default'.
  'instance-count' (int, optional)
    The number of Zopes to setup on this partition.
    Defaults to 1.
  'thread-amount' (int, optional)
    The number of worker threads for each created Zope process.
    Defaults to 1.
  'timerserver-interval' (int, optional)
    The timerserver tick perdiod. 0 to disable timerserver.
    Defaults to 5.
  'computer-guid' (string, optional)
    Computer on which partition should be allocated.
    Defauts to the same computer as the one this .cfg is executed in.
  'longrequest-logger-interval' (int, optional)
    The period, in seconds, with which LongRequestLogger polls worker thread
    stack traces. -1 to disable.
    Defaults to -1.
  'longrequest-logger-timeout' (int, optional)
    The transaction duration after which LongRequestLogger will start logging
    its stack trace, in seconds. Ignored if longrequest-logger-interval is -1.
    Defaults to 1.
  'port-base' (int, optional)
    Start allocating ports at this value. Useful if one needs to make several
    partitions share the same port range (ie, several partitions bound to a
    single address).
    Defaults to 2000.

'haproxy-maxconn' (int, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The number of connections haproxy accepts for a given backend.
See haproxy's "server maxconn" setting.
Defaults to 1 (correct for single-worker-threaded zopes).

'haproxy-server-check-path' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The path haproxy accesses on a each backend to test their responsiveness.
Occurrences of '%(site-id)s' are replaced with site-id value (see below).
Defaults to '/'.

'apache-backend-path' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Used as a rewriterule to strip components from site's URL.
Occurrences of '%(site-id)s' are replaced with site-id value (see below).
XXX: You may want to avoid using this when also requesting a frontend apache.
Defaults to '/' (ie, nothing is stripped).

'apache-access-control-string' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The list of hosts apache accepts connections from.
Defaults to 'all'.

'apache-ssl-authentication' (booleanish, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Controls certificate-based authentication.
Defaults to '0' (disabled).

'site-id' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~
Site object's id. Defaults to 'erp5'.

'ca' (dict, optional)
~~~~~~~~~~~~~~~~~~~~~
Certificate autority parameters.
Possible keys and associated value types:
'country-code' (str, optional)
  ISO 3166-1 alpha-2 country code. Defaults to 'ZZ'.
'email' (str, optional)
  E-mail address. Defaults to 'nobody@example.com'
'state' (str, optional)
  State name. Defaults to 'Dummy State'.
'city' (str, optional)
  City name. Default to 'Dummy City'.
'company' (str, optional)
  Company name. Defaults to 'Dummy Company'.

'use-ipv6' (boolean, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use IPv6 to communicate between partitions.
Defaults to False.

'mariadb-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition mariadb is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'cloudooo-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition cloudooo is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'memcached-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition memcached is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'kumofs-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition kumofs is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'zodb-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition ZODB server is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'balancer-computer-guid' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Computer GUID identifying the partition balander (haproxy, apache, some HTTP
cache) is to be requested on.
Defaults to "cluster" software type's partition's effective computer GUID.

'cloudooo-json' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
XXX: what is this ?
XXX: should not require serialising json by hand as parameter value

'bt5' (str, optional)
~~~~~~~~~~~~~~~~~~~~~
XXX: what is this ?
Defaults to 'erp5_full_text_myisam_catalog \
erp5_configurator_standard \
erp5_configurator_maxma_demo \
erp5_configurator_ung \
erp5_configurator_run_my_doc'.

'bt5-repository-url' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
XXX: what is this ?
Defaults to SR's buildout['local-bt5-repository']['list'].

'smtp-url' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
XXX: what is this ?
Defaults to 'smtp://localhost:25/'.

'timezone' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Timezone to put processes in (default timezone for DateTime instances).
Defaults to 'Europe/Paris'.

'frontend-software-url' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Frontend's software url.
Defaults to ''.
If non-empty, the following options are used (otherwise, they are all
optional and ignored):

'frontend-software-type' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Frontend's software type.
Defaults to 'RootSoftwareInstance'

'frontend-instance-guid' (str, mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Instance GUID identifying the partition frontend is on.

'frontend-domain' (str, optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The domain name used to access this ERP5 cluster, ignored if empty.
Defaults to ''.

For a better description of these parameters, see a frontend software
release documentation.

