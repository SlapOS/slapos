Changes
=======

1.0.44 (2016-12-30)
-------------------

 * pbs: handles the fact that some parameters are not present when slaves are down
 * recipe: allow usage of pidfile in wrapper recipe
 * sshd: fix generation of authorized_keys

1.0.43 (2016-11-24)
-------------------

  * pbs: fixes trap command for dash intepreter
  * pbs: remove infinite loops from pbs scripts.
  * random.py: new file containing recipes generating random values.
  * testnode: disallow frontend access to all folders, avoiding publishing private repositories

1.0.41 (2016-10-26)
-------------------

  * dcron: new parameter to get a random time, with a frequency of once a day
  * softwaretype: fix parse error on '+ =' when using buildout 2
  * pbs: General Improvement and fixes.

1.0.35 (2016-09-19)
-------------------

  * pbs: fix/accelerates deployment of resilient instances
  * recipe: new recipe to get a free network port
  * Remove url-list parameter to download fonts from fontconfig instance

1.0.31 (2016-05-30)
-------------------

  * Implement cross recipe cache for registerComputerPartition
  * Fixup! workarround for long shebang (place script on bin)  

1.0.30 (2016-05-23)
-------------------

  * Implement a workarround for long shebang
  * Implement Validation for user inputs ssl certificates 

1.0.25 (2016-04-15)
-------------------

  * fixup slap configuration: provide instance and root instance title

1.0.22 (2016-04-01)
-------------------

  * slap configuration: provide instance and root instance title

1.0.16 (2015-10.27)
-------------------

  * kvm recipe: fix bugs dowload image and disk creation

1.0.14 (2015-10.26)

-------------------
  * kvm recipe: Allow to set keyboard layout language used by qemu and VNC
  * simplehttpserver-recipe: fix encoding error

0.103 (2015-07-24)
------------------

  * kvm: fix issues with boolean parameters and add 'qed' in external disk format list.
  * simplehttpserver-recipe: Add support for POST method which only get content and save into specified file.

0.102 (2015-05-22)
------------------

 * kvm-recipe: vm of kvm-cluster can get ipv4/hostname of all other vm in the same cluster
 * simplehttpserver-recipe: simple http server to serve files

0.101 (2015-04-29)
------------------

 * kvm recipe: new parameters: external-disk-format, numa and cpu-options.
 * kvm recipe: allow guest VM to connect to host http service via a local predefined ipv4 address (guestfwd).

0.100 (2015-04-20)
------------------

 * re6stnet recipe: re6st-registry log can now be reopened with SIGUSR1
 * re6stnet recipe: re6st certificate generation is improved.

0.99 (2015-04-10)
-----------------

 * re6stnet: new recipe to deploy re6st registry (re6st master) with slapos.

0.98 (2015-04-09)
-----------------

 * shellinabox: do not run in debug mode, it is much slower !

0.97 (2015-03-26)
-----------------

 * switch softwaretype recipe: the recipe is backward compatible with old slapos node packages.
 * kvm recipe: Avoid getting wrong storage path when creating kvm external disk

0.96 (2015-03-20)
-----------------

 * slap configuration: recipe can read from master network information releated to a tap interface
 * slap configuration: recipe will setup data folder in DATA directory of computer partition if disk is mounted
 * switch softwaretype recipe: also generate tap network information when they exist
 * switch softwaretype recipe: generate configuration for DATA directory when disk is mounted

0.95 (2015-02-14)
-----------------

 * resiliency stack: allow web takeover to work inside of webrunner/erp5testnode.
 * resiliency takeover script: create lock file stating that takeover has been done.

0.94 (2015-02-06)
-----------------
 * kvm: allow to configure tap and nat interface at the same time with use-nat and use-tap [d3d65916]
 * kvm: use -netdev to configure network interface as -net is now obsolete [27baa9d4]

0.85 (2013-12-03)
-----------------

 * Slaprunner: recipe replaced by a buildout profile [14fbcd92]
 * Slaprunner: import instances can automatically deploy Software Releases [64c48388]
 * Slaprunner: backup script passes basic authentification [8877615]
 * Slaprunner: backup doesn't destroy symlinks for Software Releases [f519a078]
 * Shellinabox: now uses uid and gid to start [e9349c65]
 * Shellinabox: can do autoconnection [516e772]
 * Librecipe-generic: correction of bash code for /bin/sh compatibility [bee8c9c8]

0.84.2 (2013-10-04)
-------------------

 * sshkeys_authority: don't allow to return None as parameter. [9e340a0]

0.84.1 (2013-10-03)
-------------------

 * Resiliency: PBS: promise should NOT bang. [64886cd]

0.84 (2013-09-30)
-----------------

 * Request.py: improve instance-state handling. [ba5f160]
 * Resilient recipe: remove hashing of urls/names. [ee2aec8]
 * Resilient pbs recipe: recover from rdiff-backup failures. [be7f2fc, 92ee0c3]
 * Resilience: add pidfiles in PBS. [0b3ad5c]
 * Resilient: don't hide exception, print it. [05b3d64, d2b0494]
 * Resiliency: Only keep 10 increments of backup. [4e89e33]
 * KVM SR: add fallback in case of download exception. [de8d796]
 * slaprunner: don't check certificate for importer. [53dc772]

0.83.1 (2013-09-10)
------------------

 * slapconfiguration: fixes previous releasei (don't encode tap_set because it's not a string). [Cedric de Saint Martin]

0.83 (2013-09-10)
-----------------

 * slaprunner recipe: remove trailing / from master_url. [Cedric de Saint Martin]
 * librecipe: add pidfile option for singletons. [Cedric de Saint Martin]
 * Resiliency: Use new pidfile option. [Cedric de Saint Martin]
 * Fix request.py for slave instances. [Cedric de Saint Martin]
 * slapconfiguration recipe: cast some parameters from unicode to str. [Cedric de Saint Martin]

0.82 (2013-08-30)
-----------------

 * Certificate Authority: Can receice certificate to install. [Cedric Le Ninivin]
 * Squid: Add squid recipe. [Romain Courteaud]
 * Request: Trasmit instace state to requested instances. [Benjamin Blanc / Cédric Le Ninivin]
 * Slapconfiguration: Now return instance state. [Cédric Le Ninivin]
 * Apache Frontend: Remove recipe

0.81 (2013-08-12)
-----------------

 * KVM SR: implement resiliency test. [Cedric de Saint Martin]

0.80 (2013-08-06)
----------------

 * Add a simple readline recipe. [f4fce7e]

0.79 (2013-08-06)
-----------------

 * KVM SR: Add support for NAT based networking (User Mode Network). [627895fe35]
 * KVM SR: add virtual-hard-drive-url support. [aeb5df40cd, 8ce5a9aa1d0, a5034801aa9]
 * Fix regression in GenericBaseRecipe.generatePassword. [3333b07d33c]

0.78.5 (2013-08-06)
-------------------

 * check_url_available: add option to check secure links [6cbce4d8231]

0.78.4 (2013-08-06)
-------------------

 * slapos.cookbook:slaprunner: Update to use https. [Cedric Le Ninivin]


0.78.3 (2013-07-18)
-------------------

 * slapos.cookbook:publish: Add support to publish information for slaves. [Cedric Le Ninivin]

0.78.2 (2013-07-18)
-------------------

 * Fix slapos.cookbook:request: Add backward compatiblity about getInstanceGuid(). [Cedric de Saint Martin]
 * slapos.cookbook:check_* promises: Add timeout to curl that is not otherwise killed by slapos promise subsystem. [Cedric de Saint Martin]
 * Cloudooo: Allow any environment variables. [Yusei Tahara]
 * ERP5: disable MariaDB query cache completely by 'query_cache_type = 0' for ERP5. [Kazuhiko Shiozaki]
 * ERP5: enable haproxy admin socket and install haproxyctl script. [Kazuhiko Shiozaki]
 * ERP5: increase the maximum number of open file descriptors before starting mysqld. [Kazuhiko Shiozaki]
 * python 2.7: updated to 2.7.5 [Cedric de Saint Martin]

0.78.1 (2013-05-31)
-------------------

 * Add boinc recipe: Allow to deploy an empty BOINC project. [Alain Takoudjou]
 * Add boinc.app recipe: Allow to deploy and update a BOINC application into existing BOINC server instance . [Alain Takoudjou]
 * Add boinc.client recipe: Allow to deploy a BOINC Client instance on SlapOS. [Alain Takoudjou]
 * Add condor recipe: Allow to deploy Condor Manager or Condor worker instance on SlapOS. [Alain Takoudjou]
 * Add condor.submit recipe: Allow to deploy or update application into existing Condor Manager instance. [Alain Takoudjou]
 * Add redis.server recipe: Allow to deploy Redis server. [Alain Takoudjou]
 * Add trac recipe: for deploying Trac and manage project with support of SVN and GIT. [Alain Takoudjou]
 * Add bonjourgrid recipe: for deploying BonjourGrid Master and submit BOINC or Condor project. [Alain Takoudjou]
 * Add bonjourgrid.client recipe: for deploying BonjourGrid Worker instance and execute BOINC or Condor Jobs. [Alain Takoudjou]

0.78.0 (2013-04-28)
-------------------

 * LAMP stack: Allow to give application-dependent parameters to application configuration file. [Cedric de Saint Martin]
 * zabbix-agent: Allow user to pass zabbix parameter. [Cedric de Saint Martin]
 * kvm frontend: listen to ipv6 and ipv4. [Jean-Baptiste Petre]

0.77.1 (2013-04-18)
-------------------

 * Re-release of 0.77.0.

0.77.0 (2013-04-18)
-------------------

 * Allow to pass extra parameters when creating simple wrapper. [Sebastien Robin]
 * Apache frontend: Append all rewrite module options to http as well. [Cedric de Saint Martin]
 * Apache frontend: Add https-only support. [Cedric de Saint Martin]
 * Apache frontend: make logrotate work by using "generic" component. [Cedric de Saint Martin]

0.76.0 (2013-04-03)
-------------------

 * Add 'generic' phpconfigure recipe, allowing to configure any PHP-based app. [Cedric de Saint Martin]
 * apache_frontend: Have more useful access_log in apache frontend. [Cedric de Saint Martin]
 * apache_frontend: Add "SSLProxyEngine On" to http apache frontend vhost to be able to proxy https -> http. [Cedric de Saint Martin]
 * Add first preliminary version of nginx-based reverse proxy. [Cedric de Saint Martin]
 * Request-optional is not verbose anymore (again) if it failed. [Cedric de Saint Martin]
 * Add possibility to fetch web ip and port from apache recipe. [Cedric de Saint Martin]

0.75.0 (2013-03-26)
-------------------

 * Add backward compatibility about Partition.getInstanceGuid() in request.py. [Cedric de Saint Martin]
 * request.py: Don't crash if resource is not ready. [Cedric de Saint Martin]
 * Use memory-based kumofs instead of memcached to have no limitation for key length and data size. [Kazuhiko Shiozaki]
 * Postgres: allow slapuser# to connect as postgres user. [Marco Mariani]
 * apache_frontend: Sanitize inputs, disable Varnish cache, don't touch to custom file if already present. [Cedric de Saint Martin]
 * Resiliency: simpler, more robust PBS recipe and promise. [Marco Mariani]
 * Add helper method to set "location" parameter in librecipe. [Cedric de Saint Martin]
 * Add download helper function in librecipe. [Cedric de Saint Martin]
 * Update wrapper recipe to make it simpler and more dev-friendly. [Cedric de Saint Martin]
 * Add configurationfile recipe. [Cedric de Saint Martin]
 * Add request-edge recipe. [Cedric de Saint Martin]
 * Add publishsection recipe. [Cedric de Saint Martin]
 * Add match support for promise check_page_content. [Cedric de Saint Martin]

0.74.0 (2013-03-05)
-------------------

 * Generate mysql password randomly in LAMP stack. [Alain Takoudjou]
 * Add support for apache and haproxy to have more than one listening port. [Vincent Pelletier]
 * Use a more consistent parameter naming in 6tunnel recipe. [Vincent Pelletier]
 * Provide an SR-transparent way to (de)serialise master data. [Vincent Pelletier]
 * Initial version of neoppod recipe. [Vincent Pelletier]
 * Initial version of clusterized erp5 recipes. [Vincent Pelletier]
 * General cleanup of the request recipe (simpler parsing, less calls to master). [Vincent Pelletier, Cedric de Saint Martin]

0.73.1 (2013-02-19)
-------------------

 * softwaretype recipe: all falsy parameter values are now ignored. [Cedric de Saint Martin]

0.73.0 (2013-02-18)
-------------------

 * Add mioga and apacheperl recipes. [Viktor Horvath]
 * request.py: Properly fetch instance_guid of instance. [Cedric de Saint Martin]
 * request.py: Only append SLA parameter to the list if the key actually exists and is not empty string. [Cedric de Saint Martin]

0.72.0 (2013-02-11)
-------------------

 * librecipe: correctly handle newline and missing file in addLineToFile(). [Marco Mariani]
 * LAMP: Copy php application even if directory exists but is empty. This handle new resilient LAMP stack. [Cedric de Saint Martin]
 * LAMP: Don't even try to restart/reload/graceful Apache. This fix "Apache hangs" problem. [Cedric de Saint Martin]

0.71.4 (2013-02-01)
-------------------

 * Enable IPv6 support in KumoFS. [Vincent Pelletier]
 * Use new connection and get result when try to create new erp5 site. [Rafael Monnerat]
 * Set up timezone database in mariab's mysql table so that we can use timezone conversion function. [Kazuhiko Shiozaki]
 * Make erp5_bootstrap wait for manage_addERP5Site response [Rafael Monnerat]

0.71.3 (2013-01-31)
-------------------

 * Add mysql_ip and mysql_port parameters in apachephp recipe [Cedric de Saint
   Martin]
 * Random password for postgres in standalone SR and lapp stack; accept
   connections from the world. [Marco Mariani]

0.71.2 (2013-01-29)
-------------------

 * revised postgres/lapp recipe. [Marco Mariani]


0.71.1 (2013-01-04)
-------------------

 * Frontend: Sort instances by reference to avoid attacks. [Cedric de Saint
   Martin]
 * Frontend: Add public_ipv4 parameter support to ease deployment of slave
   frontend. [Cedric de Saint Martin]
 * Frontend: Move apache_frontend wrappers to watched directory (etc/service).
   [Cedric de Saint Martin]
 * Frontend: Add native path to varnish environment. [Cedric de Saint Martin]

0.71 (2012-12-20)
-----------------

 * frontend: Add "path" parameter for Zope instances. [Cedric de Saint Martin]

0.70 (2012-11-05)
-----------------

 * KVM: Add support for disk-type, second nbd and cpu-count. [Cedric de Saint
   Martin]

0.69 (2012-10-30)
-----------------

 * handle multiple notification_url values in notifier recipe [Marco Mariani]
 * createWrapper() sh alternative to execute.execute() for simple cases
   [Marco Mariani]
 * fixed secret key generation in apachephp config [Marco Mariani]

0.68.1 (2012-10-03)
-------------------

  * slaprunner: fix "logfile" parameter to "log_file"

0.68 (2012-10-02)
-----------------

  * request.py: Remove useless calls to master, fix "update" method. [Cedric
    de Saint Martin]
  * Add webrunner test recipe. [Alain Takoudjou]
  * Add logfile for slaprunner. [Cedric de Saint Martin]
  * Fix check_url_available promise (syntax + checks + IPv6 support). [Cedric
    de Saint Martin]

0.67 (2012-09-26)
-----------------

  * Add check_page_content promise generator. [Cedric Le Ninivin]
  * Fix check_url_available recipe. [Cedric de Saint Martin]
  * Set up timezone database in mariab's mysql table so that we can use
    timezone conversion function. [Kazuhiko Shiozaki]
  * Add many resiliency-based recipes [Timothée Lacroix]
  * Fix and unify request and requestoptional recipes [Cedric de Saint Martin]
  * Fix Dropbear. [Antoine Catton]

0.66 (2012-09-10)
-----------------

  * Add check_page_content promise generator. [Cedric Le Ninivin]

0.65 (2012-09-07)
-----------------

  * Add egg_test, recipe allowing to do "python setup.py test" on a list of
    eggs. [Rafael Monnerat, Cedric de Saint Martin]

0.64.2 (2012-08.28)
-------------------

  * Specify description on gitinit recipe. [Antoine Catton]

0.64.1 (2012-08-28)
-------------------

  * Fix: minor fix on downloader recipe in order to allow cross-device renaming.
    [Antoine Catton]

0.64 (2012-08-27)
-----------------

  * Fix: remove "template" recipe which was collinding with slapos.recipe.template.
    [Antoine Catton]

0.63 (2012-08-22)
-----------------

  * Add the ability to run command line in shellinabox. [Antoine Catton]
  * Add the ability to run shellinabox as root. (for LXC purpose) [Antoine Catton]
  * Add "uuid" recipe. [Antoine Catton]
  * Add "downloader" recipe. [Antoine Catton]

0.62 (2012-08-21)
-----------------

  * Add "wrapper" recipe. [Antoine Catton]
  * Add "gitinit" recipe. [Antoine Catton]
  * librecipe.execute code clean up and factorization. [Antoine Catton]
  * Add "template" recipe. [Antoine Catton]

0.61 (2012-08-17)
-----------------

  * Add "debug" option for slaprunner. [Alain Takoudjou]

0.60 (2012-08-13)
-----------------

  * New recipe: requestoptional, like "request", but won't fail if instance is
    not ready. [Cedric de Saint Martin]
  * Update zabbix to return strings as parameters. [Cedric de Saint Martin]
  * Add check in check_url_promise in case of empty URL. [Cedric de Saint
    Martin]
  * Upgrade slaprunner recipe to be compatible with newest version. [Alain
    Takoudjou]

0.59 (2012-07-12)
-----------------

  * Zabbix: add temperature monitoring using custom commands.

0.58 (2012-07-06)
-----------------

  * Agent rewrite. [Vincent Pelletier]

0.57 (2012-06-22)
-----------------

  * Do not use system curl. [Romain Courteaud]

0.56 (2012-06-18)
-----------------

  * Add signalwrapper, generate.mac, generate.password recipes. [Romain
    Courteaud]

0.55 (2012-06-18)
-----------------

  * Add slapmonitor and slapreport recipes. [Mohamadou Mbengue]

0.54.1 (2012-06-18)
-------------------

  * Fix 0.54 release containing wrong code in request.py.

0.54 (2012-06-18)
-----------------

  * Apache frontend: won't block sending slave informations to SlapOS Master
    in case of problem from one slave instance.[Cedric de Saint Martin]
  * Apache frontend will send IP informations for slaves in case slave is about
    custom domain. [Cedric de Saint Martin]
  * Ability to use LAMP applications without configuration. [Cedric de Saint
    Martin]
  * Users can specify custom domain in LAMP applications. [Cedric de Saint
    Martin]

0.53 (2012-06-07)
-----------------

  * Switch slaprunner into generic recipe, and add cloud9 recipe. [Cedric de
    Saint Martin]

0.52 (2012-05-16)
-----------------

  * Request bugfix: Correct default software_type (was: RootInstanceSoftware).
    [Cedric de Saint Martin]
  * Request will raise again if requested instance is not ready
    [Romain Courteaud]
  * Apache Frontend: assume apache is available from standard ports.
    Consequence: url connection parameter of slave instance doesn't contain
    port. [Cedric de Saint Martin]
  * Apache Frontend bugfix: correctly detect slave instance type (zope).
    [Cedric de Saint Martin]
  * Apache Frontend: "default" slave instances are available through http
    in addition to https. [Cedric de Saint Martin]
  * Apache Frontend: Configuration: Add mod_deflate and set ProxyPreserveHost
    [Cedric de Saint Martin]

0.51 (2012-05-14)
-----------------

  * LAMP stack bugfix: Users were losing data when slapgrid is ran (Don't
    erase htdocs if it already exist). [Cedric de Saint Martin]

0.50 (2012-05-12)
-----------------

  * LAMP stack bugfix: fix a crash where recipe was trying to restart
    non-existent httpd process. [Cedric de Saint Martin]
  * LAMP stack bugfix: don't erase htdocs at update [Cedric de Saint Martin]
  * Apache Frontend: Improve Apache configuration, inspired by Nexedi
    production frontend. [Cedric de Saint Martin]
  * Allow sysadmin of node to customize frontend instance.
    [Cedric de Saint Martin]
  * Apache Frontend: Change 'zope=true' option to 'type=zope'.
    [Cedric de Saint Martin]
  * Apache Frontend: listens to plain http port as well to redirect to https.
    [Cedric de Saint Martin]

0.49 (2012-05-10)
-----------------

  * Apache Frontend supports Zope and Varnish. [Cedric de Saint Martin]

0.48 (2012-04-26)
-----------------

  * New utility recipe: slapos.recipe.generate_output_if_input_not_null.
    [Cedric de Saint Martin]
  * New promise recipe: slapos.recipe.url_available: check if url returns http
    code 200. [Cedric de Saint Martin]
  * Fix: slapos.recipe.request won't raise anymore if instance is not ready.
    [Cedric de Saint Martin]
  * Fix: slapos.recipe.request won't assume instance reference if not
    specified. [Cedric de Saint Martin]

0.47 (2012-04-19)
-----------------

  * Slap Test Agent [Yingjie Xu]

0.46 (2012/04/12)
-----------------

  * xvfb and firefox initial release [Romain Courteaud]

0.45 (2012-03-29)
-----------------

  * slaprunner: change number of available partitions to 7 [Alain Takoudjou]

0.44 (2012-03-28)
-----------------

  * minor: apachephp: update apache configuration to work with Apache2.4

0.43 (2012-03-28)
-----------------

  * minor: erp5: add missing .zcml files into egg. [Cedric de Saint Martin]

0.42 (2012-03-26)
-----------------

 * erp5: Add web_checker recipe. [Tatuya Kamada]
 * erp5: Add generic_varnish recipe. [Tatuya Kamada]
 * erp5: Simplify erp5_update to only create the ERP5 site. [Romain Courteaud]
 * erp5: Allow to pass CA parameters from section. [Łukasz Nowak]

0.41 (2012-03-21)
-----------------

 * Release new "generic" version of KVM, includes frontend.
   [Cedric de Saint Martin]

0.40.1 (2012-03-01)
-------------------

 * Fix manifest to include files needed for apache. [Cedric de Saint Martin]

0.40 (2012-03-01)
-----------------

 * apache_frontend initial release. [Cedric de Saint Martin]

0.39 (2012-02-20)
-----------------

 * seleniumrunner initial release. [Cedric de Saint Martin]

0.38 (2011-12-05)
-----------------

 * erp5: Swtich to percona, as maatkit is obsoleted. [Sebastien Robin]
 * erp5: Improve haproxy configuration. [Sebastien Robin]
 * erp5: Support sphinxd. [Kazuhiko Shiozaki]
 * erp5: Improve and make logging more usual. [Sebastien Robin]
 * erp5: Allow mysql connection from localhost. [Romain Courteaud]
 * erp5: Allow to control Zope/Zeo cache [Arnaud Fontaine]
 * erp5: Increase precision in logs [Julien Muchembled]
 * erp5: Improve erp5 update [Arnaud Fontaine, Rafael Monnerat]

0.37 (2011-11-24)
-----------------

 * KVM : allow access to several KVM instances without SSL certificate duplicate
   problem. [Cedric de Saint Martin]

0.36 (2011-11-16)
-----------------

 * erp5testnode : the code of testnode is not in slapos repository anymore

0.35 (2011-11-10)
-----------------

 * KVM : Promise are now working properly. [Łukasz Nowak]
 * KVM : Use NoVNC with automatic login. [Cedric de Saint Martin]
 * KVM : Use websockify egg and remove numpy hack. [Cedric de Saint Martin]

0.34 (2011-11-08)
-----------------

  * Any LAMP software can specify its own php.ini [Alain Takoudjou]
  * LAMP : Fix bug where buildout does not has sufficient rights to update
    application parts. [Alain Takoudjou]
  * LAMP : Update formatting when returning list of renamed files.
    [Alain Takoudjou]

0.33 (2011-10-31)
-----------------

  * erp5 : use percona toolkit instead of maatkit [Sebastien Robin]

0.32 (2011-10-28)
-----------------

  * LAMP : Recipe can now call lampconfigure from slapos.toolbox which will
    configure PHP application instance when needed. [Alain Takoudjou Kamdem]

0.31 (2011-10-16)
-----------------

 * Split big redundant recipes into small ones. In order to factorize the code
   and have everything in the buildout file. [Antoine Catton, Romain Courteaud,
   Łukasz Nowak]
 * LAMP : Update apache and php configuration files to work with a lot of different
   PHP software. [Alain Takoudjou Kamdem]
 * LAMP : Recipe can launch scripts, move or remove files or directories
   when a given condition is filled. Useful when PHP apps require you to
   remove "admin" directory after configuration for example.
   [Alain Takoudjou Kamdem]

0.30 (2011-10-06)
-----------------

 * LAMP : Update apache and php configuration files to work with a lot of different
   PHP software. [Alain Takoudjou Kamdem]

0.29 (2011-09-28)
-----------------

 * mysql: bug fix on database recovering (avoid importing dump two times). [Antoine Catton]

0.28 (2011-09-27)
-----------------

 * lamp.request: requesting the mariadb software release instead of itself. [Antoine Catton]
 * lamp.request: adding support of remote backup repo (using a different
   software type). The default remote backup is a davstorage. [Antoine Catton]

0.27 (2011-09-27)
-----------------

 * mysql: add backup and backup recovering using different software type. [Antoine Catton]

0.26 (2011-09-27)
-----------------

 * Davstorage: returning more explicit url (using webdav scheme). [Antoine Catton]
 * Other mysql minor fixes. [Antoine Catton]

0.25 (2011-09-21)
-----------------

 * mysql: Restore to default behaviour. [Antoine Catton]
 * mysql: Use mysqldump instead of non trustable backup system. [Antoine Catton]

0.24 (2011-09-19)
-----------------

 * mysql: Unhardcode the requested url. [Antoine Catton]

0.23 (2011-09-19)
-----------------

 * Clean code in mysql recipe [Cedric de Saint Martin]
 * librecipe: Provide createPromiseWrapper method. [Antoine Catton]
 * kvm: Expose promisee checks to slapgrid. [Antoine Catton]
 * davstorage: Initial version. [Antoine Catton]
 * mysql: Support DAV backup. [Antoine Catton]

0.22 (2011-09-12)
-----------------

 * Fix haproxy setup for erp5 [Sebastien Robin]

0.21 (2011-09-12)
-----------------

 * Update PHP configuration to set session and date options.
   [Alain Takoudjou Kamdem]
 * Improve logrotate policy and haproxy config for erp5
   [Sebastien Robin]

0.20 (2011-09-07)
-----------------

 * Update and fix KVM/noVNC installation to be compatible with new WebSocket
   protocol (HyBi-10) required by Chrome >= 14 and Firefox >= 7.
   [Cedric de Saint Martin]

0.19 (2011-09-06)
-----------------

 * Update PHP configuration to disable debug logging. [Cedric de Saint Martin]

0.18 (2011-08-25)
-----------------

 * Repackage egg to include needed .bin files. [Cedric de Saint Martin]

0.17 (2011-08-25)
-----------------

 * Add XWiki software release [Cedric de Saint Martin]

0.16 (2011-07-15)
-----------------

 * Improve Vifib and pure ERP5 instantiation [Rafael Monnerat]
 * Use configurator for Vifib [Rafael Monnerat]

0.15 (2011-07-13)
-----------------

 * Encrypt connection by default. [Vivien Alger]

0.14 (2011-07-13)
-----------------

 * Provide new way to instantiate kvm. [Cedric de Saint Martin, Vivien Alger]

0.13 (2011-07-13)
-----------------

 * Implement generic execute_wait wrapper, which allows to wait for some files
   to appear before starting service depending on it. [Łukasz Nowak]

0.12 (2011-07-11)
-----------------

 * Fix slaprunner, phpmyadmin software releases, added
   wordpress software release. [Cedric de Saint Martin]

0.11 (2011-07-07)
-----------------

 * Enable test suite runner for vifib.

0.10 (2011-07-01)
-----------------

 * Add PHPMyAdmin software release used in SlapOS tutorials
   [Cedric de Saint Martin]
 * Add slaprunner software release [Cedric de Saint Martin]


0.9 (2011-06-24)
----------------

 * mysql recipe : Changing slapos.recipe.erp5.execute to
   slapos.recipe.librecipe.execute [Cedric de Saint Martin]

0.8 (2011-06-15)
----------------

 * Add MySQL and MariaDB standalone software release and recipe
   [Cedric de Saint Martin]
 * Fixed slapos.recipe.erp5testnode instantiation [Sebastien Robin]

0.7 (2011-06-14)
----------------

 * Fix slapos.recipe.erp5 package by providing site.zcml in it. [Łukasz Nowak]
 * Improve slapos.recipe.erp5testnode partition instantiation error reporting
   [Sebastien Robin]

0.6 (2011-06-13)
----------------

 * Fixed slapos.recipe.erp5 instantiation. [Łukasz Nowak]

0.5 (2011-06-13)
----------------

 * Implement zabbix agent instantiation. [Łukasz Nowak]
 * Drop dependency on Zope2. [Łukasz Nowak]
 * Share more in slapos.recipe.librecipe module. [Łukasz Nowak]

0.4 (2011-06-09)
----------------

 * Remove reference to slapos.tool.networkcache as it was removed from pypi. [Łukasz Nowak]
 * Add Kumofs standalone software release and recipe [Cedric de Saint Martin]
 * Add Memcached standalone software release and recipe [Cedric de Saint Martin]

0.3 (2011-06-09)
----------------

 * Moved out template and build to separate distributions [Łukasz Nowak]
 * Depend on slapos.core instead of depracated slapos.slap [Romain Courteaud]
 * Fix apache module configuration [Kazuhiko Shiozaki]
 * Allow to control full environment in erp5 module [Łukasz Nowak]

0.2 (2011-05-30)
----------------

  * Allow to pass zope_environment in erp5 entry point [Łukasz Nowak]

0.1 (2011-05-27)
----------------

  * All slapos.recipe.* became slapos.cookbook:* [Łukasz Nowak]
