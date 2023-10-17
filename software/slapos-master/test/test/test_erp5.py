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
import json
import glob
import urllib.parse
import socket
import time
import re
import http.server
import multiprocessing
import subprocess
import unittest

import psutil
import requests

from . import ERP5InstanceTestCase
from . import setUpModule
setUpModule # pyflakes


class TestPublishedURLIsReachableMixin:
  """Mixin that checks that default page of ERP5 is reachable.
  """

  def _checkERP5IsReachable(self, base_url, site_id, verify):
    # We access ERP5 trough a "virtual host", which should make
    # ERP5 produce URLs using https://virtual-host-name:1234/virtual_host_root
    # as base.
    virtual_host_url = urllib.parse.urljoin(
        base_url,
        '/VirtualHostBase/https/virtual-host-name:1234/{}/VirtualHostRoot/_vh_virtual_host_root/'
        .format(site_id))

    # What happens is that instantiation just create the services, but does not
    # wait for ERP5 to be initialized. When this test run ERP5 instance is
    # instantiated, but zope is still busy creating the site and haproxy replies
    # with 503 Service Unavailable when zope is not started yet, with 404 when
    # erp5 site is not created, with 500 when mysql is not yet reachable, so we
    # configure this requests session to retry.
    # XXX we should probably add a promise instead
    session = requests.Session()
    session.mount(
        base_url,
        requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.retry.Retry(
                total=60,
                backoff_factor=.5,
                status_forcelist=(404, 500, 503))))
    with session:
      r = session.get(virtual_host_url, verify=verify, allow_redirects=False)
      self.assertEqual(r.status_code, requests.codes.found)
      # access on / are redirected to login form, with virtual host preserved
      self.assertEqual(r.headers.get('location'), 'https://virtual-host-name:1234/virtual_host_root/login_form')

      # login page can be rendered and contain the text "ERP5"
      r = session.get(
          urllib.parse.urljoin(base_url, f'{site_id}/login_form'),
          verify=verify,
          allow_redirects=False,
      )
      self.assertEqual(r.status_code, requests.codes.ok)
      self.assertIn("ERP5", r.text)

  def test_published_family_default_v6_is_reachable(self):
    """Tests the IPv6 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      param_dict['family-default-v6'],
      param_dict['site-id'],
      verify=False)

  def test_published_family_default_v4_is_reachable(self):
    """Tests the IPv4 URL published by the root partition is reachable.
    """
    param_dict = self.getRootPartitionConnectionParameterDict()
    self._checkERP5IsReachable(
      param_dict['family-default'],
      param_dict['site-id'],
      verify=False)

class TestDefaultParameters(
  ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 can be instantiated with no parameters
  """
  __partition_reference__ = 'defp'


class TestJupyter(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test ERP5 Jupyter notebook
  """
  __partition_reference__ = 'jupyter'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({'jupyter': {'enable': True}})}

  def test_jupyter_notebook_is_reachable(self):
    param_dict = self.getRootPartitionConnectionParameterDict()

    self.assertEqual(
      f'https://[{self.getPartitionIPv6(self.getPartitionId("jupyter"))}]:8888/tree',
      param_dict['jupyter-url']
    )

    result = requests.get(
      param_dict['jupyter-url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [requests.codes.found, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )


class TestApacheBalancerPorts(ERP5InstanceTestCase):
  """Instantiate with two zope families, this should create for each family:
   - a balancer entry point with corresponding haproxy
   - a balancer entry point for test runner
  """
  __partition_reference__ = 'ap'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
            json.dumps({
                "zope-partition-dict": {
                    "family1": {
                        "instance-count": 3,
                        "family": "family1"
                    },
                    "family2": {
                        "instance-count": 5,
                        "family": "family2"
                    },
                },
            })
    }

  def checkValidHTTPSURL(self, url):
    parsed = urllib.parse.urlparse(url)
    self.assertEqual(parsed.scheme, 'https')
    self.assertTrue(parsed.hostname)
    self.assertTrue(parsed.port)

  def test_published_family_parameters(self):
    # when we request two families, we have two published family-{family_name} URLs
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      self.checkValidHTTPSURL(
          param_dict[f'family-{family_name}'])
      self.checkValidHTTPSURL(
          param_dict[f'family-{family_name}-v6'])

  def test_published_test_runner_url(self):
    # each family's also a list of test test runner URLs, by default 3 per family
    param_dict = self.getRootPartitionConnectionParameterDict()
    for family_name in ('family1', 'family2'):
      family_test_runner_url_list = param_dict[
          f'{family_name}-test-runner-url-list']
      self.assertEqual(3, len(family_test_runner_url_list))
      for url in family_test_runner_url_list:
        self.checkValidHTTPSURL(url)

  def test_zope_listen(self):
    # we requested 3 zope in family1 and 5 zopes in family2, we should have 8 zope running.
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    self.assertEqual(
        3 + 5,
        len([p for p in all_process_info if p['name'].startswith('zope-')]))

  def test_apache_listen(self):
    # We have 2 families, apache should listen to a total of 3 ports per family
    # normal access on ipv4 and ipv6 and test runner access on ipv4 only
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = (p for p in all_process_info if p['name'] == 'apache')
    apache_process = psutil.Process(process_info['pid'])
    self.assertEqual(
        sorted([socket.AF_INET] * 4 + [socket.AF_INET6] * 2),
        sorted(
            c.family
            for c in apache_process.connections()
            if c.status == 'LISTEN'
        ))

  def test_haproxy_listen(self):
    # There is one haproxy per family
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = (
        p for p in all_process_info if p['name'].startswith('haproxy-')
    )
    haproxy_process = psutil.Process(process_info['pid'])
    self.assertEqual([socket.AF_INET, socket.AF_INET], [
        c.family for c in haproxy_process.connections() if c.status == 'LISTEN'
    ])


class TestZopeNodeParameterOverride(ERP5InstanceTestCase, TestPublishedURLIsReachableMixin):
  """Test override zope node parameters
  """
  __partition_reference__ = 'override'

  @classmethod
  def getInstanceParameterDict(cls):
    # The following example includes the most commonly used options,
    # but not necessarily in a meaningful way.
    return {'_': json.dumps({
      "zodb": [{
        "type": "zeo",
        "server": {},
        "cache-size-bytes": "20MB",
        "cache-size-bytes!": [
          ("bb-0", 1<<20),
          ("bb-.*", "500MB"),
        ],
        "pool-timeout": "10m",
        "storage-dict": {
          "cache-size!": [
            ("a-.*", "50MB"),
          ],
        },
      }],
      "zope-partition-dict": {
          "a": {
              "instance-count": 3,
          },
          "bb": {
              "instance-count": 5,
              "port-base": 2300,
          },
      },
    })}

  def test_zope_conf(self):
    zeo_addr = json.loads(
        self.getComputerPartition('zodb').getConnectionParameter('_')
      )["storage-dict"]["root"]["server"]

    def checkParameter(line, kw):
      k, v = line.split()
      self.assertFalse(k.endswith('!'), k)
      try:
        expected = kw.pop(k)
      except KeyError:
        if k == 'server':
          return
      self.assertIsNotNone(expected)
      self.assertEqual(str(expected), v)

    def checkConf(zodb, storage):
      zodb["mount-point"] = "/"
      zodb["pool-size"] = 4
      zodb["pool-timeout"] = "10m"
      zodb["%import"] = "ZEO"
      storage["storage"] = "root"
      storage["server"] = zeo_addr
      storage["server-sync"] = "true"
      with open(f'{partition}/etc/zope-{zope}.conf') as f:
        conf = list(map(str.strip, f.readlines()))
      i = conf.index("<zodb_db root>") + 1
      conf = iter(conf[i:conf.index("</zodb_db>", i)])
      for line in conf:
        if line == '<clientstorage>':
          for line in conf:
            if line == '</clientstorage>':
              break
            checkParameter(line, storage)
          for k, v in storage.items():
            self.assertIsNone(v, k)
          del storage
        else:
          checkParameter(line, zodb)
      for k, v in zodb.items():
        self.assertIsNone(v, k)

    partition = self.getComputerPartitionPath('zope-a')
    for zope in range(3):
      checkConf({
          "cache-size-bytes": "20MB",
        }, {
          "cache-size": "50MB",
        })
    partition = self.getComputerPartitionPath('zope-bb')
    for zope in range(5):
      checkConf({
          "cache-size-bytes": "500MB" if zope else 1<<20,
        }, {
          "cache-size": None,
        })


def popenCommunicate(command_list, input_=None, **kwargs):
  kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  popen = subprocess.Popen(command_list, **kwargs)
  result = popen.communicate(input_)[0]
  if popen.returncode is None:
    popen.kill()
  if popen.returncode != 0:
    raise ValueError(
      f'Issue during calling {command_list!r}, result was:\n{result}')
  return result


class TestHandler(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    response = json.dumps(
        {
            'Path': self.path,
            'Incoming Headers': {k.lower(): v for k, v in self.headers.items()},
        },
        indent=2,
    ).encode('utf-8')
    self.end_headers()
    self.wfile.write(response)


class TestDeploymentScriptInstantiation(ERP5InstanceTestCase):
  """This check deployment script like instantiation

  Low level assertions are done here in order to assure that
  https://lab.nexedi.com/nexedi/slapos.package/blob/master/playbook/
  slapos-master-standalone.yml
  works correctly
  """
  __partition_reference__ = 'tdsi'
  # a bit more partition is required
  partition_count = 20

  @classmethod
  def getInstanceParameterDict(cls):
    # As close as possible configuration to deployment script
    parameter_dict = {
      "timezone": "UTC",
      "site-id": "erp5",
      "bt5": "erp5_full_text_myisam_catalog slapos_configurator",
      "test-runner": {"enabled": False},  # won't work anyway here
      "zope-partition-dict": {
        "admin": {
          "family": "admin",
          "thread-amount": 4,
          "port-base": 2220,
          "instance-count": 1
        },
        "activities-node": {
          "family": "activities",
          "thread-amount": 4,
          "instance-count": 1,
          "timerserver-interval": 1,
          "port-base": 2230
        },
        "distribution-node": {
          "family": "distribution",
          "thread-amount": 1,
          "instance-count": 1,
          "port-base": 2210,
          "timerserver-interval": 1
        },
        "web-node": {
          "family": "web",
          "thread-amount": 2,
          "instance-count": 1,
          "port-base": 2240
        },
        "service-slapos": {
          "family": "service",
          "thread-amount": 2,
          "instance-count": 1,
          "port-base": 2250,
          "ssl-authentication": True,
          "backend-path": "/%(site-id)s/portal_slap"
        }
      }
    }

    # put shared-certificate-authority-path in controlled location
    cls.ca_path = os.path.join(cls.slap.instance_directory, 'ca_path')
    parameter_dict["shared-certificate-authority-path"] = cls.ca_path
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def callSupervisorMethod(cls, method, *args, **kwargs):
    with cls.slap.instance_supervisor_rpc as instance_supervisor:
      return getattr(instance_supervisor, method)(*args, **kwargs)

  @unittest.expectedFailure
  def test_ssl_auth(self):
    backend_apache_configuration_list = glob.glob(
      os.path.join(
        self.slap.instance_directory, '*', 'etc', 'apache', 'apache.conf'))
    self.assertEqual(
      1,
      len(backend_apache_configuration_list)
    )
    with open(backend_apache_configuration_list[0]) as f:
      backend_apache_configuration = f.read()
    self.assertIn(
      'SSLVerifyClient require',
      backend_apache_configuration
    )
    self.assertIn(
      r'RequestHeader set Remote-User %{SSL_CLIENT_S_DN_CN}s',
      backend_apache_configuration
    )

    # stop haproxy, it's going to be hijacked
    haproxy_name = ':'.join([
      (q['group'], q['name'])
      for q in self.callSupervisorMethod('getAllProcessInfo')
      if 'haproxy' in q['name']][0])
    self.callSupervisorMethod('stopProcess', haproxy_name)

    # do similar certificate request like CertificateAuthorityTool
    openssl_config = os.path.join(self.ca_path, 'openssl.cnf')
    key = os.path.join(self.ca_path, 'private', 'test.key')
    csr = os.path.join(self.ca_path, 'text.csr')
    cert = os.path.join(self.ca_path, 'certs', 'test.crt')
    common_name = 'TEST-SSL-AUTH'
    popenCommunicate([
      'openssl', 'req', '-utf8', '-nodes', '-config', openssl_config, '-new',
      '-keyout', key, '-out', csr, '-days', '3650'], f'{common_name}\n'.encode(),
      stdin=subprocess.PIPE)
    popenCommunicate([
      'openssl', 'ca', '-utf8', '-days', '3650', '-batch', '-config',
      openssl_config, '-out', cert, '-infiles', csr])
    # find IP and port on which hijacked process shall listen
    portal_slap_line = [
      q for q in backend_apache_configuration.splitlines()
      if 'portal_slap' in q][0]
    ip, port = re.search(
      r'.*http:\/\/(.*):(\d*)\/.*', portal_slap_line).groups()
    port = int(port)
    server = http.server.HTTPServer((ip, port), TestHandler)
    server_process = multiprocessing.Process(
      target=server.serve_forever, name='HTTPServer')
    server_process.start()
    self.addCleanup(server_process.terminate)
    self.addCleanup(server_process.join, 10)
    server.socket.close()

    # assert that accessing the service endpoint results with certificate
    # authentication and proper information extraction
    result_json = requests.get(
      self.getRootPartitionConnectionParameterDict()['family-service'],
      verify=False, cert=(cert, key)).json()
    self.assertEqual(
      common_name,
      result_json['Incoming Headers']['remote-user']
    )
    self.assertEqual(
      '/erp5/portal_slap/',
      result_json['Path']
    )
