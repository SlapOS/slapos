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

import functools
import io
import json
import logging
import pathlib
import re
import tempfile
import time
import urllib.parse

import psutil
import requests
from six.moves import configparser

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  pathlib.Path(__file__).parent.parent / 'software.cfg')


class GrafanaTestCase(SlapOSInstanceTestCase):
  """Base test case for grafana.

  Since the instances takes time to start and stop,
  we increase the number of retries.
  """
  instance_max_retry = 50
  report_max_retry = 30


class TestGrafana(GrafanaTestCase):
  def setUp(self):
    self.connection_params = json.loads(
      self.computer_partition.getConnectionParameterDict()['_']
    )
    self.grafana_url = self.connection_params['grafana-url']

  def test_grafana_available(self):
    resp = requests.get(self.grafana_url, verify=False)
    self.assertEqual(resp.status_code, requests.codes.ok)

  def test_grafana_api(self):
    # check API is usable
    api_org_url = f'{self.grafana_url}/api/org'
    resp = requests.get(api_org_url, verify=False)
    self.assertEqual(resp.status_code, requests.codes.unauthorized)

    resp = requests.get(
      api_org_url,
      verify=False,
      auth=requests.auth.HTTPBasicAuth(
        self.connection_params['grafana-username'],
        self.connection_params['grafana-password'],
      ))
    self.assertEqual(resp.status_code, requests.codes.ok)
    self.assertEqual(resp.json()['id'], 1)

  def test_grafana_datasource_provisioned(self):
    # data sources are provisionned
    get = functools.partial(
      requests.get,
      verify=False,
      auth=requests.auth.HTTPBasicAuth(
        self.connection_params['grafana-username'],
        self.connection_params['grafana-password'],
      )
    )
    datasources_resp = get(f'{self.grafana_url}/api/datasources')
    self.assertEqual(datasources_resp.status_code, requests.codes.ok)
    self.assertEqual(
      sorted([ds['type'] for ds in datasources_resp.json()]),
      sorted(['influxdb', 'loki']))

    # data sources are usable
    # for this we need to wait a bit, because they are only usable once
    # some data has been ingested
    influxdb, = [ds for ds in datasources_resp.json() if ds['type'] == 'influxdb']
    loki, = [ds for ds in datasources_resp.json() if ds['type'] == 'loki']
    for retry in range(16):
      influxdb_health = get(f'{self.grafana_url}/api/datasources/uid/{influxdb["uid"]}/health').json()
      if influxdb_health.get('status') == "OK":
        break
      time.sleep(retry)
    self.assertEqual(influxdb_health['status'], "OK")
    for retry in range(16):
      loki_health = get(f'{self.grafana_url}/api/datasources/uid/{loki["uid"]}/resources/labels?start={time.time() - 1000}').json()
      if loki_health.get('data'):
        break
      time.sleep(retry)
    else:
      self.fail(loki_health)
    self.assertEqual(loki_health['status'], "success")
    self.assertIn("app", loki_health['data'])

  def test_email_disabled(self):
    config = configparser.ConfigParser()
    # grafana config file is like an ini file with an implicit default section
    f = self.computer_partition_root_path / 'etc' / 'grafana-config-file.cfg'
    config.read_file(io.StringIO('[default]\n' + f.read_text()))
    self.assertEqual(config.get('smtp', 'enabled'), 'false')


class TestGrafanaEmailEnabled(GrafanaTestCase):
  __partition_reference__ = 'mail'
  smtp_verify_ssl = True
  smtp_skip_verify = "false"

  @classmethod
  def getInstanceParameterDict(cls):
    return {"_": json.dumps({
      "email": {
        "smtp-server": "smtp.example.com:25",
        "smtp-username": "smtp_username",
        "smtp-password": "smtp_password",
        'smtp-verify-ssl': cls.smtp_verify_ssl,
        "email-from-address": "grafana@example.com",
        "email-from-name": "Grafana From Name",
      }})}

  def test_email_enabled(self):
    config = configparser.ConfigParser()
    f = self.computer_partition_root_path / 'etc' / 'grafana-config-file.cfg'
    config.read_file(io.StringIO('[default]\n' + f.read_text()))
    self.assertEqual(config.get('smtp', 'enabled'), 'true')
    self.assertEqual(config.get('smtp', 'host'), 'smtp.example.com:25')
    self.assertEqual(config.get('smtp', 'user'), 'smtp_username')
    self.assertEqual(config.get('smtp', 'password'), '"""smtp_password"""')
    self.assertEqual(config.get('smtp', 'skip_verify'), self.smtp_skip_verify)
    self.assertEqual(config.get('smtp', 'from_address'), 'grafana@example.com')
    self.assertEqual(config.get('smtp', 'from_name'), 'Grafana From Name')


class TestGrafanaEmailEnabledSkipVerify(TestGrafanaEmailEnabled):
  smtp_verify_ssl = False
  smtp_skip_verify = "true"


class TestInfluxDb(GrafanaTestCase):
  def setUp(self):
    self.connection_params = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.influxdb_url = self.connection_params['influxdb-url']

  def test_influxdb_available(self):
    ping_url = f'{self.influxdb_url}/ping'
    resp = requests.get(ping_url, verify=False)
    self.assertEqual(resp.status_code, requests.codes.no_content)

  def test_influxdb_api(self):
    query_url = f'{self.influxdb_url}/query'

    for i in range(16):
      # retry, as it may take a little delay to create databases
      resp = requests.get(
        query_url,
        verify=False,
        params=dict(
          q='SHOW DATABASES',
          u=self.connection_params['influxdb-username'],
          p=self.connection_params['influxdb-password']))
      self.assertEqual(resp.status_code, requests.codes.ok)
      result, = resp.json()['results']
      if result['series'] and 'values' in result['series'][0]:
        break
      time.sleep(0.5 * i)

    self.assertIn(
      [self.connection_params['influxdb-database']], result['series'][0]['values'])


class TestTelegraf(GrafanaTestCase):
  __partition_reference__ = 'G'
  @classmethod
  def getInstanceParameterDict(cls):
    parameter_dict = {
      "agent": {
        "applications": [
          {
            "name": "slapos-standalone-from-test",
            "type": "SlapOS",
            "instance-root": cls.slap._instance_root,
            "partitions": [
              {
                "name": "test grafana - default partition",
                "type": "default",
                "reference": "G0",  # XXX assumes partitions will be allocated in order
              },
              {
                "name": "test grafana - agent partition",
                "type": "default",
                "reference": "G1"
              },
            ],
          },
        ],
      },
    }
    return {'_': json.dumps(parameter_dict)}

  def setUp(self):
    self.connection_params = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.influxdb_url = self.connection_params['influxdb-url']

  def test_telegraf_running(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()
    process_info, = [p for p in all_process_info if 'telegraf' in p['name']]
    self.assertEqual(process_info['statename'], 'RUNNING')

  def test_telegraf_ingest_slapos_metrics(self):
    # wait for data to be ingested
    time.sleep(16)

    query_url = f'{self.influxdb_url}/query'
    query = """
      SELECT max("state")
      FROM "slapos_services"
      WHERE time >= now() - 5m and time <= now()
      GROUP BY time(5m),
               "partition_reference"::tag,
               "name"::tag,
               "computer_id"::tag,
               "process_name"::tag
      fill(null)
    """

    get = functools.partial(
      requests.get,
      verify=False,
      params=dict(
        q=query,
        db=self.connection_params['influxdb-database'],
        u=self.connection_params['influxdb-username'],
        p=self.connection_params['influxdb-password'],
      ),
    )
    for i in range(16):
      resp = get(query_url)
      if resp.ok and resp.json()['results'][0].get('series'):
        break
      time.sleep(i)
    else:
      self.fail(resp.text)

    series = resp.json()['results'][0].get('series')

    # hashes and "-on-watch" is removed from process_name
    self.assertIn('grafana', [s['tags']['process_name'] for s in series])
    self.assertIn('telegraf', [s['tags']['process_name'] for s in series])
    self.assertIn('loki-service', [s['tags']['process_name'] for s in series])
    self.assertIn('loki-grafana-client-certificate-updater', [s['tags']['process_name'] for s in series])

    tags = [s['tags'] for s in series if s['tags']['partition_reference'] == 'G0'][0]
    self.assertEqual(tags['name'], 'test grafana - default partition')
    self.assertEqual(tags['computer_id'], self.slap._computer_id)
    self.assertEqual(tags['partition_reference'], 'G0')

    self.assertEqual(
      {s['tags']['partition_reference'] for s in series},
      {'G0', 'G1'},
    )


class TestLoki(GrafanaTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    cls._logfile = tempfile.NamedTemporaryFile(suffix='log')
    cls.addClassCleanup(cls._logfile.close)
    parameter_dict = {
      "agent": {
        "applications": [
          {
            "name": "TestLoki",
            "type": "system",
            "partitions": [
              {
                "name": "test log file",
                "log-file-patterns": [cls._logfile.name],
                "static-tags": {
                  "testtag": "foo",
                },
              },
            ],
          },
        ],
      },
    }
    return {'_': json.dumps(parameter_dict)}

  def setUp(self):
    self.loki_url = json.loads(
      self.computer_partition.getConnectionParameterDict()['_']
    )['loki-url']

  def test_loki_certificate_required(self):
    with self.assertRaisesRegex(requests.exceptions.SSLError, 'certificate required'):
      requests.get(f'{self.loki_url}/ready', verify=False)

  def test_log_ingested(self):
    # create a logger logging to the file that we have
    # configured in instance parameter.
    test_logger = logging.getLogger(self.id())
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)
    test_handler = logging.FileHandler(filename=self._logfile.name)
    test_logger.addHandler(test_handler)
    test_logger.info("testing info message")
    get = functools.partial(
      requests.get,
      cert=(
        self.computer_partition_root_path / 'etc' / 'loki-promise-client-certificate.crt',
        self.computer_partition_root_path / 'etc' / 'loki-promise-client-certificate.key',
      ),
      verify=self.computer_partition_root_path / 'etc' / 'loki-server-certificate.ca.crt',
    )
    url = urllib.parse.urlparse(
      self.loki_url
    )._replace(
      path="/loki/api/v1/query_range",
      query=urllib.parse.urlencode({'query': '{app="TestLoki"} |= ""'}),
    ).geturl()
    for i in range(16):
      resp = get(url)
      if resp.ok:
        if result := resp.json().get('data', {}).get('result', []):
          break
      time.sleep(i)
    else:
      self.fail(resp.text)
    self.assertEqual(
      result[0]['stream'],
      {
        'app': 'TestLoki',
        'computer_id': self.slap._computer_id,
        'detected_level': 'info',
        'filename': self._logfile.name,
        'job': 'TestLoki-test log file',
        'name': 'test log file',
        'service_name': 'TestLoki',
        'testtag': 'foo',
      }
    )
    self.assertEqual(
      [v[1] for v in result[0]['values']],
      ['testing info message'])
    self.assertEqual(len(result), 1)


class TestListenInPartition(GrafanaTestCase):
  def setUp(self):
    with self.slap.instance_supervisor_rpc as supervisor:
      all_process_info = supervisor.getAllProcessInfo()

    def canonical_process_name(process):
      """remove hash from hash-files and "on-watch"
      """
      return re.sub(
        r'-([a-f0-9]{32})$',
        '',
        process['name'].replace('-on-watch', ''),
      )

    self.process_dict = {
      canonical_process_name(p): psutil.Process(p['pid'])
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
        sorted([
            (self._ipv4_address, 8088),
            (self.computer_partition_ipv6_address, 8086),
        ]),
    )

  def test_telegraf_listen(self):
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
            c.laddr for c in self.process_dict['loki-service'].connections()
            if c.status == 'LISTEN'
        ]),
        sorted([
            (self._ipv4_address, 9095),
            (self.computer_partition_ipv6_address, 3100),
        ]),
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
