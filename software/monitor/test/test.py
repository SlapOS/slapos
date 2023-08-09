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

import datetime
import glob
import hashlib
import json
import os
import psutil
import re
import requests
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.util import bytes2str

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

  def test_monitor_httpd_normal_reboot(self):
    # Start the monitor-httpd service
    monitor_httpd_process_name = ''
    with self.slap.instance_supervisor_rpc as supervisor:
      info, = [i for i in
         supervisor.getAllProcessInfo() if ('monitor-httpd' in i['name']) and ('on-watch' in i['name'])]
      partition = info['group']
      if info['statename'] != "RUNNING":
        monitor_httpd_process_name = f"{info['group']}:{info['name']}"
        supervisor.startProcess(monitor_httpd_process_name)
        for _retries in range(20):
          time.sleep(1)
          info, = [i for i in 
           supervisor.getAllProcessInfo() if ('monitor-httpd' in i['name']) and ('on-watch' in i['name'])]
          if info['statename'] == "RUNNING":
            break
        else:
          self.fail(f"the supervisord service '{monitor_httpd_process_name}' is not running")

    # Get the partition path
    partition_path_list = glob.glob(os.path.join(self.slap.instance_directory, '*'))
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc', 'monitor-httpd.conf')):
        self.partition_path = partition_path
        break

    # Make sure we are focusing the same httpd service
    self.assertIn(partition, self.partition_path)

    # Get the monitor-httpd-service
    monitor_httpd_service_path = glob.glob(os.path.join(
      self.partition_path, 'etc', 'service', 'monitor-httpd*'
    ))[0]

    try:
      output = subprocess.check_output([monitor_httpd_service_path], timeout=10, stderr=subprocess.STDOUT, text=True)
      # If the httpd-monitor service is running
      # and the monitor-httpd.pid contains the identical PID as the servicse
      # run the monitor-httpd service can cause the "already running" error correctly
      self.assertIn("already running", output)
    except subprocess.CalledProcessError as e:
      self.logger.debug(e.output)
      self.logger.debug("Unexpected error when running the monitor-httpd service:", e)
      self.fail("Unexpected error when running the monitor-httpd service")
    except subprocess.TimeoutExpired as e:
      # Timeout means we run the httpd service corrrectly
      # This is not the expected behaviour
      self.logger.debug("Unexpected behaviour: We are not suppose to be able to run the httpd service in the test:", e)
      # Kill the process that we started manually
      # Get the pid of the monitor_httpd from the PID file
      monitor_httpd_pid_file = os.path.join(self.partition_path, 'var', 'run', 'monitor-httpd.pid')
      monitor_httpd_pid = ""
      if os.path.exists(monitor_httpd_pid_file):
        with open(monitor_httpd_pid_file, "r") as pid_file:
          monitor_httpd_pid = pid_file.read()
      try:
        pid_to_kill = monitor_httpd_pid.strip('\n')
        subprocess.run(["kill", "-9", str(pid_to_kill)], check=True)
        self.logger.debug(f"Process with PID {pid_to_kill} killed.")
      except subprocess.CalledProcessError as e:
        self.logger.debug(f"Error killing process with PID {pid_to_kill}: {e}")
      self.fail("Unexpected behaviour: We are not suppose to be able to run the httpd service in the test")

    with self.slap.instance_supervisor_rpc as supervisor:
      info, = [i for i in
         supervisor.getAllProcessInfo() if ('monitor-httpd' in i['name']) and ('on-watch' in i['name'])]
      partition = info['group']
      if info['statename'] == "RUNNING":
        monitor_httpd_process_name = f"{info['group']}:{info['name']}"
        supervisor.stopProcess(monitor_httpd_process_name)

  def test_monitor_httpd_crash_reboot(self):
    # Get the partition path
    partition_path_list = glob.glob(os.path.join(self.slap.instance_directory, '*'))
    for partition_path in partition_path_list:
      if os.path.exists(os.path.join(partition_path, 'etc', 'monitor-httpd.conf')):
        self.partition_path = partition_path
        break

    # Get the pid file
    monitor_httpd_pid_file = os.path.join(self.partition_path, 'var', 'run', 'monitor-httpd.pid')
    monitor_httpd_process_name = ''
    with self.slap.instance_supervisor_rpc as supervisor:
      info, = [i for i in
         supervisor.getAllProcessInfo() if ('monitor-httpd' in i['name']) and ('on-watch' in i['name'])]
      if info['statename'] == "RUNNING":
        monitor_httpd_process_name = f"{info['group']}:{info['name']}"
        supervisor.stopProcess(monitor_httpd_process_name)

    # Write the PID of the infinite process to the pid file.
    with open(monitor_httpd_pid_file, "w") as file:
      file.write(str(os.getpid()))

    # Get the monitor-httpd-service
    monitor_httpd_service_path = glob.glob(os.path.join(
      self.partition_path, 'etc', 'service', 'monitor-httpd*'
    ))[0]
    output = ''

    monitor_httpd_service_is_running = False

    # Create the subprocess
    self.logger.debug("Ready to run the process in crash reboot")
    try:
      process = subprocess.Popen(monitor_httpd_service_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      stdout, stderr = '', ''
      try:
        # Wait for the process to finish, but with a timeout
        stdout, stderr = process.communicate(timeout=3)
        self.logger.debug("Communicated!")
      except subprocess.TimeoutExpired:
        monitor_httpd_service_is_running = True # We didn't get any output within 3 seconds, this means everything is fine.
        # If the process times out, terminate it
        try:
          main_process = psutil.Process(process.pid)
          child_processes = main_process.children(recursive=True)

          for process in child_processes + [main_process]:
            process.terminate()

          psutil.wait_procs(child_processes + [main_process])

          self.logger.debug(f"Processes with PID {process.pid} and its subprocesses terminated.")
        except psutil.NoSuchProcess as e:
          # This print will generate ResourceWarningm but it is normal in Python 3
          # See https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_process.py#L1526
          self.logger.debug("No process found with PID: %s" % process.pid)
    except subprocess.CalledProcessError as e:
      self.logger.debug(e.output)
      self.logger.debug("Unexpected error when running the monitor-httpd service:", e)
      self.fail("Unexpected error when running the monitor-httpd service")

    # "httpd (pid 21934) already running" means we start httpd failed
    if "already running" in stdout:
      self.fail("Unexepected output from the monitor-httpd process: %s" % stdout)
      raise Exception("Unexepected output from the monitor-httpd process: %s" % stdout)

    self.assertTrue(monitor_httpd_service_is_running)


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

  enabled_sense_list = "'dns_query tcp_server http_query ssl_certificate '\n"\
                       "                        'elapsed_time'"

  def assertSurykatkaPromises(self):
    self.assertHttpQueryPromiseContent(
      'edge0',
      'path-check',
      'https://path.example.com/path',
      """extra_config_dict = { 'certificate-expiration-days': '7',
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


class TestNodeMonitoring(SlapOSInstanceTestCase):
  """Test class for node monitoring instanciation"""
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'promise_cpu_temperature_frequency': 2,
      'promise_cpu_temperature_threshold': 90,
      'promise_cpu_avg_temperature_threshold': 80,
      'promise_cpu_avg_temperature_threshold_duration': 600,
      'promise_ram_available_frequency': 2,
      'promise_ram_available_threshold': 500,
      'promise_ram_avg_available_threshold': 1e3,
      'promise_ram_avg_available_threshold_duration': 600,
      'promise_network_errors_frequency': 5,
      'promise_network_errors_threshold': 100,
      'promise_network_lost_packets_threshold': 100,
      'promise_network_transit_frequency': 1,
      'promise_network_transit_max_data_threshold': 1e6,
      'promise_network_transit_min_data_threshold': 0,
      'promise_network_transit_duration': 600,
      'promise_cpu_load_threshold': 1.5,
      'promise_monitor_space_frequency': 5,
      'promise_partition_space_threshold': 0.08,
      'promise_free_disk_space_frequency': 3,
      'promise_free_disk_space_threshold': 0.08,
      'promise_free_disk_space_nb_days_predicted': 10,
      'promise_free_disk_space_display_partition': True,
      'promise_free_disk_space_display_prediction': True,
    })}

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  def test_node_monitoring_instance(self):
    pass


class TestNodeMonitoringRe6stCertificate(SlapOSInstanceTestCase):
  @classmethod
  def getInstanceSoftwareType(cls):
    return 'default'

  def reRequestInstance(self, partition_parameter_kw=None, state='started'):
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    software_url = self.getSoftwareURL()
    software_type = self.getInstanceSoftwareType()
    return self.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference=self.default_partition_reference,
        partition_parameter_kw=partition_parameter_kw,
        state=state)

  def test_default(self):
    self.reRequestInstance()
    self.slap.waitForInstance()
    promise = os.path.join(
      self.computer_partition_root_path, 'etc', 'plugin',
      'check-re6stnet-certificate.py')
    self.assertTrue(os.path.exists(promise))
    with open(promise) as fh:
      promise_content = fh.read()
    # this test depends on OS level configuration
    if os.path.exists('/etc/re6stnet/cert.crt'):
      self.assertIn(
        "extra_config_dict = {'certificate': '/etc/re6stnet/cert.crt', "
        "'certificate-expiration-days': '15'}", promise_content)
      self.assertIn(
        "from slapos.promise.plugin.check_certificate import RunPromise",
        promise_content)
    else:
      self.assertIn(
        "extra_config_dict = {'command': 'echo \"re6stnet disabled on the "
        "node\"'}", promise_content)
      self.assertIn(
        "from slapos.promise.plugin.check_command_execute import RunPromise",
        promise_content)

  def createKey(self):
    key = rsa.generate_private_key(
      public_exponent=65537, key_size=2048, backend=default_backend())
    key_pem = key.private_bytes(
      encoding=serialization.Encoding.PEM,
      format=serialization.PrivateFormat.TraditionalOpenSSL,
      encryption_algorithm=serialization.NoEncryption()
    )
    return key, key_pem

  def createCertificate(self, key, days=30):
    subject = issuer = x509.Name([
      x509.NameAttribute(NameOID.COUNTRY_NAME, u"FR"),
      x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Nord"),
      x509.NameAttribute(NameOID.LOCALITY_NAME, u"Lille"),
      x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Nexedi"),
      x509.NameAttribute(NameOID.COMMON_NAME, u"Common"),
    ])
    certificate = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days)
    ).sign(key, hashes.SHA256(), default_backend())
    certificate_pem = certificate.public_bytes(
      encoding=serialization.Encoding.PEM)
    return certificate, certificate_pem

  def createKeyCertificate(self, certificate_path):
    key, key_pem = self.createKey()
    certificate, certificate_pem = self.createCertificate(key, 30)
    with open(certificate_path, 'w') as fh:
      fh.write(bytes2str(key_pem))
    with open(certificate_path, 'a') as fh:
      fh.write(bytes2str(certificate_pem))

  def setUp(self):
    super().setUp()
    self.re6st_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.re6st_dir)

  def test_re6st_dir(self, days=None, filename='cert.crt'):
    self.createKeyCertificate(os.path.join(self.re6st_dir, filename))
    with open(os.path.join(self.re6st_dir, 're6stnet.conf'), 'w') as fh:
      fh.write("")
    partition_parameter_kw = {
      'promise_re6stnet_config_directory': self.re6st_dir
    }
    if filename != 'cert.crt':
      partition_parameter_kw['promise_re6stnet_certificate_file'] = filename
    if days is not None:
      partition_parameter_kw['re6stnet_certificate_expiration_delay'] = days
    self.reRequestInstance(
      partition_parameter_kw={'_': json.dumps(partition_parameter_kw)})
    self.slap.waitForInstance()
    promise = os.path.join(
      self.computer_partition_root_path, 'etc', 'plugin',
      'check-re6stnet-certificate.py')
    self.assertTrue(os.path.exists(promise))
    with open(promise) as fh:
      promise_content = fh.read()
    self.assertIn(
      """extra_config_dict = { 'certificate': '%(re6st_dir)s/%(filename)s',
  'certificate-expiration-days': '%(days)s'}""" % {
       're6st_dir': self.re6st_dir,
       'days': days or 15,
       'filename': filename},
      promise_content)
    self.assertIn(
      "from slapos.promise.plugin.check_certificate import RunPromise",
      promise_content)

  def test_re6st_dir_expiration(self):
    self.test_re6st_dir(days=10)

  def test_re6st_dir_filename(self):
    self.test_re6st_dir(filename="cert.pem")
