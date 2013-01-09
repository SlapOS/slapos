from setuptools import setup, find_packages
import glob
import os

version = '0.68.2-dev'
name = 'slapos.cookbook'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read() + "\n"

for f in sorted(glob.glob(os.path.join('slapos', 'recipe', 'README.*.txt'))):
  long_description += '\n' + open(f).read() + '\n'

# extras_requires are not used because of
#   https://bugs.launchpad.net/zc.buildout/+bug/85604
setup(name=name,
      version=version,
      description="SlapOS recipes.",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout :: Recipe",
          "Programming Language :: Python",
        ],
      keywords='slapos recipe',
      license='GPLv3',
      namespace_packages=['slapos', 'slapos.recipe'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
        'PyXML', # for full blown python interpreter
        'lxml', # for full blown python interpreter
        'netaddr', # to manipulate on IP addresses
        'setuptools', # namespaces
        'inotifyx', # to watch filesystem changes (used in lockfile)
        'lock_file', #another lockfile implementation for multiprocess
        'slapos.core', # uses internally
#        'slapos.toolbox', # needed for libcloud, cloudmgr, disabled for now
        'xml_marshaller', # need to communication with slapgrid
        'zc.buildout', # plays with buildout
        'zc.recipe.egg', # for scripts generation
        'pytz', # for timezone database
        ],
      zip_safe=True,
      entry_points={
        'zc.buildout': [
          'addresiliency = slapos.recipe.addresiliency:Recipe',
          'agent = slapos.recipe.agent:Recipe',
          'apache.frontend = slapos.recipe.apache_frontend:Recipe',
          'apachephp = slapos.recipe.apachephp:Recipe',
          'apacheproxy = slapos.recipe.apacheproxy:Recipe',
          'apache.zope.backend = slapos.recipe.apache_zope_backend:Recipe',
	        'boinc = slapos.recipe.boinc:Recipe',
          'boinc.app = slapos.recipe.boinc:App',
          'boinc.client = slapos.recipe.boinc:Client',
          'bonjourgrid = slapos.recipe.bonjourgrid:Recipe',
          'bonjourgrid.client = slapos.recipe.bonjourgrid:Client',
          'certificate_authority.request = slapos.recipe.certificate_authority:Request',
          'certificate_authority = slapos.recipe.certificate_authority:Recipe',
          'check_port_listening = slapos.recipe.check_port_listening:Recipe',
          'check_url_available = slapos.recipe.check_url_available:Recipe',
          'check_page_content = slapos.recipe.check_page_content:Recipe',
          'cloud9 = slapos.recipe.cloud9:Recipe',
          'cloudooo.test = slapos.recipe.erp5_test:CloudoooRecipe',
	        'condor = slapos.recipe.condor:Recipe',
          'condor.submit = slapos.recipe.condor:AppSubmit',
          'cron.d = slapos.recipe.dcron:Part',
          'cron = slapos.recipe.dcron:Recipe',
          'davstorage = slapos.recipe.davstorage:Recipe',
          'downloader = slapos.recipe.downloader:Recipe',
          'dropbear.add_authorized_key = slapos.recipe.dropbear:AddAuthorizedKey',
          'dropbear.client = slapos.recipe.dropbear:Client',
          'dropbear = slapos.recipe.dropbear:Recipe',
          'dumpmdb = slapos.recipe.dumpmdb:Recipe',
          'duplicity = slapos.recipe.duplicity:Recipe',
          'egg_test = slapos.recipe.erp5_test:EggTestRecipe',
          'equeue = slapos.recipe.equeue:Recipe',
          'erp5.bootstrap = slapos.recipe.erp5_bootstrap:Recipe',
          'erp5.promise = slapos.recipe.erp5_promise:Recipe',
          'erp5scalabilitytestbed = slapos.recipe.erp5scalabilitytestbed:Recipe',
          'erp5testnode = slapos.recipe.erp5testnode:Recipe',
          'erp5.test = slapos.recipe.erp5_test:Recipe',
          'erp5.update = slapos.recipe.erp5_update:Recipe',
          'firefox = slapos.recipe.firefox:Recipe',
          'fontconfig = slapos.recipe.fontconfig:Recipe',
          'generate.mac = slapos.recipe.generatemac:Recipe',
          'generate.password = slapos.recipe.generatepassword:Recipe',
          'generic.cloudooo = slapos.recipe.generic_cloudooo:Recipe',
          'generic.kumofs = slapos.recipe.generic_kumofs:Recipe',
          'generic.memcached = slapos.recipe.generic_memcached:Recipe',
          'generic.mysql = slapos.recipe.generic_mysql:Recipe',
          'generic.varnish = slapos.recipe.generic_varnish:Recipe',
          'generic.zope = slapos.recipe.generic_zope:Recipe',
          'generic.zope.zeo.client = slapos.recipe.generic_zope_zeo_client:Recipe',
          'gitinit = slapos.recipe.gitinit:Recipe',
          'haproxy = slapos.recipe.haproxy:Recipe',
          'helloworld = slapos.recipe.helloworld:Recipe',
          'importmdb = slapos.recipe.importmdb:Recipe',
          'java = slapos.recipe.java:Recipe',
          'kumofs = slapos.recipe.kumofs:Recipe',
          'kvm.frontend = slapos.recipe.kvm_frontend:Recipe',
          'kvm = slapos.recipe.kvm:Recipe',
          'lamp.request = slapos.recipe.lamp:Request',
          'lamp.simple = slapos.recipe.lamp:Simple',
          'lamp = slapos.recipe.lamp:Request',
          'lamp.static = slapos.recipe.lamp:Static',
          'libcloudrequest = slapos.recipe.libcloudrequest:Recipe',
          'libcloud = slapos.recipe.libcloud:Recipe',
          'lockfile = slapos.recipe.lockfile:Recipe',
          'logrotate.d = slapos.recipe.logrotate:Part',
          'logrotate = slapos.recipe.logrotate:Recipe',
          'memcached = slapos.recipe.memcached:Recipe',
          'mkdirectory = slapos.recipe.mkdirectory:Recipe',
          'mydumper = slapos.recipe.mydumper:Recipe',
          'mysql = slapos.recipe.mysql:Recipe',
          'nbdserver = slapos.recipe.nbdserver:Recipe',
          'nosqltestbed = slapos.recipe.nosqltestbed:NoSQLTestBed',
          'notifier.callback = slapos.recipe.notifier:Callback',
          'notifier.notify = slapos.recipe.notifier:Notify',
          'notifier = slapos.recipe.notifier:Recipe',
          'novnc = slapos.recipe.novnc:Recipe',
          'onetimeupload = slapos.recipe.onetimeupload:Recipe',
          'pbs = slapos.recipe.pbs:Recipe',
          'proactive = slapos.recipe.proactive:Recipe',
          'publish = slapos.recipe.publish:Recipe',
          'publishurl = slapos.recipe.publishurl:Recipe',
          'pwgen = slapos.recipe.pwgen:Recipe',
          'pwgen.stable = slapos.recipe.pwgen:StablePasswordGeneratorRecipe',
          'redis.server = slapos.recipe.redis:Recipe',
          'requestoptional = slapos.recipe.request:RequestOptional',
          'request = slapos.recipe.request:Recipe',
          'seleniumrunner = slapos.recipe.seleniumrunner:Recipe',
          'sheepdogtestbed = slapos.recipe.sheepdogtestbed:SheepDogTestBed',
          'shellinabox = slapos.recipe.shellinabox:Recipe',
          'shell = slapos.recipe.shell:Recipe',
          'signalwrapper= slapos.recipe.signal_wrapper:Recipe',
          'simplelogger = slapos.recipe.simplelogger:Recipe',
          'siptester = slapos.recipe.siptester:SipTesterRecipe',
          'slapconfiguration = slapos.recipe.slapconfiguration:Recipe',
          'slapcontainer = slapos.recipe.container:Recipe',
          'slapmonitor = slapos.recipe.slapmonitor:Recipe',
          'slapreport = slapos.recipe.slapreport:Recipe',
          'slaprunner = slapos.recipe.slaprunner:Recipe',
          'slaprunner.test = slapos.recipe.slaprunner:Test',
          'softwaretype = slapos.recipe.softwaretype:Recipe',
          'sphinx= slapos.recipe.sphinx:Recipe',
          'sshkeys_authority.request = slapos.recipe.sshkeys_authority:Request',
          'sshkeys_authority = slapos.recipe.sshkeys_authority:Recipe',
          'stunnel = slapos.recipe.stunnel:Recipe',
          'symbolic.link = slapos.recipe.symbolic_link:Recipe',
          'testnode = slapos.recipe.testnode:Recipe',
          'tidstorage = slapos.recipe.tidstorage:Recipe',
          'urlparse = slapos.recipe._urlparse:Recipe',
          'uuid = slapos.recipe._uuid:Recipe',
          'vifib = slapos.recipe.vifib:Recipe',
          'waitfor = slapos.recipe.waitfor:Recipe',
          'webchecker = slapos.recipe.web_checker:Recipe',
          'wrapper = slapos.recipe.wrapper:Recipe',
          'xvfb = slapos.recipe.xvfb:Recipe',
          'xwiki = slapos.recipe.xwiki:Recipe',
          'zabbixagent = slapos.recipe.zabbixagent:Recipe',
          'zeo = slapos.recipe.zeo:Recipe',
        ],
        'slapos.recipe.nosqltestbed.plugin': [
          'kumo = slapos.recipe.nosqltestbed.kumo:KumoTestBed',
        ],
      },
    )

