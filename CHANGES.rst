Changes
=======
1.0.92 (2019-02-21)
-------------------

* plugin recipe: improve recipe to correctly generate promise with parameters which contain control characters

1.0.85 (2018-12-28)
-----------------------

* Drop ``slapos.recipe:xvfb``, use simple ``slapos.recipe:wrapper`` instead.
* Drop ``slapos.recipe:seleniumrunner`` and ``slapos.recipe:firefox``, they
  were not used.
* Encode unicode to UTF-8 on ``slapos.recipe:request`` and 
  ``slapos.recipe:slapconfiguration`` 

1.0.75 (2018-09-04)
-------------------

* erp5_test: stop using erp5_test recipe
* random: fix password generation with newlines
* erp5testnode: enable password authentication for scalability test system
* pbs: Ignore numerical IDs (UID/GID) when push
* request: add requestoptional.serialised

1.0.65 (2018-06-22)
-------------------

* Automatic restart of services when configuration changes
* erp5_test: define cloudooo-retry-count value in test
* userinfo: expose values as string

1.0.62 (2018-04-10)
-------------------

* promise.plugin: new recipe for python promises plugin script generation

1.0.59 (2018-03-15)
-------------------
* librecipe.execute: fix convert process arguments to string formatting.

1.0.58 (2018-03-14)
-------------------

* generic.mysql: unregister UDFs before (re)adding UDFs
* Remove obsolete/unused recipes.
* neoppod: add support for new --dedup storage option.
* Use inotify-simple instead of inotifyx.
* erp5.test: remove duplicated code.
* librecipe: bugfixes found by pylint, performance improvements, and major
  refactoring of executable wrappers.
* GenericBaseRecipe.createWrapper: remove 'comments' parameter.
* Drop the 'parameters-extra' option and always forward extra parameters.
* wrapper: new 'private-dev-shm' option (useful for wendelin.core).
* generic.cloudooo: OnlyOffice converter support odf.
* erp5testnode: don't tell git to ignore SSL errors.

1.0.53 (2017-09-13)
-------------------

* check_port_listening: workaround for shebang limitation, reduce to a single file
* erp5.test: pass new --conversion_server_url option to runUnitTest

1.0.52 (2017-07-04)
-------------------

* wrapper: Add option to reserve CPU core
* slapconfiguration: Recipe reads partitions resource file
* neoppod: add support for new --disable-drop-partitions storage option
* random: Fix the monkeypatch in random.py to incorporate the recent changes in buildout 'get' function
* random: Add Integer recipe.
* librecipe.execute: Notify on file moved
* zero_knowledge: allow to set destination folder of configuration file


1.0.50 (2017-04-18)
-------------------

* pbs: Do not parallelize calculus when the heaviest task is IO
* re6st-registry: Refactor integration with re6st registry
* erp5testnode: make shellinabox reusing password file of pwgen

1.0.48 (2017-01-31)
-------------------

* random-recipe: add option create-once to prevent storage file deletion by buildout

1.0.45 (2017-01-09)
-------------------

* recipe: set default timeout of check url promise to 20 seconds

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
* Fix workaround for long shebang (place script on bin)

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

For older entries, see https://lab.nexedi.com/nexedi/slapos/blob/a662db75cc840df9d4664a9d048ef28ebfff4d50/CHANGES.rst
