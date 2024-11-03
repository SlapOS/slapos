##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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

import contextlib
import datetime
import json
import os
import pathlib
import socket
import struct
import subprocess
import typing
import urllib.parse

import psutil
import requests
import MySQLdb

from . import ERP5InstanceTestCase, default, matrix, setUpModule
from .test_erp5 import ZopeSkinsMixin


_ = setUpModule


class TestOrderBuildPackingListSimulation(
    ZopeSkinsMixin,
    ERP5InstanceTestCase,
):
  """Create orders and build packing lists.
  """
  __partition_reference__ = 's'
  __test_matrix__ = matrix((default, ))

  _start: datetime.datetime
  _previous: datetime.datetime

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {
      '_':
      json.dumps(
        {
          "bt5":
          " ".join(
            [
              "erp5_full_text_mroonga_catalog",
              "erp5_configurator_standard",
              "erp5_scalability_test",
            ]),
          "mariadb": {
            # We use a large innodb-buffer-pool-size because the simulation
            # select method used for sale packing list does not use index and
            # cause slow queries
            "innodb-buffer-pool-size": 32 * 1024 * 1024 * 1024,  # 32Go
          },
          "zope-partition-dict": {
            "activities": {
              "instance-count": 32,
              "family": "activities",
              "thread-amount": 2,
              "port-base": 2300
            },
            "default": {
              "instance-count": 1,
              "family": "default",
              "port-base": 2200
            },
          },
          "family-override": {
            "default": {
              "xml-rpc": True
            }
          }
        })
    }

  @classmethod
  def _setUpClass(cls) -> None:
    super()._setUpClass()
    cls.zope_base_url = cls._getAuthenticatedZopeUrl('')
    cls.create_sale_order_batch_url = urllib.parse.urljoin(
      cls.zope_base_url, 'ERP5Site_createScalabilityTestSaleOrderBatch')

  def setUp(self) -> None:
    super().setUp()
    self.measurement_file = open(f'measures{self.id()}.jsonl', 'w')
    self.addCleanup(self.measurement_file.close)

    # Describe the software used. TODO: use nxd-bom once integrated
    self.write_measurement(
      {
        'type': 'sbom',
        # content of runwsgi script, to know which versions of python packages were used
        'runwsgi-content':
        (pathlib.Path(
      self.computer_partition_root_path
    ) / 'software_release' / 'bin' / 'runwsgi').read_text(),
      'mysql-show-variables':
        subprocess.check_output((
          pathlib.Path(self.getComputerPartitionPath('mariadb')) / 'bin' / 'mysql',
          '-e', 'show variables'), text=True),
      'erp5-git-describe':
        subprocess.check_output(
          ('git', 'describe', '--long'),
          cwd=pathlib.Path(self.computer_partition_root_path) / 'software_release' / 'parts' / 'erp5',
          text=True),
      'erp5-git-diff':
        subprocess.check_output(
          ('git', 'diff'),
          cwd=pathlib.Path(self.computer_partition_root_path) / 'software_release' / 'parts' / 'erp5',
          text=True),
      'slapos-software-release-git-describe':
        subprocess.check_output(
          ('git', 'describe', '--long'),
          cwd=pathlib.Path(self.getSoftwareURL()).parent,
          text=True),
      'slapos-software-release-git-diff':
        subprocess.check_output(
          ('git', 'diff'),
          cwd=pathlib.Path(self.getSoftwareURL()).parent,
          text=True),
    })

  def getDatabaseConnection(self):
    connection_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])
    db_url = urllib.parse.urlparse(connection_parameter_dict['mariadb-database-list'][0])
    self.assertEqual('mysql', db_url.scheme)

    self.assertTrue(db_url.path.startswith('/'))
    database_name = db_url.path[1:]
    return MySQLdb.connect(
      user=db_url.username,
      passwd=db_url.password,
      host=db_url.hostname,
      port=db_url.port,
      db=database_name,
      use_unicode=True,
      charset='utf8mb4',
    )

  def write_measurement(
      self, measurement: dict[str, typing.Union[str, float]]) -> None:
    json.dump(
      measurement,
      self.measurement_file,
    )
    self.measurement_file.write('\n')
    self.measurement_file.flush()

  def take_measurements(self, step: str) -> None:
    # Time for this iteration
    now = datetime.datetime.now()
    elapsed = now - self._previous
    self._previous = now

    # Memory usage of all zopes
    with self.slap.instance_supervisor_rpc as supervisor:
      zope_memory_info_list = [
        psutil.Process(process['pid']).memory_info()
        for process in supervisor.getAllProcessInfo()
        if process['name'].startswith('zope-') and process['pid']
      ]
    zope_total_rss = sum(mem.rss for mem in zope_memory_info_list)
    zope_count = len(zope_memory_info_list)

    # Database size
    if self.isNEO():
      root_fs_size = zeo_root_stats = 'N/A'
    else:
      root_fs = pathlib.Path(
       self.getComputerPartitionPath('zodb')) / 'srv' / 'zodb' / 'root.fs'
      root_fs_size = root_fs.stat().st_size

      # ZEO stats ( using ruok protocol https://github.com/zopefoundation/ZEO/commit/d5082536 )
      with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((self._ipv4_address, 2100))
        s.sendall(b'\x00\x00\x00\x04ruok')
        _ = s.recv(struct.unpack(">I", s.recv(4))[0])
        zeo_stats = json.loads(s.recv(struct.unpack(">I", s.recv(4))[0]))
      # we are supposed to have only one storage with name "root"
      zeo_root_stats = zeo_stats.pop('root')
      assert not zeo_stats

    # InnoDB/MariaDB metrics
    with contextlib.closing(self.getDatabaseConnection()) as cnx:
      cursor = cnx.cursor(MySQLdb.cursors.DictCursor)
      cursor.execute('SELECT * FROM information_schema.INNODB_METRICS')
      innodb_metrics = {r['NAME']: r['COUNT'] for r in cursor.fetchall()
                        if r.get('ENABLED') or r.get('STATUS') == 'enabled'}
      cursor.execute('SHOW GLOBAL STATUS')
      mariadb_metrics = {r['Variable_name']: r['Value'] for r in cursor.fetchall()}

    self.logger.info(
      "Measurements for %s (after %s): "
      "elapsed=%s zope_total_rss=%s / %s root_fs_size=%s",
      step,
      now - self._start,
      elapsed,
      zope_total_rss,
      zope_count,
      root_fs_size,
    )
    self.write_measurement(
      {
        'step': step,
        'step_duration_seconds': elapsed.total_seconds(),
        'step_duration': str(elapsed),
        'zope_total_rss': zope_total_rss,
        'zope_count': zope_count,
        'root_fs_size': root_fs_size,
        'zeo_stats': zeo_root_stats,
        'innodb_metrics': innodb_metrics,
        'mariadb_metrics': mariadb_metrics,
        'now': str(now),
      })

  def test(self) -> None:
    self._start = self._previous = datetime.datetime.now()

    with requests.Session() as session:
      ret = session.get(
        urllib.parse.urljoin(
          self.zope_base_url, 'ERP5Site_bootstrapScalabilityTest'),
        verify=False,
        params={'user_quantity:int': 1})
      if not ret.ok:
        self.logger.error(ret.text)
        if self._debug:
          breakpoint()
      ret.raise_for_status()
      self._waitForActivities(
        timeout=datetime.timedelta(hours=2).total_seconds())

      # XXX default reference generator for sale packing list cause
      # many conflict errors, disable it.
      self._addPythonScript(
        script_id='Delivery_generateReference',
        params='*args, **kw',
        body='context.setReference("no reference for benchmark")',
      )
      self.take_measurements("setup")

    # XXX now that we have installed business templates,
    # restart all zopes to workaround a bug with accessors not
    # working after some time (packing_list_line.getStartDate no longer
    # acquire from parent's sale packing list)
    with self.slap.instance_supervisor_rpc as supervisor:
      supervisor.stopAllProcesses()
      supervisor.startAllProcesses()
    self.slap.waitForInstance()
    self.take_measurements("restart")

    with requests.Session() as session:
      for i in range(100):
        for j in range(5):
          ret = session.get(
            self.create_sale_order_batch_url,
            verify=False,
            params={
              'random_seed': f'{i}.{j}',
              'order_count:int': '50',
            },
          )
          if not ret.ok:
            self.logger.error(ret.text)
            if self._debug:
              breakpoint()
          ret.raise_for_status()
        self._waitForActivities(
          timeout=datetime.timedelta(hours=2).total_seconds())
        self.take_measurements(f"iteration_{i+1:03}")

      # final measurements, take a "zodb analyze" snapshot
      if not self.isNEO():
        zodb_cmd = pathlib.Path(
          self.computer_partition_root_path
        ) / 'software_release' / 'bin' / 'zodb'
        root_fs = pathlib.Path(
          self.getComputerPartitionPath('zodb')) / 'srv' / 'zodb' / 'root.fs'
        self.write_measurement(
          {
            'zodb analyze':
            subprocess.check_output((zodb_cmd, 'analyze', root_fs), text=True)
          })

      # and a pt-query-digest for slow log
      pt_query_digest = pathlib.Path(
        self.getComputerPartitionPath(
          'mariadb')) / 'bin' / 'pt-query-digest'
      mariadb_slowquery_log = pathlib.Path(
        self.getComputerPartitionPath(
          'mariadb')) / 'var' / 'log' / 'mariadb_slowquery.log'
      mariadb_data = pathlib.Path(
        self.getComputerPartitionPath(
          'mariadb')) / 'srv' / 'mariadb'
      mariadb_data_size = sum(sum(os.path.getsize(os.path.join(root, f)) for f in files) \
        for root, dirs, files in os.walk(mariadb_data))
      mariadb_binlog_data = pathlib.Path(
        self.getComputerPartitionPath(
          'mariadb')) / 'srv' / 'backup' / 'mariadb-incremental'
      mariadb_binlog_data_size = sum(sum(os.path.getsize(os.path.join(root, f)) for f in files) \
        for root, dirs, files in os.walk(mariadb_binlog_data))
      self.write_measurement(
        {
          'pt-query-digest':
          subprocess.check_output(
            (pt_query_digest, mariadb_slowquery_log), text=True, errors='surrogateescape'),
          'data-size': mariadb_data_size,
          'binlog-data-size': mariadb_binlog_data_size,
        })
