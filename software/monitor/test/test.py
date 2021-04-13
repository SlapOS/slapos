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

import copy
import glob
import json
import os
import re
import requests
import subprocess
import unittest
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


class MonitorTestMixin:
  monitor_setup_url_key = 'monitor-setup-url'

  def test_monitor_setup(self):
    connection_parameter_dict_serialised = self\
      .computer_partition.getConnectionParameterDict()
    connection_parameter_dict = json.loads(
      connection_parameter_dict_serialised['_'])
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
  expected_connection_parameter_dict = {}

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'edgetest'

  def requestEdgetestSlave(self, partition_reference, partition_parameter_kw):
    software_url = self.getSoftwareURL()
    return self.slap.request(
      software_release=software_url,
      software_type='edgetest',
      partition_reference=partition_reference,
      partition_parameter_kw={'_': json.dumps(partition_parameter_kw)},
      shared=True
    )

  def updateSurykatkaDict(self):
    for instance_reference in self.surykatka_dict:
      for class_ in self.surykatka_dict[instance_reference]:
        update_dict = {}
        update_dict['ini-file'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'etc',
          'surykatka-%s.ini' % (class_,))
        update_dict['json-file'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'srv',
          'surykatka-%s.json' % (class_,))
        update_dict['status-json'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'bin',
          'surykatka-status-json-%s' % (class_,))
        update_dict['bot-promise'] = 'surykatka-bot-promise-%s.py' % (class_,)
        update_dict['status-cron'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'etc',
          'cron.d', 'surykatka-status-%s' % (class_,))
        update_dict['db_file'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'srv',
          'surykatka-%s.db' % (class_,))
        self.surykatka_dict[instance_reference][class_].update(update_dict)

  def setUpMonitorConfigurationList(self):
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

  def setUp(self):
    self.updateSurykatkaDict()
    self.setUpMonitorConfigurationList()

  def assertSurykatkaIni(self):
    expected_init_path_list = []
    for instance_reference in self.surykatka_dict:
      expected_init_path_list.extend(
        [q['ini-file']
         for q in self.surykatka_dict[instance_reference].values()])
    self.assertEqual(
      set(
        glob.glob(
          os.path.join(
            self.slap.instance_directory, '*', 'etc', 'surykatka*.ini'
          )
        )
      ),
      set(expected_init_path_list)
    )
    for instance_reference in self.surykatka_dict:
      for info_dict in self.surykatka_dict[instance_reference].values():
        self.assertEqual(
          info_dict['expected_ini'].strip() % info_dict,
          open(info_dict['ini-file']).read().strip()
        )

  def assertPromiseContent(self, instance_reference, name, content):
    promise = open(
      os.path.join(
        self.slap.instance_directory, instance_reference, 'etc', 'plugin', name
      )).read().strip()

    self.assertTrue(content in promise)

  def assertSurykatkaBotPromise(self):
    for instance_reference in self.surykatka_dict:
      for info_dict in self.surykatka_dict[instance_reference].values():
        self.assertPromiseContent(
          instance_reference,
          info_dict['bot-promise'],
          "'report': 'bot_status'")
        self.assertPromiseContent(
          instance_reference,
          info_dict['bot-promise'],
          "'json-file': '%s'" % (info_dict['json-file'],),)

  def assertSurykatkaCron(self):
    for instance_reference in self.surykatka_dict:
      for info_dict in self.surykatka_dict[instance_reference].values():
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
    for instance_reference in self.surykatka_dict:
      for info_dict in self.surykatka_dict[instance_reference].values():
        if os.path.exists(info_dict['json-file']):
          os.unlink(info_dict['json-file'])
        try:
          subprocess.check_call(info_dict['status-json'])
        except subprocess.CalledProcessError as e:
          self.fail('%s failed with code %s and message %s' % (
            info_dict['status-json'], e.returncode, e.output))
        with open(info_dict['json-file']) as fh:
          status_json = json.load(fh)
        self.assertIn('bot_status', status_json)

  def assertConnectionParameterDict(self):
    serialised = self.requestDefaultInstance().getConnectionParameterDict()
    connection_parameter_dict = json.loads(serialised['_'])
    # tested elsewhere
    connection_parameter_dict.pop('monitor-setup-url', None)
    # comes from instance-monitor.cfg.jinja2, not needed here
    connection_parameter_dict.pop('server_log_url', None)
    self.assertEqual(
      self.expected_connection_parameter_dict,
      connection_parameter_dict
    )

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
    self.assertConnectionParameterDict()


class TestEdge(EdgeSlaveMixin, SlapOSInstanceTestCase):
  expected_connection_parameter_dict = {
    'active-region-list': ['1'],
    'sla-computer_guid': 'local', 'sla-instance_guid': 'local-edge0'}
  surykatka_dict = {
    'edge1': {
      1: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 3
SQLITE = %(db_file)s
URL =
  https://www.checkmaximumelapsedtime1.org/"""},
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.checkcertificateexpirationdays.org/
  https://www.checkfrontendiplist.org/
  https://www.checkhttpheaderdict.org/
  https://www.checkstatuscode.org/
  https://www.default.org/
  https://www.failureamount.org/"""},
      20: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 22
SQLITE = %(db_file)s
URL =
  https://www.checkmaximumelapsedtime20.org/"""},
    }
  }

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'edge1',
      'http-query-checkcertificateexpirationdays-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '20',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.checkcertificateexpirationdays.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-checkhttpheaderdict-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{"A": "AAA"}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.checkhttpheaderdict.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-checkmaximumelapsedtime1-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '1',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.checkmaximumelapsedtime1.org/'}""" % (
        self.surykatka_dict['edge1'][1]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-checkmaximumelapsedtime20-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '20',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.checkmaximumelapsedtime20.org/'}""" % (
        self.surykatka_dict['edge1'][20]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-checkstatuscode-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '300',
  'url': 'https://www.checkstatuscode.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-default-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.default.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-failureamount-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '10',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.failureamount.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-checkfrontendiplist-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '128.129.130.131 131.134.135.136',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.checkfrontendiplist.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'default',
      {'url': 'https://www.default.org/'},
    )
    self.requestEdgetestSlave(
      'checkstatuscode',
      {'url': 'https://www.checkstatuscode.org/', 'check-status-code': 300},
    )
    self.requestEdgetestSlave(
      'checkhttpheaderdict',
      {'url': 'https://www.checkhttpheaderdict.org/',
       'check-http-header-dict': {"A": "AAA"}},
    )
    self.requestEdgetestSlave(
      'checkcertificateexpirationdays',
      {'url': 'https://www.checkcertificateexpirationdays.org/',
       'check-certificate-expiration-days': '20'},
    )
    self.requestEdgetestSlave(
      'checkmaximumelapsedtime20',
      {'url': 'https://www.checkmaximumelapsedtime20.org/',
       'check-maximum-elapsed-time': 20},
    )
    self.requestEdgetestSlave(
      'checkmaximumelapsedtime1',
      {'url': 'https://www.checkmaximumelapsedtime1.org/',
       'check-maximum-elapsed-time': 1},
    )
    self.requestEdgetestSlave(
      'failureamount',
      {'url': 'https://www.failureamount.org/', 'failure-amount': '10'},
    )
    self.requestEdgetestSlave(
      'checkfrontendiplist',
      {'url': 'https://www.checkfrontendiplist.org/',
       'check-frontend-ip-list': ['128.129.130.131', '131.134.135.136']},
    )


class TestEdgeNameserverListCheckFrontendIpList(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  expected_connection_parameter_dict = {
    'active-region-list': ['1'], 'sla-computer_guid': 'local',
    'sla-instance_guid': 'local-edge0'}
  surykatka_dict = {
    'edge1': {
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
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'nameserver-list': ['127.0.1.1', '127.0.1.2'],
      'check-frontend-ip-list': ['127.0.0.1', '127.0.0.2'],
    })}

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'ip-list': '127.0.0.1 127.0.0.2'")
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'report': 'http_query'")
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'status-code': '200'")
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'certificate-expiration-days': '15'")
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'url': 'https://www.erp5.com/'")
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'json-file': '%s'" % (self.surykatka_dict['edge1'][2]['json-file'],)
    )
    self.assertPromiseContent(
      'edge1',
      'http-query-backend-promise.py',
      "'failure-amount': '2'"
    )

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'backend',
      {'url': 'https://www.erp5.com/'},
    )


class TestEdgeSlaveNotJson(
  EdgeSlaveMixin, SlapOSInstanceTestCase):
  surykatka_dict = {
    'edge1': {
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.erp5.com/"""}
    }
  }

  # non-json provided in slave '_' results with damaging the cluster
  # test here is to expose real problem, which has no solution for now
  @unittest.expectedFailure
  def test(self):
    EdgeSlaveMixin.test()

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'http-query-default-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.default.org/'}""" % (
        self.surykatka_dict[2]['json-file'],))

  def requestEdgetestSlaves(self):
    self.requestEdgetestSlave(
      'default',
      {'url': 'https://www.default.org/'},
    )
    software_url = self.getSoftwareURL()
    self.slap.request(
      software_release=software_url,
      software_type='edgetest',
      partition_reference='notajson',
      partition_parameter_kw={'_': 'notajson'},
      shared=True
    )


class TestEdgeRegion(EdgeSlaveMixin, SlapOSInstanceTestCase):
  expected_connection_parameter_dict = {
    'active-region-list': [
      'Region One', 'Region Three', 'Region Two'],
    'sla-computer_guid': 'local', 'sla-instance_guid': 'local-edge0'}
  surykatka_dict = {
    'edge1': {
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
NAMESERVER =
  127.0.1.1
  127.0.1.2

URL =
  https://www.all.org/
  https://www.globalcheck.org/
  https://www.onetwo.org/
  https://www.specificcheck.org/
  https://www.specificoverride.org/"""},
    },
    'edge2': {
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
URL =
  https://www.all.org/
  https://www.three.org/"""},
    },
    'edge3': {
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(db_file)s
NAMESERVER =
  127.0.2.1
  127.0.2.2

URL =
  https://www.all.org/
  https://www.onetwo.org/
  https://www.parialmiss.org/
  https://www.specificoverride.org/"""},
    }
  }

  def setUpMonitorConfigurationList(self):
    self.monitor_configuration_list = [
     {
       'htmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,),
       'text': 'testing partition 0',
       'title': 'testing partition 0',
       'type': 'rss',
       'url': 'https://[%s]:9700/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region One',
       'title': 'edgebot-Region One',
       'type': 'rss',
       'url': 'https://[%s]:9701/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9702/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Three',
       'title': 'edgebot-Region Three',
       'type': 'rss',
       'url': 'https://[%s]:9702/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9702/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Two',
       'title': 'edgebot-Region Two',
       'type': 'rss',
       'url': 'https://[%s]:9703/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,)
      }
    ]

  instance_parameter_dict = {
    'region-dict': {
      'Region One': {
        'sla-computer_guid': 'local',
        'state': 'started',
        'nameserver-list': ['127.0.1.1', '127.0.1.2'],
        'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
      },
      'Region Two': {
        'sla-computer_guid': 'local',
        'state': 'started',
        'nameserver-list': ['127.0.2.1', '127.0.2.2'],
      },
      'Region Three': {
        'sla-computer_guid': 'local',
        'state': 'started',
        'check-frontend-ip-list': ['127.0.3.1', '127.0.3.2'],
      }
    }
  }

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(cls.instance_parameter_dict)}

  slave_parameter_dict_dict = {
    'all': {
      'url': 'https://www.all.org/'
    },
    'onetwo': {
      'url': 'https://www.onetwo.org/',
      'region-dict': {'Region One': {}, 'Region Two': {}}
    },
    'three': {
      'url': 'https://www.three.org/',
      'region-dict': {'Region Three': {}}
    },
    'missed': {
      'url': 'https://www.missed.org/',
      'region-dict': {'Region Non Existing': {}}
    },
    'partialmiss': {
      'url': 'https://www.parialmiss.org/',
      'region-dict': {'Region Two': {}, 'Region Non Existing': {}}
    },
    'specificcheck': {
      'url': 'https://www.specificcheck.org/',
      'region-dict': {
        'Region One': {'check-frontend-ip-list': ['99.99.99.1', '99.99.99.2']}}
    },
    'globalcheck': {
      'url': 'https://www.globalcheck.org/',
      'check-frontend-ip-list': ['99.99.99.3', '99.99.99.4'],
      'region-dict': {'Region One': {}}
    },
    'specificoverride': {
      'url': 'https://www.specificoverride.org/',
      'check-frontend-ip-list': ['99.99.99.5', '99.99.99.6'],
      'region-dict': {
        'Region One': {'check-frontend-ip-list': ['99.99.99.7', '99.99.99.8']},
        'Region Two': {}}
    },
  }

  def requestEdgetestSlaves(self):
    for reference, parameter_dict in self.slave_parameter_dict_dict.items():
      self.requestEdgetestSlave(reference, parameter_dict)

  def assertSurykatkaPromises(self):
    self.assertPromiseContent(
      'edge1',
      'http-query-all-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '127.0.1.3 127.0.1.4',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.all.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-specificcheck-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '99.99.99.1 99.99.99.2',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.specificcheck.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-globalcheck-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '99.99.99.3 99.99.99.4',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.globalcheck.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-specificoverride-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '99.99.99.7 99.99.99.8',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.specificoverride.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge1',
      'http-query-onetwo-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '127.0.1.3 127.0.1.4',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.onetwo.org/'}""" % (
        self.surykatka_dict['edge1'][2]['json-file'],))

    self.assertPromiseContent(
      'edge2',
      'http-query-all-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '127.0.3.1 127.0.3.2',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.all.org/'}""" % (
        self.surykatka_dict['edge2'][2]['json-file'],))

    self.assertPromiseContent(
      'edge2',
      'http-query-three-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '127.0.3.1 127.0.3.2',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.three.org/'}""" % (
        self.surykatka_dict['edge2'][2]['json-file'],))

    self.assertPromiseContent(
      'edge3',
      'http-query-all-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.all.org/'}""" % (
        self.surykatka_dict['edge3'][2]['json-file'],))

    self.assertPromiseContent(
      'edge3',
      'http-query-onetwo-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.onetwo.org/'}""" % (
        self.surykatka_dict['edge3'][2]['json-file'],))

    self.assertPromiseContent(
      'edge3',
      'http-query-partialmiss-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.parialmiss.org/'}""" % (
        self.surykatka_dict['edge3'][2]['json-file'],))

    self.assertPromiseContent(
      'edge3',
      'http-query-specificoverride-promise.py',
      """extra_config_dict = { 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '99.99.99.5 99.99.99.6',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.specificoverride.org/'}""" % (
        self.surykatka_dict['edge3'][2]['json-file'],))

  def test(self):
    super(TestEdgeRegion, self).test()
    self.assertSlaveConnectionParameterDict()

  maxDiff = None

  expected_slave_connection_parameter_dict_dict = {
    'all': {
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two'],
      'assigned-region-dict': {
        'Region One': {
          'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
          'nameserver-list': ['127.0.1.1', '127.0.1.2']
        },
        'Region Three': {
          'check-frontend-ip-list': ['127.0.3.1', '127.0.3.2'],
          'nameserver-list': []
        },
        'Region Two': {
          'check-frontend-ip-list': [],
          'nameserver-list': ['127.0.2.1', '127.0.2.2']
        }
      }
    },
    'onetwo': {
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two'],
      'assigned-region-dict': {
        'Region One': {
          'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
          'nameserver-list': ['127.0.1.1', '127.0.1.2']
        },
        'Region Two': {
          'check-frontend-ip-list': [],
          'nameserver-list': ['127.0.2.1', '127.0.2.2']
        }
      }
    },
    'specificcheck': {
      'assigned-region-dict': {
        'Region One': {
          'check-frontend-ip-list': ['99.99.99.1', '99.99.99.2'],
          'nameserver-list': ['127.0.1.1', '127.0.1.2']
        }
      },
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two']
    },
    'specificoverride': {
      'assigned-region-dict': {
        'Region One': {
          'check-frontend-ip-list': ['99.99.99.7', '99.99.99.8'],
          'nameserver-list': ['127.0.1.1', '127.0.1.2']
        },
        'Region Two': {
          'check-frontend-ip-list': ['99.99.99.5', '99.99.99.6'],
          'nameserver-list': ['127.0.2.1', '127.0.2.2']
        }
      },
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two']
    },
    'three': {
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two'],
      'assigned-region-dict': {
        'Region Three': {
          'check-frontend-ip-list': ['127.0.3.1', '127.0.3.2'],
          'nameserver-list': []
        }
      }
    },
    'globalcheck': {
      'assigned-region-dict': {
        'Region One': {
          'check-frontend-ip-list': ['99.99.99.3', '99.99.99.4'],
          'nameserver-list': ['127.0.1.1', '127.0.1.2']
        }
      },
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two']
    },
    'missed': {
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two'],
      'assigned-region-dict': {
      }
    },
    'partialmiss': {
      'available-region-list': [
        'Region One', 'Region Three', 'Region Two'],
      'assigned-region-dict': {
        'Region Two': {
          'check-frontend-ip-list': [],
          'nameserver-list': ['127.0.2.1', '127.0.2.2']
        }
      }
    }
  }

  def assertSlaveConnectionParameterDict(self):
    slave_connection_parameter_dict_dict = {}
    for reference, parameter_dict in self.slave_parameter_dict_dict.items():
      slave_connection_parameter_dict_dict[
        reference] = self.requestEdgetestSlave(
          reference, parameter_dict).getConnectionParameterDict()
      # unload the json
      slave_connection_parameter_dict_dict[
        reference] = json.loads(
        slave_connection_parameter_dict_dict[reference].pop('_'))
    self.assertEqual(
      self.expected_slave_connection_parameter_dict_dict,
      slave_connection_parameter_dict_dict
    )


class TestEdgeRegionDestroyed(TestEdgeRegion):
  def setUpMonitorConfigurationList(self):
    # already for destroyed case, as test_monitor_setup will be called after
    # test
    self.monitor_configuration_list = [
     {
       'htmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,),
       'text': 'testing partition 0',
       'title': 'testing partition 0',
       'type': 'rss',
       'url': 'https://[%s]:9700/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region One',
       'title': 'edgebot-Region One',
       'type': 'rss',
       'url': 'https://[%s]:9701/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Two',
       'title': 'edgebot-Region Two',
       'type': 'rss',
       'url': 'https://[%s]:9703/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,)
      }
    ]

  def _test(self):
    self.__class__._instance_parameter_dict = self.getInstanceParameterDict()
    self.requestDefaultInstance()
    # give time to stabilise the tree
    self.slap.waitForInstance(max_retry=4)

    self.assertConnectionParameterDict()

    self.expected_slave_connection_parameter_dict_dict = {
      'all': {
        'available-region-list': [
          'Region One', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      },
      'onetwo': {
        'available-region-list': [
          'Region One', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      },
      'specificcheck': {
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.1', '99.99.99.2'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          }
        },
        'available-region-list': [
          'Region One', 'Region Two']
      },
      'specificoverride': {
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.7', '99.99.99.8'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Two': {
            'check-frontend-ip-list': ['99.99.99.5', '99.99.99.6'],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        },
        'available-region-list': [
          'Region One', 'Region Two']
      },
      'three': {
        'assigned-region-dict': {},
        'available-region-list': [
          'Region One', 'Region Two'],
      },
      'globalcheck': {
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.3', '99.99.99.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          }
        },
        'available-region-list': [
          'Region One', 'Region Two']
      },
      'missed': {
        'available-region-list': [
          'Region One', 'Region Two'],
        'assigned-region-dict': {
        }
      },
      'partialmiss': {
        'available-region-list': [
          'Region One', 'Region Two'],
        'assigned-region-dict': {
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      }
    }
    self.assertSlaveConnectionParameterDict()

  def test(self):
    super(TestEdgeRegionDestroyed, self).test()
    # hack around @classmethod
    original_instance_parameter_dict = copy.deepcopy(
      self.__class__.instance_parameter_dict)
    original_expected_connection_parameter_dict = copy.deepcopy(
      self.__class__.expected_connection_parameter_dict)
    self.__class__.instance_parameter_dict[
      'region-dict']['Region Three']['state'] = 'destroyed'
    # Region was removed
    self.__class__.expected_connection_parameter_dict[
      'active-region-list'].remove('Region Three')
    try:
      self._test()
    finally:
      self.__class__.instance_parameter_dict = \
        original_instance_parameter_dict
      self.__class__.expected_connection_parameter_dict = \
          original_expected_connection_parameter_dict


class TestEdgeRegionAdded(TestEdgeRegion):
  def setUpMonitorConfigurationList(self):
    # already for added case, as test_monitor_setup will be called after test
    self.monitor_configuration_list = [
     {
       'htmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,),
       'text': 'testing partition 0',
       'title': 'testing partition 0',
       'type': 'rss',
       'url': 'https://[%s]:9700/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9700/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Four',
       'title': 'edgebot-Region Four',
       'type': 'rss',
       'url': 'https://[%s]:9701/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9701/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9702/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region One',
       'title': 'edgebot-Region One',
       'type': 'rss',
       'url': 'https://[%s]:9702/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9702/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Three',
       'title': 'edgebot-Region Three',
       'type': 'rss',
       'url': 'https://[%s]:9703/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9703/public/feed' % (self._ipv6_address,)
     },
     {
       'htmlUrl': 'https://[%s]:9704/public/feed' % (self._ipv6_address,),
       'text': 'edgebot-Region Two',
       'title': 'edgebot-Region Two',
       'type': 'rss',
       'url': 'https://[%s]:9704/share/private/' % (self._ipv6_address,),
       'version': 'RSS',
       'xmlUrl': 'https://[%s]:9704/public/feed' % (self._ipv6_address,)
      }
    ]

  def _test(self):
    self.__class__._instance_parameter_dict = self.getInstanceParameterDict()
    self.requestDefaultInstance()
    # give time to stabilise the tree, 6 times as new node is added
    self.slap.waitForInstance(max_retry=6)
    # XXX: few more times, but ignoring good result from promises, as there is
    #      "Unknown Instance" of just added node which is not caught by any
    #      promise, but in the end it shall get better
    for f in range(5):
      try:
        self.slap.waitForInstance()
      except Exception:
        pass
    self.slap.waitForInstance()

    self.assertConnectionParameterDict()

    self.expected_slave_connection_parameter_dict_dict = {
      'all': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region Four': {
            'check-frontend-ip-list': ['127.0.4.3', '127.0.4.4'],
            'nameserver-list': ['127.0.4.1', '127.0.4.2']
          },
          'Region One': {
            'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Three': {
            'check-frontend-ip-list': ['127.0.3.1', '127.0.3.2'],
            'nameserver-list': []
          },
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      },
      'onetwo': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['127.0.1.3', '127.0.1.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      },
      'specificcheck': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.1', '99.99.99.2'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          }
        },
      },
      'specificoverride': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.7', '99.99.99.8'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          },
          'Region Two': {
            'check-frontend-ip-list': ['99.99.99.5', '99.99.99.6'],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        },
      },
      'three': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region Three': {
            'check-frontend-ip-list': ['127.0.3.1', '127.0.3.2'],
            'nameserver-list': []
          }
        }
      },
      'globalcheck': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region One': {
            'check-frontend-ip-list': ['99.99.99.3', '99.99.99.4'],
            'nameserver-list': ['127.0.1.1', '127.0.1.2']
          }
        },
      },
      'missed': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
        }
      },
      'partialmiss': {
        'available-region-list': [
          'Region Four', 'Region One', 'Region Three', 'Region Two'],
        'assigned-region-dict': {
          'Region Two': {
            'check-frontend-ip-list': [],
            'nameserver-list': ['127.0.2.1', '127.0.2.2']
          }
        }
      }
    }
    self.assertSlaveConnectionParameterDict()
    self.surykatka_dict['edge4'] = {
      2: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 4
SQLITE = %(dbfile)
NAMESERVER =
  127.0.4.1
  127.0.4.2

URL =
  https://www.all.org/"""},
    }
    self.updateSurykatkaDict()

    self.assertPromiseContent(
      'edge4',
      'http-query-all-promise.py',
      """{ 'certificate-expiration-days': '15',
  'failure-amount': '2',
  'http-header-dict': '{}',
  'ip-list': '127.0.4.3 127.0.4.4',
  'json-file': '%s',
  'maximum-elapsed-time': '2',
  'report': 'http_query',
  'status-code': '200',
  'url': 'https://www.all.org/'}""" % (
        self.surykatka_dict['edge4'][2]['json-file'],))

  def test(self):
    super(TestEdgeRegionAdded, self).test()
    # hack around @classmethod
    original_instance_parameter_dict = copy.deepcopy(
      self.__class__.instance_parameter_dict)
    original_expected_connection_parameter_dict = copy.deepcopy(
      self.__class__.expected_connection_parameter_dict)
    self.__class__.instance_parameter_dict['region-dict']['Region Four'] = {
      'sla-computer_guid': 'local',
      'state': 'started',
      'nameserver-list': ['127.0.4.1', '127.0.4.2'],
      'check-frontend-ip-list': ['127.0.4.3', '127.0.4.4'],
    }
    # Region was added
    self.__class__.expected_connection_parameter_dict[
      'active-region-list'].insert(0, 'Region Four')
    try:
      self._test()
    finally:
      self.__class__.instance_parameter_dict = \
        original_instance_parameter_dict
      self.__class__.expected_connection_parameter_dict = \
          original_expected_connection_parameter_dict
