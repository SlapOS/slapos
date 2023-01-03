##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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

from __future__ import unicode_literals
import io
import logging
import os
import tempfile
import textwrap
import time
import json

import psutil
import requests
from six.moves import configparser

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class GrafanaTestCase(SlapOSInstanceTestCase):
  """Base test case for grafana.

  Since the instances takes time to start and stop,
  we increase the number of retries.
  """
  instance_max_retry = 50
  report_max_retry = 30


class TestGrafana(GrafanaTestCase):
  def setUp(self):
    self.grafana_url = self.computer_partition.getConnectionParameterDict(
    )['grafana-url']

  def test_grafana_available(self):
    resp = requests.get(self.grafana_url, verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)

  def test_grafana_api(self):
    # check API is usable
    api_org_url = '{self.grafana_url}/api/org'.format(**locals())
    resp = requests.get(api_org_url, verify=False)
    self.assertEqual(requests.codes.unauthorized, resp.status_code)

    connection_params = self.computer_partition.getConnectionParameterDict()
    resp = requests.get(
        api_org_url,
        verify=False,
        auth=requests.auth.HTTPBasicAuth(
            connection_params['grafana-username'],
            connection_params['grafana-password'],
        ))
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertEqual(1, resp.json()['id'])

  def test_grafana_datasource_provisioned(self):
    # data sources are provisionned
    connection_params = self.computer_partition.getConnectionParameterDict()
    resp = requests.get(
        '{self.grafana_url}/api/datasources'.format(**locals()),
        verify=False,
        auth=requests.auth.HTTPBasicAuth(
            connection_params['grafana-username'],
            connection_params['grafana-password'],
        ))
    self.assertEqual(requests.codes.ok, resp.status_code)
    self.assertEqual(
        sorted(['influxdb', 'loki']),
        sorted([ds['type'] for ds in resp.json()]))

  def test_email_disabled(self):
    config = configparser.ConfigParser()
    # grafana config file is like an ini file with an implicit default section
    with open(
        os.path.join(self.computer_partition_root_path, 'etc',
                     'grafana-config-file.cfg')) as f:
      config.read_file(io.StringIO('[default]\n' + f.read()))
    self.assertEqual(config.get('smtp', 'enabled'), 'false')


class TestGrafanaEmailEnabled(GrafanaTestCase):
  __partition_reference__ = 'mail'
  smtp_verify_ssl = "true"
  smtp_skip_verify = "false"

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        "smtp-server": "smtp.example.com:25",
        "smtp-username": "smtp_username",
        "smtp-password": "smtp_password",
        'smtp-verify-ssl': cls.smtp_verify_ssl,
        "email-from-address": "grafana@example.com",
        "email-from-name": "Grafana From Name",
    }

  def test_email_enabled(self):
    config = configparser.ConfigParser()
    with open(
        os.path.join(self.computer_partition_root_path, 'etc',
                     'grafana-config-file.cfg')) as f:
      config.readfp(io.StringIO('[default]\n' + f.read()))

    self.assertEqual(config.get('smtp', 'enabled'), 'true')
    self.assertEqual(config.get('smtp', 'host'), 'smtp.example.com:25')
    self.assertEqual(config.get('smtp', 'user'), 'smtp_username')
    self.assertEqual(config.get('smtp', 'password'), '"""smtp_password"""')
    self.assertEqual(config.get('smtp', 'skip_verify'), self.smtp_skip_verify)
    self.assertEqual(config.get('smtp', 'from_address'), 'grafana@example.com')
    self.assertEqual(config.get('smtp', 'from_name'), 'Grafana From Name')


class TestGrafanaEmailEnabledSkipVerify(TestGrafanaEmailEnabled):
  smtp_verify_ssl = "false"
  smtp_skip_verify = "true"


class TestInfluxDb(GrafanaTestCase):
  def setUp(self):
    self.influxdb_url = self.computer_partition.getConnectionParameterDict(
    )['influxdb-url']

  def test_influxdb_available(self):
    ping_url = '{self.influxdb_url}/ping'.format(**locals())
    resp = requests.get(ping_url, verify=False)
    self.assertEqual(requests.codes.no_content, resp.status_code)

  def test_influxdb_api(self):
    query_url = '{self.influxdb_url}/query'.format(**locals())
    connection_params = self.computer_partition.getConnectionParameterDict()

    for i in range(10):
      # retry, as it may take a little delay to create databases
      resp = requests.get(
          query_url,
          verify=False,
          params=dict(
              q='SHOW DATABASES',
              u=connection_params['influxdb-username'],
              p=connection_params['influxdb-password']))
      self.assertEqual(requests.codes.ok, resp.status_code)
      result, = resp.json()['results']
      if result['series'] and 'values' in result['series'][0]:
        break
      time.sleep(0.5 * i)

    self.assertIn(
        [connection_params['influxdb-database']], result['series'][0]['values'])


class TestTelegraf(GrafanaTestCase):
  def test_telegraf_running(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if 'telegraf' in p['name']]
    self.assertEqual('RUNNING', process_info['statename'])


class TestLoki(GrafanaTestCase):
  instance_max_retry = 2
  @classmethod
  def getInstanceParameterDict(cls):
    cls._logfile = tempfile.NamedTemporaryFile(suffix='log')
    parameter_dict = {
        "applications": [
    {
      "name": "System",
      "instance-root": "/",
      "partitions": [
        {
          # no slapos for system application
          # XXX example
          "name": "syslog",
          "reference": "syslog",
          "files": [
            "/srv/slapgrid/slappart15/grosgzip/bench.log",
          ]
        },
      ]
    },
    {
      "name": "ERP5",
      "instance-root": "/srv/slapgrid/slappart15/srv/runner/instance/",
      "urls": [
        # TODO
       # "https://XXX.host.vifib.net/erp5/",
      ],
      "partitions": [
        {
          "name": "jerome-dev-mariadb",
          "reference": "slappart3",
          "type": "erp5/mariadb",
          #"static-tags": {
          #  "XXX": "needed?"
          #}
        },
        {
          "name": "jerome-dev-zodb",
          "reference": "slappart4",
          "type": "erp5/zeo",
          #"static-tags": {
          #  "XXX": "needed?"
          #}
        },
        {
          "name": "jerome-dev-balancer",
          "reference": "slappart6",
          "type": "erp5/balancer",
          #"static-tags": {
          #  "XXX": "needed?"
          #}
        },
        {
          "name": "jerome-dev-zope-front",
          "reference": "slappart5",
          "type": "erp5/zope-front",
          #"static-tags": {
          #  "XXX": "needed?"
          #}
        },
        # {
          # "name": "jerome-dev-zope-front",
          # "reference": "slappart13",
          # "type": "erp5/zope-activity",
          # #"static-tags": {
          # #  "XXX": "needed?"
          # #}
        # }
      ]
    }
  ],
  # TODO: drop this
        'promtail-extra-scrape-config':
        textwrap.dedent(r'''
                - job_name: {cls.__name__}
                  pipeline_stages:
                    - match:
                        selector: '{{job="{cls.__name__}"}}'
                        stages:
                          - multiline:
                              firstline: '^\d{{4}}-\d{{2}}-\d{{2}}\s\d{{1,2}}\:\d{{2}}\:\d{{2}}\,\d{{3}}'
                              max_wait_time: 3s
                          - regex:
                              expression: '^(?P<timestamp>.*) - (?P<name>\S+) - (?P<level>\S+) - (?P<message>.*)'
                          - timestamp:
                              format: 2006-01-02T15:04:05Z00:00
                              source: timestamp
                          - labels:
                              level:
                              name:
                  static_configs:
                    - targets:
                        - localhost
                      labels:
                        job: {cls.__name__}
                        __path__: {cls._logfile.name}
            ''').format(**locals())
    }
    return {'_': json.dumps(parameter_dict)}


  def xgetInstanceParameterDict(cls):
    cls._logfile = tempfile.NamedTemporaryFile(suffix='log')
    return {
        'promtail-extra-scrape-config':
            textwrap.dedent(
                r'''
                - job_name: {cls.__name__}
                  pipeline_stages:
                    - match:
                        selector: '{{job="{cls.__name__}"}}'
                        stages:
                          - multiline:
                              firstline: '^\d{{4}}-\d{{2}}-\d{{2}}\s\d{{1,2}}\:\d{{2}}\:\d{{2}}\,\d{{3}}'
                              max_wait_time: 3s
                          - regex:
                              expression: '^(?P<timestamp>.*) - (?P<name>\S+) - (?P<level>\S+) - (?P<message>.*)'
                          - timestamp:
                              format: 2006-01-02T15:04:05Z00:00
                              source: timestamp
                          - labels:
                              level:
                              name:
                  static_configs:
                    - targets:
                        - localhost
                      labels:
                        job: {cls.__name__}
                        __path__: {cls._logfile.name}
            ''').format(**locals())
    }

  @classmethod
  def tearDownClass(cls):
    cls._logfile.close()
    super(TestLoki, cls).tearDownClass()

  def setUp(self):
    self.loki_url = self.computer_partition.getConnectionParameterDict(
    )['loki-url']

  def test_loki_available(self):
    import pdb;pdb; set_trace()
    self.assertEqual(
        requests.codes.ok,
        requests.get(f'{self.loki_url}/ready',
                     verify=False).status_code)

  def test_log_ingested(self):
    # create a logger logging to the file that we have
    # configured in instance parameter.
    test_logger = logging.getLogger(self.id())
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)
    test_handler = logging.FileHandler(filename=self._logfile.name)
    test_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    test_logger.addHandler(test_handler)
    test_logger.info("testing message")
    test_logger.info("testing another message")
    test_logger.warning("testing warn")
    # log an exception, which will be multi line in log file.
    def nested1():
      def nested2():
        raise ValueError('boom')
      nested2()
    try:
      nested1()
    except ValueError:
      test_logger.exception("testing exception")

    # Check our messages have been ingested
    # we retry a few times, because there's a short delay until messages are
    # ingested and returned.
    for i in range(60):
      resp = requests.get(
          '{self.loki_url}/api/prom/query?query={{job="TestLoki"}}'.format(
              **locals()),
          verify=False).json()
      if len(resp.get('streams', [])) < 3:
        time.sleep(0.5 * i)
        continue

    warn_stream_list = [stream for stream in resp['streams'] if 'level="WARNING"' in stream['labels']]
    self.assertEqual(1, len(warn_stream_list), resp['streams'])
    warn_stream, = warn_stream_list
    self.assertIn("testing warn", warn_stream['entries'][0]['line'])

    info_stream_list = [stream for stream in resp['streams'] if 'level="INFO"' in stream['labels']]
    self.assertEqual(1, len(info_stream_list), resp['streams'])
    info_stream, = info_stream_list
    self.assertTrue(
        [
            line for line in info_stream['entries']
            if "testing message" in line['line']
        ])
    self.assertTrue(
        [
            line for line in info_stream['entries']
            if "testing another message" in line['line']
        ])

    error_stream_list = [stream for stream in resp['streams'] if 'level="ERROR"' in stream['labels']]
    self.assertEqual(1, len(error_stream_list), resp['streams'])
    error_stream, = error_stream_list
    line, = [line['line'] for line in error_stream['entries']]
    # this entry is multi-line
    self.assertIn('testing exception\nTraceback (most recent call last):\n', line)
    self.assertIn('ValueError: boom', line)

    # The labels we have configued are also available
    resp = requests.get(
        '{self.loki_url}/api/prom/label'.format(**locals()),
        verify=False).json()
    self.assertIn('level', resp['values'])
    self.assertIn('name', resp['values'])


class TestListenInPartition(GrafanaTestCase):
  def setUp(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()

    self.process_dict = {
        p['name'].replace('-on-watch', ''): psutil.Process(p['pid'])
        for p in all_process_info if p['name'] != 'watchdog'
    }

  def test_grafana_listen(self):
    self.assertEqual(
        [
            c.laddr for c in self.process_dict['grafana'].connections()
            if c.status == 'LISTEN'
        ],
        [(self.computer_partition_ipv6_address, 8180)],
    )

  def test_influxdb_listen(self):
    self.assertEqual(
        sorted([
            c.laddr for c in self.process_dict['influxdb'].connections()
            if c.status == 'LISTEN'
        ]),
        [
            (self._ipv4_address, 8088),
            (self.computer_partition_ipv6_address, 8086),
        ],
    )

  def test_telegraph_listen(self):
    self.assertEqual(
        [
            c.laddr for c in self.process_dict['telegraf'].connections()
            if c.status == 'LISTEN'
        ],
        [],
    )

  def test_loki_listen(self):
    self.assertEqual(
        sorted([
            c.laddr for c in self.process_dict['loki'].connections()
            if c.status == 'LISTEN'
        ]),
        [
            (self._ipv4_address, 3100),
            (self._ipv4_address, 9095),
        ],
    )

  def test_promtail_listen(self):
    self.assertEqual(
        sorted([
            c.laddr for c in self.process_dict['promtail'].connections()
            if c.status == 'LISTEN'
        ]),
        [
            (self._ipv4_address, 19080),
            (self._ipv4_address, 19095),
        ],
    )
