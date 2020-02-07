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

import glob
import json
import os
import re
import requests
import subprocess
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

  def updateSurykatkaDict(self):
    class_list = self.surykatka_dict.keys()
    for class_ in class_list:
      update_dict = {}
      update_dict['ini-file'] = os.path.join(
        self.bot_partition_path, 'etc', 'surykatka-%s.ini' % (class_,))
      update_dict['json-file'] = os.path.join(
        self.bot_partition_path, 'srv', 'surykatka-%s.json' % (class_,))
      update_dict['status-json'] = os.path.join(
        self.bot_partition_path, 'bin', 'surykatka-status-json-%s' % (class_,))
      update_dict['bot-promise'] = 'surykatka-bot-promise-%s.py' % (class_,)
      update_dict['status-cron'] = os.path.join(
        self.bot_partition_path, 'etc', 'cron.d', 'surykatka-status-%s' % (
          class_,))
      update_dict['db_file'] = os.path.join(
        self.bot_partition_path, 'srv', 'surykatka-%s.db' % (class_,))
      self.surykatka_dict[class_].update(update_dict)

  def setUp(self):
    self.bot_partition_path = os.path.join(
      self.slap.instance_directory,
      self.__partition_reference__ + '1')
    self.updateSurykatkaDict()
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
    self.assertEqual(
      set(
        glob.glob(
          os.path.join(self.bot_partition_path, 'etc', 'surykatka*.ini'))),
      set([q['ini-file'] for q in self.surykatka_dict.values()])
    )
    for info_dict in self.surykatka_dict.values():
      self.assertEqual(
        info_dict['expected_ini'].strip() % info_dict,
        open(info_dict['ini-file']).read().strip()
      )

  def assertPromiseContent(self, name, content):
    promise = open(
      os.path.join(
        self.bot_partition_path, 'etc', 'plugin', name
      )).read().strip()

    self.assertTrue(content in promise)

  def assertSurykatkaBotPromise(self):
    for info_dict in self.surykatka_dict.values():
      self.assertPromiseContent(
        info_dict['bot-promise'],
        "'report': 'bot_status'")
      self.assertPromiseContent(
        info_dict['bot-promise'],
        "'json-file': '%s'" % (info_dict['json-file'],)
      )

  def assertSurykatkaCron(self):
    for info_dict in self.surykatka_dict.values():
      self.assertEqual(
        '*/2 * * * * %s' % (info_dict['status-json'],),
        open(info_dict['status-cron']).read().strip()
      )

  def initiateSurykatkaRun(self):
    try:
      self.slap.waitForInstance(max_retry=2)
    except Exception:
      pass

  def assertSurykatkaStatusJSON(self):
    for info_dict in self.surykatka_dict.values():
      if os.path.exists(info_dict['json-file']):
        os.unlink(info_dict['json-file'])
      env = os.environ.copy()
      env.pop('PYTHONPATH', None)
      try:
        subprocess.check_call(info_dict['status-json'], shell=True, env=env)
      except subprocess.CalledProcessError as e:
        self.fail('%s failed with code %s and message %s' % (
          info_dict['status-json'], e.returncode, e.output))
      self.assertTrue(os.path.exists(info_dict['json-file']))
      with open(info_dict['json-file']) as fh:
        status_json = json.load(fh)
      self.assertIn('bot_status', status_json)

  def test(self):
    # Note: Those tests do not run surykatka and do not do real checks, as
    #       this depends too much on the environment and is really hard to
    #       mock
    #       So it is possible that some bugs might slip under the radar
    #       Nevertheless the surykatka and check_surykatka_json are heavily
    #       unit tested, and configuration created by the profiles is asserted
    #       here, so it shall be enough as reasonable status
    self.requestEdgetestSlaves()
    self.initiateSurykatkaRun()
    self.assertSurykatkaStatusJSON()
    self.assertSurykatkaIni()
    self.assertSurykatkaBotPromise()
    self.assertSurykatkaPromises()
    self.assertSurykatkaCron()


class TestEdge(EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.erp5.com/
  https://www.erp5.org/"""}
  }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'status-code': '300'")
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-300-promise.py',
      "'failure-amount': '2'"
    )

    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-300',
      {'url': 'https://www.erp5.org/', 'check-status-code': '300'},
    )


class TestEdgeNameserverCheckFrontendIp(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
NAMESERVER =
  127.0.1.1
  127.0.1.2

URL =
  https://www.erp5.com/"""}
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'nameserver': '127.0.1.1 127.0.1.2',
      'check-frontend-ip': '127.0.0.1 127.0.0.2',
    }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'ip-list': '127.0.0.1 127.0.0.2'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )


class TestEdgeCheckStatusCode(EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.erp5.com/
  https://www.erp5.org/"""}
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'check-status-code': '500',
    }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'status-code': '501'")
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-501-promise.py',
      "'failure-amount': '2'"
    )

    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'status-code': '500'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-501',
      {'url': 'https://www.erp5.org/', 'check-status-code': '501'},
    )


class TestEdgeCheckCertificateExpirationDays(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.erp5.com/
  https://www.erp5.org/"""}
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'check-certificate-expiration-days': '10',
    }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'certificate-expiration-days': '20'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'failure-amount': '2'"
    )

    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'certificate-expiration-days': '10'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-20',
      {'url': 'https://www.erp5.org/',
       'check-certificate-expiration-days': '20'},
    )


class TestEdgeCheckMaximumElapsedTime(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    5: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 7
SQLITE = %(db_file)s
URL =
  https://www.erp5.com/"""},
    20: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 22
SQLITE = %(db_file)s
URL =
  https://www.erp5.org/"""},
    1: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 3
SQLITE = %(db_file)s
URL =
  https://www.erp5.net/"""}
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'check-maximum-elapsed-time': '5',
    }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'maximum-elapsed-time': '20'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[20]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-20-promise.py',
      "'failure-amount': '2'"
    )

    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'maximum-elapsed-time': '5'")
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[5]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-default-promise.py',
      "'failure-amount': '2'"
    )

    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'ip-list': ''")
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'maximum-elapsed-time': '1'")
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'url': 'https://www.erp5.net/'")
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[1]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-1-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend-default',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-20',
      {'url': 'https://www.erp5.org/',
       'check-maximum-elapsed-time': '20'},
    )
    self.requestEdgetestSlave(
      'backend-1',
      {'url': 'https://www.erp5.net/',
       'check-maximum-elapsed-time': '1'},
    )


class TestEdgeFailureAmount(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.erp5.org/
  https://www.erp5.com/"""}
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'failure-amount': '5'
    }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-promise.py',
      "'failure-amount': '5'"
    )

    self.assertPromiseContent(
      'http-query-backend-10-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'http-query-backend-10-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'http-query-backend-10-promise.py',
      "'url': 'https://www.erp5.org/'")
    self.assertPromiseContent(
      'http-query-backend-10-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict[2]['json-file'],)
    )
    self.assertPromiseContent(
      'http-query-backend-10-promise.py',
      "'failure-amount': '10'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )
    self.requestEdgetestSlave(
      'backend-10',
      {'url': 'https://www.erp5.org/', 'failure-amount': '10'},
    )
