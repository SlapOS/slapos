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
import hashlib
import json
import os
import subprocess
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class EdgeMixin(object):
  __partition_reference__ = 'edge'
  instance_max_retry = 20
  expected_connection_parameter_dict = {}

  def setUp(self):
    self.updateSurykatkaDict()

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
        with open(info_dict['ini-file']) as fh:
          self.assertEqual(
            info_dict['expected_ini'].strip() % info_dict,
            fh.read().strip()
          )

  def assertPromiseContent(self, instance_reference, name, content):
    with open(
      os.path.join(
        self.slap.instance_directory, instance_reference, 'etc', 'plugin', name
      )) as fh:
      promise = fh.read().strip()
    self.assertIn(content, promise)

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
        with open(info_dict['status-cron']) as fh:
          self.assertEqual(
            '*/2 * * * * %s' % (info_dict['status-json'],),
            fh.read().strip()
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


class TestEdgeBasic(EdgeMixin, SlapOSInstanceTestCase):
  surykatka_dict = {}

  def assertConnectionParameterDict(self):
    connection_parameter_dict = self.requestDefaultInstance(
      ).getConnectionParameterDict()
    # tested elsewhere
    connection_parameter_dict.pop('monitor-setup-url', None)
    # comes from instance-monitor.cfg.jinja2, not needed here
    connection_parameter_dict.pop('server_log_url', None)
    self.assertEqual(
      self.expected_connection_parameter_dict,
      connection_parameter_dict
    )

  def assertHttpQueryPromiseContent(
    self, instance_reference, name, url, content):
    hashed = 'http-query-%s-%s.py' % (
      hashlib.md5((name).encode('utf-8')).hexdigest(),
      hashlib.md5((url).encode('utf-8')).hexdigest(),
    )
    self.assertPromiseContent(instance_reference, hashed, content)

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
        update_dict['bot-promise'] = 'surykatka-bot-%s.py' % (class_,)
        update_dict['status-cron'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'etc',
          'cron.d', 'surykatka-status-%s' % (class_,))
        update_dict['db_file'] = os.path.join(
          self.slap.instance_directory, instance_reference, 'srv',
          'surykatka-%s.db' % (class_,))
        self.surykatka_dict[instance_reference][class_].update(update_dict)

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'nameserver-list': ['127.0.1.1', '127.0.1.2'],
      'check-frontend-ip-list': ['127.0.0.1', '127.0.0.2'],
      "check-maximum-elapsed-time": 5,
      "check-certificate-expiration-days": 7,
      "check-status-code": 201,
      "failure-amount": 1,
      "check-dict": {
        "path-check": {
           "url-list": [
             "https://path.example.com/path",
           ]
        },
        "domain-check": {
           "url-list": [
             "domain.example.com",
           ]
        },
        "frontend-check": {
           "url-list": [
             "https://frontend.example.com",
           ],
           "check-frontend-ip-list": ['127.0.0.3'],
        },
        "frontend-empty-check": {
           "url-list": [
             "https://frontendempty.example.com",
           ],
           "check-frontend-ip-list": [],
        },
        "status-check": {
           "url-list": [
             "https://status.example.com",
           ],
           "check-status-code": 202,
        },
        "certificate-check": {
           "url-list": [
             "https://certificate.example.com",
           ],
           "check-certificate-expiration-days": 11,
        },
        "time-check": {
           "url-list": [
             "https://time.example.com",
           ],
           "check-maximum-elapsed-time": 11,
        },
        "failure-check": {
           "url-list": [
             "https://failure.example.com",
           ],
           "failure-amount": 3,
        },
        "header-check": {
           "url-list": [
             "https://header.example.com",
           ],
           'check-http-header-dict': {"A": "AAA"},
        },
        "whois-check": {
           "url-list": [
             "https://whois.example.com",
           ],
           "check-domain-expiration-days": 16,
        },
      }
    })}

  surykatka_dict = {
    'edge0': {
      5: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 7
SQLITE = %(db_file)s
ELAPSED_FAST = 5
NAMESERVER =
  127.0.1.1
  127.0.1.2

URL =
  http://domain.example.com
  https://certificate.example.com
  https://domain.example.com
  https://failure.example.com
  https://frontend.example.com
  https://frontendempty.example.com
  https://header.example.com
  https://path.example.com/path
  https://status.example.com
  https://whois.example.com
"""},
      11: {'expected_ini': """[SURYKATKA]
INTERVAL = 120
TIMEOUT = 13
SQLITE = %(db_file)s
ELAPSED_FAST = 11
NAMESERVER =
  127.0.1.1
  127.0.1.2

URL =
  https://time.example.com
"""},
    }
  }

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'edgetest-basic'

  enabled_sense_list = \
      "'dns_query whois tcp_server http_query ssl_certificate '\n"\
      "                        'elapsed_time'"

  def assertSurykatkaPromises(self):
    self.assertHttpQueryPromiseContent(
      'edge0',
      'path-check',
      'https://path.example.com/path',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://path.example.com/path'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'domain-check',
      'https://domain.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://domain.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'domain-check',
      'http://domain.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'http://domain.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'frontend-check',
      'https://frontend.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.3',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://frontend.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'frontend-empty-check',
      'https://frontendempty.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://frontendempty.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'status-check',
      'https://status.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '202',
  'url': 'https://status.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'certificate-check',
      'https://certificate.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '11',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://certificate.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'time-check',
      'https://time.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '11',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://time.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][11]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'failure-check',
      'https://failure.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '3',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://failure.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'header-check',
      'https://header.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '30',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{"A": "AAA"}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://header.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

    self.assertHttpQueryPromiseContent(
      'edge0',
      'whois-check',
      'https://whois.example.com',
      """extra_config_dict = { 'certificate-expiration-days': '7',
  'domain-expiration-days': '16',
  'enabled-sense-list': %s,
  'failure-amount': '1',
  'http-header-dict': '{}',
  'ip-list': '127.0.0.1 127.0.0.2',
  'json-file': '%s',
  'maximum-elapsed-time': '5',
  'report': 'http_query',
  'status-code': '201',
  'url': 'https://whois.example.com'}""" % (
        self.enabled_sense_list,
        self.surykatka_dict['edge0'][5]['json-file'],))

  def test(self):
    # Note: Those tests do not run surykatka and do not do real checks, as
    #       this depends too much on the environment and is really hard to
    #       mock
    #       So it is possible that some bugs might slip under the radar
    #       Nevertheless the surykatka and check_surykatka_json are heavily
    #       unit tested, and configuration created by the profiles is asserted
    #       here, so it shall be enough as reasonable status
    self.initiateSurykatkaRun()
    self.assertSurykatkaStatusJSON()
    self.assertSurykatkaIni()
    self.assertSurykatkaBotPromise()
    self.assertSurykatkaPromises()
    self.assertSurykatkaCron()
    self.assertConnectionParameterDict()


class TestEdgeBasicEnableSenseList(TestEdgeBasic):
  enabled_sense_list = "'ssl_certificate'"

  @classmethod
  def getInstanceParameterDict(cls):
    orig_instance_parameter_dict = super().getInstanceParameterDict()
    _ = json.loads(orig_instance_parameter_dict['_'])
    _['enabled-sense-list'] = 'ssl_certificate'
    return {'_': json.dumps(_)}
