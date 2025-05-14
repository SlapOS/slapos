##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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

import json
import msgpack
import os
import random
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import sys

from http.server import SimpleHTTPRequestHandler
from socketserver import StreamRequestHandler, TCPServer

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import findFreeTCPPort

FLUENTD_PORT = 24224
FLUSH_INTERVAL = 1


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class OneRequestServer(TCPServer):

  address_family = socket.AF_INET6
  timeout = 1

  def get_first_data(self, flush_interval=1):
    start = time.time()
    while(not self.RequestHandlerClass.received_data
          and time.time() - start < 10*flush_interval):
      self.handle_request()
    return self.RequestHandlerClass.received_data


class FluentdHTTPRequestHandler(StreamRequestHandler):

  received_data = b''

  def handle(self):
    data = self.rfile.readline().strip()
    # ignore heartbeats (https://docs.fluentd.org/output/forward#heartbeat_type)
    if len(data) > 0:
      FluentdHTTPRequestHandler.received_data = data


class WendelinHTTPRequestHandler(SimpleHTTPRequestHandler):

  received_data = b''

  def do_POST(self):
    WendelinHTTPRequestHandler.received_data = self.rfile.read(
      int(self.headers['Content-Length']))
    self.send_response(200)
    self.end_headers()


class WendelinTutorialTestCaseMixin:

  @classmethod
  def measureDict(cls):
    return {k: v for k, v in
      zip(('pressure', 'humidity', 'temperature'), cls._measurementList)}

  @classmethod
  def sensor_value_list(cls):
    return [str(value) for value in (round(random.uniform(870, 1084), 2),
                                     round(random.uniform(0, 100), 2),
                                     round(random.uniform(-20, 50), 3))]

  def serve(self, port, request_handler_class):
    server_address = (self.computer_partition_ipv6_address, port)
    server = OneRequestServer(server_address, request_handler_class)

    data = server.get_first_data(FLUSH_INTERVAL)
    server.server_close()
    return data


class FluentdTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'fluentd'

  @classmethod
  def getInstanceParameterDict(cls):
    # Required placeholder values
    parameter_dict = {
      'wendelin-ingestion-url': 'foo',
      'username': 'bar',
      'password': 'baz'
    }
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    cls._fluentd_conf = os.path.join(cls.computer_partition_root_path, 'etc', 'fluentd-agent.conf')

    fluentd_dir = os.path.join(cls.computer_partition_root_path,
                               'software_release', 'parts', 'fluentd')
    cls._fluentd_bin = os.path.join(fluentd_dir, 'bin', 'fluentd')
    cls._gem_path = os.path.join(fluentd_dir, 'lib', 'ruby', 'gems')

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()

  def read_fluentd_conf(self):
    return subprocess.check_output(
      [self._fluentd_bin, '-c', self._fluentd_conf, '--dry-run'],
      env={'GEM_PATH': self._gem_path},
      text=True,
    )

  def _test_configuration(self, expected_str):
    fluentd_conf_content = ''
    with open(self._fluentd_conf, 'r') as file:
      fluentd_conf_content = file.read()
    self.assertEqual(
      fluentd_conf_content,
      self.get_configuration(),
    )
    self.assertRegex(
      self.read_fluentd_conf(),
      expected_str,
    )

  def test_process(self):
    expected_process_name_list = [
      'fluentd-service-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                       for process in supervisor.getAllProcessInfo()]

    for expected_process_name in expected_process_name_list:
      self.assertIn(expected_process_name, process_names)


# see https://wendelin.nexedi.com/wendelin-Learning.Track/wendelin-Tutorial.Setup.Fluentd.on.Sensor
class SensorConfTestCase(WendelinTutorialTestCaseMixin, FluentdTestCase):

  @classmethod
  def getInstanceSoftwareType(cls):
    return 'expert'

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {'conf-text': cls._conf}
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def sensor_script(cls, measurementList):
    measurement_text = "\t".join(measurementList)
    return f'''\
#!{sys.executable}
# -*- coding: utf-8 -*-

print("{measurement_text}")'''

  @classmethod
  def sensor_conf(cls, script_path):
    return f'''\
<source>
  @type exec
  tag tag.name
  command {sys.executable} {script_path}
  run_interval {FLUSH_INTERVAL}s
  <parse>
    keys pressure, humidity, temperature
  </parse>
</source>
<match tag.name>
  @type forward
  <server>
    name myserver1
    host {cls.computer_partition_ipv6_address}
  </server>
  <buffer>
    flush_mode immediate
  </buffer>
</match>'''

  @classmethod
  def get_configuration(cls):
    script_path = os.path.join(cls._tmp_dir, "custom_read_bme280.py")
    with open(script_path, "w") as script:
      script.write(cls.sensor_script(cls._measurementList))
    return cls.sensor_conf(script_path)

  @classmethod
  def setUpClass(cls):
    cls._tmp_dir = tempfile.mkdtemp()
    cls._measurementList = cls.sensor_value_list()
    cls._conf = cls.get_configuration()

    super(FluentdTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls._tmp_dir)
    super(FluentdTestCase, cls).tearDownClass()

  def test_configuration(self):
    self._test_configuration(
      fr'adding forwarding server \'myserver1\' host="{self.computer_partition_ipv6_address}" port={FLUENTD_PORT} weight=60'
    )

  def test_send_data(self):
    tag, data, header = msgpack.unpackb(
      self.serve(FLUENTD_PORT, FluentdHTTPRequestHandler),
      raw=True,
    )
    self.assertEqual(b'tag.name', tag)
    self.assertEqual(self.measureDict(), msgpack.unpackb(data)[-1])
    self.assertEqual({b'compressed': b'text', b'size': 1}, header)


# see https://wendelin.nexedi.com/wendelin-Learning.Track/wendelin-Tutorial.Setup.Fluentd.on.IOTGateway
class GatewayConfTestCase(WendelinTutorialTestCaseMixin, FluentdTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {
      'bind': cls.computer_partition_ipv6_address,
      'port': cls._fluentd_port,
      'tag-match-pattern': 'tag.name',
      'wendelin-ingestion-url': f'http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}/erp5/portal_ingestion_policies/default',
      'username': 'foo',
      'password': 'bar',
      'flush-interval': '1s'
    }
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def get_configuration(cls):
    buffer_file_dir = os.path.join(cls.computer_partition_root_path, 'var', 'fluentd-buffer')
    return f'''\
<source>
  @type forward
  bind {cls.computer_partition_ipv6_address}
  port {cls._fluentd_port}
</source>
<match tag.name>
  @type wendelin
  streamtool_uri http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}/erp5/portal_ingestion_policies/default
  user foo
  password bar
  <buffer tag,time>
    timekey 1m
    flush_mode interval
    flush_interval 1s
    flush_thread_count 4
    @type file
    path {buffer_file_dir}/
  </buffer>
</match>'''

  @classmethod
  def setUpClass(cls):
    cls._measurementList = cls.sensor_value_list()

    cls._fluentd_port = findFreeTCPPort(cls.computer_partition_ipv6_address)
    cls._wendelin_port = findFreeTCPPort(cls.computer_partition_ipv6_address)

    super(FluentdTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    super(FluentdTestCase, cls).tearDownClass()

  def test_configuration_file(self):
    self._test_configuration('starting fluentd')

  def test_wendelin_data_forwarding(self):
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.connect((self.computer_partition_ipv6_address, self._fluentd_port))

    data = [
      msgpack.ExtType(0, struct.pack('!Q', int(time.time()) << 32)),
      self.measureDict(),
    ]
    sock.sendall(
      msgpack.packb([
        b'tag.name',
        msgpack.packb(data),
        {b'size': 1, b'compressed': b'text'},
      ], use_bin_type=False),
    )
    sock.close()

    self.assertEqual(
      data,
      msgpack.unpackb(
        self.serve(self._wendelin_port, WendelinHTTPRequestHandler)),
    )


class TlsDefaultTestCase(FluentdTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {
      'tls-transport-enabled': True,
      'bind': cls.computer_partition_ipv6_address,
      'port': cls._fluentd_port,
      'wendelin-ingestion-url': f'http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}',
      'username': 'foo',
      'password': 'bar'
    }
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def get_configuration(cls):
    buffer_file_dir = os.path.join(cls.computer_partition_root_path, 'var', 'fluentd-buffer')
    ca_cert_dir = os.path.join(cls.computer_partition_root_path, 'srv', 'ssl', 'certs')
    return f'''\
<source>
  @type forward
  bind {cls.computer_partition_ipv6_address}
  port {cls._fluentd_port}
  <transport tls>
    cert_path {ca_cert_dir}/fluentd.crt
    private_key_path {ca_cert_dir}/fluentd.key
    private_key_passphrase
  </transport>
</source>
<match **>
  @type wendelin
  streamtool_uri http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}
  user foo
  password bar
  <buffer tag,time>
    timekey 1m
    flush_mode interval
    flush_interval 1m
    flush_thread_count 4
    @type file
    path {buffer_file_dir}/
  </buffer>
</match>'''

  @classmethod
  def setUpClass(cls):
    cls._fluentd_port = findFreeTCPPort(cls.computer_partition_ipv6_address)
    cls._wendelin_port = findFreeTCPPort(cls.computer_partition_ipv6_address)

    super(FluentdTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    super(FluentdTestCase, cls).tearDownClass()

  def test_configuration_file(self):
    self._test_configuration('starting fluentd')


class TagPrefixDefaultTestCase(FluentdTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {
      'bind': cls.computer_partition_ipv6_address,
      'port': cls._fluentd_port,
      'tag-prefix': 'ors',
      'wendelin-ingestion-url': f'http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}',
      'username': 'foo',
      'password': 'bar'
    }
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def get_configuration(cls):
    buffer_file_dir = os.path.join(cls.computer_partition_root_path, 'var', 'fluentd-buffer')
    return f'''\
<source>
  @type forward
  bind {cls.computer_partition_ipv6_address}
  port {cls._fluentd_port}
  add_tag_prefix ors
</source>
<match ors.**>
  @type wendelin
  streamtool_uri http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}
  user foo
  password bar
  <buffer tag,time>
    timekey 1m
    flush_mode interval
    flush_interval 1m
    flush_thread_count 4
    @type file
    path {buffer_file_dir}/
  </buffer>
</match>'''

  @classmethod
  def setUpClass(cls):
    cls._fluentd_port = findFreeTCPPort(cls.computer_partition_ipv6_address)
    cls._wendelin_port = findFreeTCPPort(cls.computer_partition_ipv6_address)

    super(FluentdTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    super(FluentdTestCase, cls).tearDownClass()

  def test_configuration_file(self):
    self._test_configuration('starting fluentd')


class TagMatchPatternWithTagPrefixDefaultTestCase(FluentdTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {
      'bind': cls.computer_partition_ipv6_address,
      'port': cls._fluentd_port,
      'tag-prefix': 'ors',
      'tag-match-pattern': 'tag.name',
      'wendelin-ingestion-url': f'http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}',
      'username': 'foo',
      'password': 'bar'
    }
    return {'_': json.dumps(parameter_dict)}

  @classmethod
  def get_configuration(cls):
    buffer_file_dir = os.path.join(cls.computer_partition_root_path, 'var', 'fluentd-buffer')
    return f'''\
<source>
  @type forward
  bind {cls.computer_partition_ipv6_address}
  port {cls._fluentd_port}
  add_tag_prefix ors
</source>
<match tag.name>
  @type wendelin
  streamtool_uri http://[{cls.computer_partition_ipv6_address}]:{cls._wendelin_port}
  user foo
  password bar
  <buffer tag,time>
    timekey 1m
    flush_mode interval
    flush_interval 1m
    flush_thread_count 4
    @type file
    path {buffer_file_dir}/
  </buffer>
</match>'''

  @classmethod
  def setUpClass(cls):
    cls._fluentd_port = findFreeTCPPort(cls.computer_partition_ipv6_address)
    cls._wendelin_port = findFreeTCPPort(cls.computer_partition_ipv6_address)

    super(FluentdTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    super(FluentdTestCase, cls).tearDownClass()

  def test_configuration_file(self):
    self._test_configuration('starting fluentd')
