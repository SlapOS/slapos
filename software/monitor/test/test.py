##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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

import os
import re
import requests
import xml.etree.ElementTree as ET
from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class ServicesTestCase(SlapOSInstanceTestCase):

  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
    ]
    expected_process_names = [
      'monitor-httpd-{hash}-on-watch',
      'crond-{hash}-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)


class MonitorTestMixin(object):
  monitor_setup_url_key = 'monitor-setup-url'

  def test_monitor_setup(self):
    connection_parameter_dict = self\
      .computer_partition.getConnectionParameterDict()
    self.assertTrue(
      self.monitor_setup_url_key in connection_parameter_dict,
      '%s not in %s' % (self.monitor_setup_url_key, connection_parameter_dict))
    monitor_setup_url_value = connection_parameter_dict[
      self.monitor_setup_url_key]
    monitor_url_match = re.match(r'.*url=(.*)', monitor_setup_url_value)
    self.assertNotEqual(
      None, monitor_url_match, '%s not parsable' % (monitor_setup_url_value,))
    self.assertEqual(1, len(monitor_url_match.groups()))
    monitor_url = monitor_url_match.groups()[0]
    monitor_url_split = monitor_url.split('&')
    self.assertEqual(
      3, len(monitor_url_split), '%s not splitabble' % (monitor_url,))
    self.monitor_url = monitor_url_split[0]
    monitor_username = monitor_url_split[1].split('=')
    self.assertEqual(
      2, len(monitor_username), '%s not splittable' % (monitor_username))
    monitor_password = monitor_url_split[2].split('=')
    self.assertEqual(
      2, len(monitor_password), '%s not splittable' % (monitor_password))
    self.monitor_username = monitor_username[1]
    self.monitor_password = monitor_password[1]

    opml_text = requests.get(self.monitor_url, verify=False).text
    opml = ET.fromstring(opml_text)

    body = opml[1]
    self.assertEqual('body', body.tag)

    outline_list = body[0].findall('outline')

    self.assertEqual(
      self.monitor_configuration_list,
      [q.attrib for q in outline_list]
    )

    expected_status_code_list = []
    got_status_code_list = []
    for monitor_configuration in self.monitor_configuration_list:
      status_code = requests.get(
          monitor_configuration['url'],
          verify=False,
          auth=(self.monitor_username, self.monitor_password)
        ).status_code
      expected_status_code_list.append(
        {
          'url': monitor_configuration['url'],
          'status_code': 200
        }
      )
      got_status_code_list.append(
        {
          'url': monitor_configuration['url'],
          'status_code': status_code
        }
      )
    self.assertEqual(
      expected_status_code_list,
      got_status_code_list
    )


class EdgeSlaveMixin(MonitorTestMixin):
  __partition_reference__ = 'edge'
  instance_max_retry = 20

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'edgetest'

  def requestEdgetestSlave(self, partition_reference, partition_parameter_kw):
    software_url = self.getSoftwareURL()
    self.slap.request(
      software_release=software_url,
      software_type='edgetest',
      partition_reference=partition_reference,
      partition_parameter_kw=partition_parameter_kw,
      shared=True
    )

  def setUp(self):
    self.bot_partition_path = os.path.join(
      self.slap.instance_directory,
      self.__partition_reference__ + '1')
    self.surykatka_json = os.path.join(
        self.bot_partition_path, 'srv', 'surykatka.json')
    self.monitor_configuration_list = [
      {
        'xmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,),
        'version': 'RSS',
        'title': 'testing partition 0',
        'url': 'https://[%s]:9700/share/private/' % (self._ipv6_address,),
        'text': 'testing partition 0',
        'type': 'rss',
        'htmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,)
      },
      {
        'xmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,),
        'version': 'RSS',
        'title': 'edgebot-1',
        'url': 'https://[%s]:9701/share/private/' % (self._ipv6_address,),
        'text': 'edgebot-1',
        'type': 'rss',
        'htmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,)
      }
    ]

  def assertSurykatkaIni(self):
    surykatka_ini = open(
      os.path.join(
        self.bot_partition_path, 'etc', 'surykatka.ini')).read().strip()

    expected = self.surykatka_ini % dict(
        partition_path=self.bot_partition_path)
    self.assertEqual(
      expected.strip(),
      surykatka_ini)

  def assertPromiseContent(self, name, content):
    promise = open(
      os.path.join(
        self.bot_partition_path, 'etc', 'plugin', name
      )).read().strip()

    self.assertTrue(content in promise)

  def assertSurykatkaBotPromise(self):
    self.assertPromiseContent(
      'surykatka-bot-promise.py',
      "'report': 'bot_status'")
    self.assertPromiseContent(
      'surykatka-bot-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

  def assertSurykatkaCron(self):
    surykatka_cron = open(
      os.path.join(
        self.bot_partition_path, 'etc', 'cron.d', 'surykatka-status')
        ).read().strip()
    self.assertEqual(
      '*/2 * * * * %s' % (
        os.path.join(
          self.bot_partition_path, 'bin', 'surykatka-status-json'),),
      surykatka_cron
    )

  def initiateSurykatkaRun(self):
    try:
      self.slap.waitForInstance(max_retry=2)
    except Exception:
      pass


class TestEdge(EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_ini = """[SURYKATKA]
INTERVAL = 120
SQLITE = %(partition_path)s/srv/surykatka.db
URL =
  https://www.erp5.com/
  https://www.erp5.org/"""

  def assertSurykatkaPromises(self):
    self.assertSurykatkaBotPromise()
    self.assertPromiseContent(
      'backend-300-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'backend-300-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'backend-300-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'backend-300-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'backend-300-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

    self.assertPromiseContent(
      'backend-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

  def test(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-300',
      {'url': 'https://www.erp5.org/', 'status-code': '300'},
    )

    self.initiateSurykatkaRun()
    self.assertSurykatkaIni()
    self.assertSurykatkaPromises()
    self.assertSurykatkaCron()


class TestEdgeDnsCheckFrontendIp(EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_ini = """[SURYKATKA]
INTERVAL = 120
SQLITE = %(partition_path)s/srv/surykatka.db
DNS =
  127.0.1.1
  127.0.1.2

URL =
  https://www.erp5.com/"""

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'dns': '127.0.1.1 127.0.1.2',
      'check-frontend-ip': '127.0.0.1 127.0.0.2',
    }

  def assertSurykatkaPromises(self):
    self.assertSurykatkaBotPromise()

    self.assertPromiseContent(
      'backend-promise.py',
      "'ip-list': '127.0.0.1 127.0.0.2'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

  def test(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )

    self.initiateSurykatkaRun()
    self.assertSurykatkaIni()
    self.assertSurykatkaPromises()
    self.assertSurykatkaCron()


class TestEdgeCheckStatusCode(EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_ini = """[SURYKATKA]
INTERVAL = 120
SQLITE = %(partition_path)s/srv/surykatka.db
DNS =
  127.0.1.1
  127.0.1.2

URL =
  https://www.erp5.com/"""

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'status-code': '500',
    }

  def assertSurykatkaPromises(self):
    self.assertSurykatkaBotPromise()
    self.assertPromiseContent(
      'backend-501-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'backend-501-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'backend-501-promise.py',
      "'status-code': '501'")
    self.assertPromiseContent(
      'backend-501-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'backend-501-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

    self.assertPromiseContent(
      'backend-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'status-code': '500'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_json,)
    )

  def test(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-501',
      {'url': 'https://www.erp5.com/', 'status-code': '501'},
    )

    self.initiateSurykatkaRun()
    self.assertSurykatkaIni()
    self.assertSurykatkaPromises()
    self.assertSurykatkaCron()
