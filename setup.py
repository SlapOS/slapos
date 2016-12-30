##############################################################################
#
# Copyright (c) 2010-2013 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from setuptools import setup, find_packages
import glob
import os

version = '1.0.44'
name = 'slapos.cookbook'
long_description = open("README.rst").read() + "\n" + \
    open("CHANGES.rst").read() + "\n"

for f in sorted(glob.glob(os.path.join('slapos', 'recipe', 'README.*.rst'))):
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
      maintainer="Nexedi",
      maintainer_email="info@nexedi.com",
      url="https://lab.nexedi.com/nexedi/slapos",
      keywords='slapos recipe',
      license='GPLv3',
      namespace_packages=['slapos', 'slapos.recipe'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
        'jsonschema',
        'hexagonit.recipe.download',
        'netaddr', # to manipulate on IP addresses
        'setuptools', # namespaces
        'inotifyx', # to watch filesystem changes (used in lockfile)
        'lock_file', #another lockfile implementation for multiprocess
        'slapos.core', # uses internally
        'zc.buildout', # plays with buildout
        'zc.recipe.egg', # for scripts generation
        'pytz', # for timezone database
        ],
      zip_safe=True,
      entry_points={
        'zc.buildout': [
          'addresiliency = slapos.recipe.addresiliency:Recipe',
          'accords = slapos.recipe.accords:Recipe',
          'apache.zope.backend = slapos.recipe.apache_zope_backend:Recipe',
          'apacheperl = slapos.recipe.apacheperl:Recipe',
          'apachephp = slapos.recipe.apachephp:Recipe',
          'apachephpconfigure = slapos.recipe.apachephpconfigure:Recipe',
          'apacheproxy = slapos.recipe.apacheproxy:Recipe',
          'boinc = slapos.recipe.boinc:Recipe',
          'boinc.app = slapos.recipe.boinc:App',
          'boinc.client = slapos.recipe.boinc:Client',
          'bonjourgrid = slapos.recipe.bonjourgrid:Recipe',
          'bonjourgrid.client = slapos.recipe.bonjourgrid:Client',
          'certificate_authority = slapos.recipe.certificate_authority:Recipe',
          'certificate_authority.request = slapos.recipe.certificate_authority:Request',
          'check_page_content = slapos.recipe.check_page_content:Recipe',
          'check_port_listening = slapos.recipe.check_port_listening:Recipe',
          'check_url_available = slapos.recipe.check_url_available:Recipe',
          'check_parameter = slapos.recipe.check_parameter:Recipe',
          'cloud9 = slapos.recipe.cloud9:Recipe',
          'cloudooo.test = slapos.recipe.erp5_test:CloudoooRecipe',
          'condor = slapos.recipe.condor:Recipe',
          'condor.submit = slapos.recipe.condor:AppSubmit',
          'copyfilelist = slapos.recipe.copyfilelist:Recipe',
          'cron = slapos.recipe.dcron:Recipe',
          'cron.d = slapos.recipe.dcron:Part',
          'davstorage = slapos.recipe.davstorage:Recipe',
          'dropbear = slapos.recipe.dropbear:Recipe',
          'dropbear.add_authorized_key = slapos.recipe.dropbear:AddAuthorizedKey',
          'dropbear.client = slapos.recipe.dropbear:Client',
          'duplicity = slapos.recipe.duplicity:Recipe',
          'egg_test = slapos.recipe.erp5_test:EggTestRecipe',
          'equeue = slapos.recipe.equeue:Recipe',
          'erp5.bootstrap = slapos.recipe.erp5_bootstrap:Recipe',
          'erp5.promise = slapos.recipe.erp5_promise:Recipe',
          'erp5.test = slapos.recipe.erp5_test:Recipe',
          'erp5scalabilitytestbed = slapos.recipe.erp5scalabilitytestbed:Recipe',
          'erp5testnode = slapos.recipe.erp5testnode:Recipe',
          'firefox = slapos.recipe.firefox:Recipe',
          'fontconfig = slapos.recipe.fontconfig:Recipe',
          'free_port = slapos.recipe.free_port:Recipe',
          'generate.mac = slapos.recipe.random:Mac',
          'generate.password = slapos.recipe.random:Password',
          'generic.cloudooo = slapos.recipe.generic_cloudooo:Recipe',
          'generic.kumofs = slapos.recipe.generic_kumofs:Recipe',
          'generic.memcached = slapos.recipe.generic_memcached:Recipe',
          'generic.mysql = slapos.recipe.generic_mysql:Recipe',
          'generic.mysql.wrap_update_mysql = slapos.recipe.generic_mysql:WrapUpdateMySQL',
          'generic.mysql.wrap_mysqld = slapos.recipe.generic_mysql:WrapMySQLd',
          'generic.varnish = slapos.recipe.generic_varnish:Recipe',
          'generic.zope = slapos.recipe.generic_zope:Recipe',
          'generic.zope.zeo.client = slapos.recipe.generic_zope_zeo_client:Recipe',
          'gitinit = slapos.recipe.gitinit:Recipe',
          'haproxy = slapos.recipe.haproxy:Recipe',
          'ipv4toipv6 = slapos.recipe.6tunnel:FourToSix',
          'ipv6toipv4 = slapos.recipe.6tunnel:SixToFour',
          'jsondump = slapos.recipe.jsondump:Recipe',
          'kumofs = slapos.recipe.kumofs:Recipe',
          'kvm.frontend = slapos.recipe.kvm_frontend:Recipe',
          'lamp = slapos.recipe.lamp:Request',
          'lamp.generic = slapos.recipe.lampgeneric:Recipe',
          'lamp.request = slapos.recipe.lamp:Request',
          'lamp.simple = slapos.recipe.lamp:Simple',
          'lamp.static = slapos.recipe.lamp:Static',
          'libcloud = slapos.recipe.libcloud:Recipe',
          'libcloudrequest = slapos.recipe.libcloudrequest:Recipe',
          'lockfile = slapos.recipe.lockfile:Recipe',
          'logrotate = slapos.recipe.logrotate:Recipe',
          'logrotate.d = slapos.recipe.logrotate:Part',
          'memcached = slapos.recipe.memcached:Recipe',
          'mkdirectory = slapos.recipe.mkdirectory:Recipe',
          'mioga.instantiate = slapos.recipe.mioga.instantiate:Recipe',
          'mydumper = slapos.recipe.mydumper:Recipe',
          'mysql = slapos.recipe.mysql:Recipe',
          'nbdserver = slapos.recipe.nbdserver:Recipe',
          'neoppod.admin = slapos.recipe.neoppod:Admin',
          'neoppod.master = slapos.recipe.neoppod:Master',
          'neoppod.storage = slapos.recipe.neoppod:Storage',
          'nosqltestbed = slapos.recipe.nosqltestbed:NoSQLTestBed',
          'notifier = slapos.recipe.notifier:Recipe',
          'notifier.callback = slapos.recipe.notifier:Callback',
          'notifier.notify = slapos.recipe.notifier:Notify',
          'novnc = slapos.recipe.novnc:Recipe',
          'onetimeupload = slapos.recipe.onetimeupload:Recipe',
          'pbs = slapos.recipe.pbs:Recipe',
          'postgres = slapos.recipe.postgres:Recipe',
          'postgres.export = slapos.recipe.postgres.backup:ExportRecipe',
          'postgres.import = slapos.recipe.postgres.backup:ImportRecipe',
          'proactive = slapos.recipe.proactive:Recipe',
          'publish = slapos.recipe.publish:Recipe',
          'publish.serialised = slapos.recipe.publish:Serialised',
          'publish-early = slapos.recipe.publish_early:Recipe',
          'publishsection = slapos.recipe.publish:PublishSection',
          'publishurl = slapos.recipe.publishurl:Recipe',
          'random.time = slapos.recipe.random:Time',
          'readline = slapos.recipe.readline:Recipe',
          'redis.server = slapos.recipe.redis:Recipe',
          'request = slapos.recipe.request:Recipe',
          'request.serialised = slapos.recipe.request:Serialised',
          'request.edge = slapos.recipe.request:RequestEdge',
          'requestoptional = slapos.recipe.request:RequestOptional',
          're6stnet.registry = slapos.recipe.re6stnet:Recipe',
          'reverseproxy.nginx = slapos.recipe.reverse_proxy_nginx:Recipe',
          'seleniumrunner = slapos.recipe.seleniumrunner:Recipe',
          'sheepdogtestbed = slapos.recipe.sheepdogtestbed:SheepDogTestBed',
          'shell = slapos.recipe.shell:Recipe',
          'shellinabox = slapos.recipe.shellinabox:Recipe',
          'signalwrapper= slapos.recipe.signal_wrapper:Recipe',
          'simplelogger = slapos.recipe.simplelogger:Recipe',
          'simplehttpserver = slapos.recipe.simplehttpserver:Recipe',
          'siptester = slapos.recipe.siptester:SipTesterRecipe',
          'slapconfiguration = slapos.recipe.slapconfiguration:Recipe',
          'slapconfiguration.serialised = slapos.recipe.slapconfiguration:Serialised',
          'slapconfiguration.jsondump = slapos.recipe.slapconfiguration:JsonDump',
          'slapcontainer = slapos.recipe.container:Recipe',
          'softwaretype = slapos.recipe.softwaretype:Recipe', # BBB
          'sphinx= slapos.recipe.sphinx:Recipe',
          'squid = slapos.recipe.squid:Recipe',
          'sshkeys_authority = slapos.recipe.sshkeys_authority:Recipe',
          'sshkeys_authority.request = slapos.recipe.sshkeys_authority:Request',
          'stunnel = slapos.recipe.stunnel:Recipe',
          'switch-softwaretype = slapos.recipe.switch_softwaretype:Recipe',
          'symbolic.link = slapos.recipe.symbolic_link:Recipe',
          'tidstorage = slapos.recipe.tidstorage:Recipe',
          'trac = slapos.recipe.trac:Recipe',
          'urlparse = slapos.recipe._urlparse:Recipe',
          'uuid = slapos.recipe._uuid:Recipe',
          'userinfo = slapos.recipe.userinfo:Recipe',
          'waitfor = slapos.recipe.waitfor:Recipe',
          'webchecker = slapos.recipe.web_checker:Recipe',
          'wrapper = slapos.recipe.wrapper:Recipe',
          'xvfb = slapos.recipe.xvfb:Recipe',
          'xwiki = slapos.recipe.xwiki:Recipe',
          'zabbixagent = slapos.recipe.zabbixagent:Recipe',
          'zimbra.kvm = slapos.recipe.zimbra_kvm:Recipe',
          'zeo = slapos.recipe.zeo:Recipe',
          'zero-knowledge.read = slapos.recipe.zero_knowledge:ReadRecipe',
          'zero-knowledge.write = slapos.recipe.zero_knowledge:WriteRecipe'
        ],
        'slapos.recipe.nosqltestbed.plugin': [
          'kumo = slapos.recipe.nosqltestbed.kumo:KumoTestBed',
        ],
      },
      test_suite='slapos.test',
      tests_require=[
        'jsonschema',
        'mock',
      ],
    )
