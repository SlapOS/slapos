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

      # "httpd (pid 21934) already running" means we start httpd failed
      if "already running" in stdout:
        self.fail("Unexepected output from the monitor-httpd process: %s" % stdout)
        raise Exception("Unexepected output from the monitor-httpd process: %s" % stdout)

    except subprocess.CalledProcessError as e:
      self.logger.debug("Unexpected error when running the monitor-httpd service:", e)
      self.fail("Unexpected error when running the monitor-httpd service")

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
