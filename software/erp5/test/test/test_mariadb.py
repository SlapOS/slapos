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

import contextlib
import datetime
import glob
import gzip
import json
import lzma
import os
import subprocess
import time
import urllib.parse

import MySQLdb
import MySQLdb.connections

from slapos.testing.utils import CrontabMixin, getPromisePluginParameterDict

from . import ERP5InstanceTestCase, default, matrix, setUpModule

_ = setUpModule


class MariaDBTestCase(ERP5InstanceTestCase):
  """Base test case for mariadb tests.
  """
  __partition_reference__ = 'm'
  # We explicitly specify 'mariadb' as our software type here,
  # therefore we don't request ZODB. We therefore don't
  # need to run these tests with both NEO and ZEO mode,
  # it wouldn't make any difference.
  #   https://lab.nexedi.com/nexedi/slapos/blob/273037c8/stack/erp5/instance.cfg.in#L216-230
  __test_matrix__ = matrix((default,))

  @classmethod
  def getInstanceSoftwareType(cls):
    return "mariadb"

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    return {
        'tcpv4-port': 3306,
        'max-connection-count': 5,
        'long-query-time': 3,
        'max-slowqueries-threshold': 1,
        'slowest-query-threshold': 0.1,
        # XXX what is this ? should probably not be needed here
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        # XXX should probably not be needed here
        'computer-memory-percent-threshold': 100,
    }

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {'_': json.dumps(cls._getInstanceParameterDict())}

  def getDatabaseConnection(self, computer_partition=None) -> MySQLdb.connections.Connection:
    computer_partition = computer_partition or self.computer_partition
    connection_parameter_dict = json.loads(
        computer_partition.getConnectionParameterDict()['_'])
    db_url = urllib.parse.urlparse(connection_parameter_dict['database-list'][0])
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
        charset='utf8mb4'
    )

  @classmethod
  def getComputerPartitionPath(cls, computer_partition=None):
    computer_partition = computer_partition or cls.computer_partition
    return os.path.join(cls.slap._instance_root, computer_partition.getId())

  def getSocketDatabaseConnection(self, computer_partition=None) -> MySQLdb.connections.Connection:
    partition_path = self.getComputerPartitionPath(computer_partition)
    default_file = os.path.join(partition_path, 'etc', 'mariadb.cnf')
    return MySQLdb.connect(
        read_default_file = default_file,
        use_unicode=True,
        charset='utf8mb4',
        cursorclass=MySQLdb.cursors.DictCursor,
    )

class TestCrontabs(MariaDBTestCase, CrontabMixin):
  _save_instance_file_pattern_list = \
    MariaDBTestCase._save_instance_file_pattern_list + (
      '*/srv/backup/*',
    )

  def test_full_backup(self) -> None:
    self._executeCrontabAtDate('mariadb-backup', '2050-01-01')
    full_backup_file, = glob.glob(
      os.path.join(
        self.computer_partition_root_path,
        'srv',
        'backup',
        'mariadb-full',
        '205001010000??.sql.gz',
    ))

    with gzip.open(full_backup_file, 'rt') as dump:
      self.assertIn('CREATE TABLE', dump.read())

  def test_logrotate_and_slow_query_digest(self) -> None:
    # slow query digest needs to run after logrotate, since it operates on the rotated
    # file, so this tests both logrotate and slow query digest.

    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')

    # make two slow queries. We are using long-query-time=3, so the queries
    # must take more than 3 seconds to be logged.
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query("SELECT SLEEP(3.1)")
      cnx.store_result()
      cnx.query("SELECT SLEEP(3.2)")

    # slow query crontab depends on crontab for log rotation
    # to be executed first.
    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # this logrotate leaves the log for the day as non compressed
    rotated_log_file = os.path.join(
        self.computer_partition_root_path,
        'srv',
        'backup',
        'logrotate',
        'mariadb_slowquery.log-20500101',
    )
    self.assertTrue(os.path.exists(rotated_log_file))

    # then crontab to generate slow query report is executed
    self._executeCrontabAtDate('generate-mariadb-slow-query-report', '2050-01-01')
    # and it creates a report for the day
    slow_query_report = os.path.join(
        self.computer_partition_root_path,
        'srv',
        'monitor',
        'private',
        'slowquery_digest',
        'slowquery_digest.txt-2050-01-01.xz',
    )
    with lzma.open(slow_query_report, 'rt') as f:
      # this is the hash for our "select sleep(n)" slow query
      self.assertIn("ID 0xF9A57DD5A41825CA", f.read())

    # on next day execution of logrotate, log files are compressed
    self._executeCrontabAtDate('logrotate', '2050-01-02')
    self.assertTrue(os.path.exists(rotated_log_file + '.xz'))
    self.assertFalse(os.path.exists(rotated_log_file))

    # there's a promise checking that the threshold is not exceeded
    # and it reports a problem since we set a threshold of 1 slow query
    check_slow_query_promise_plugin = getPromisePluginParameterDict(
        os.path.join(
            self.computer_partition_root_path,
            'etc',
            'plugin',
            'check-slow-query-pt-digest-result.py',
        ))
    with self.assertRaises(subprocess.CalledProcessError) as error_context:
      subprocess.check_output(
        'faketime 2050-01-01 %s' % check_slow_query_promise_plugin['command'],
        text=True,
        shell=True)
    self.assertEqual(
      error_context.exception.output,
      "Threshold is lower than expected: \n"
      "Expected total queries : 1.0 and current is: 2\n"
      "Expected slowest query : 0.1 and current is: 3\n",
    )


class TestMariaDB(MariaDBTestCase):
  def test_utf8_collation(self) -> None:
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query(
          """
          CREATE TABLE test_utf8_collation (
            col1 CHAR(10)
          )
          """)

      cnx.store_result()
      cnx.query(
          """
          insert into test_utf8_collation values ("à"), ("あ")
          """)
      cnx.store_result()

      cnx.query(
          """
          select * from test_utf8_collation where col1 = "a"
          """)
      self.assertEqual((('à',),), cnx.store_result().fetch_row(maxrows=2))


class TestMroonga(MariaDBTestCase):
  def test_mroonga_plugin_loaded(self) -> None:
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query("show plugins")
      plugins = cnx.store_result().fetch_row(maxrows=1000)
      self.assertIn(
          ('Mroonga', 'ACTIVE', 'STORAGE ENGINE', 'ha_mroonga.so', 'GPL'),
          plugins)

  def test_mroonga_normalize_udf(self) -> None:
    # example from https://mroonga.org/docs/reference/udf/mroonga_normalize.html#usage
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query(
          """
          SELECT mroonga_normalize("ABCDあぃうぇ㍑")
          """)
      # XXX this is returned as bytes by mroonga/mariadb (this might be a bug)
      self.assertEqual((('abcdあぃうぇリットル'.encode(),),),
                       cnx.store_result().fetch_row(maxrows=2))

      if 0:
        # this example fail with:
        # OperationalError: (1123, "Can't initialize function 'mroonga_normalize'; mroonga_normalize(): nonexistent normalizer NormalizerMySQLUnicodeCIExceptKanaCI")
        # same error on mroonga "official" docker images using mysql
        # https://hub.docker.com/layers/groonga/mroonga/latest/images/sha256-e5a979801c95544ca3a1228d2c4d819820850e0162649553f2e94850e5e1c988?context=explore
        # so it's probably OK to ignore
        cnx.query(
            """
            SELECT mroonga_normalize("aBｃＤあぃウェ㍑", "NormalizerMySQLUnicodeCIExceptKanaCIKanaWithVoicedSoundMark")
            """)
        self.assertEqual((('ABCDあぃうぇ㍑'.encode(),),),
                         cnx.store_result().fetch_row(maxrows=2))

  def test_mroonga_full_text_normalizer(self) -> None:
    # example from https://mroonga.org//docs/tutorial/storage.html#how-to-specify-the-normalizer
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):

      cnx.query("SET NAMES utf8")
      cnx.store_result()
      cnx.query(
          """
          CREATE TABLE diaries (
            day DATE PRIMARY KEY,
            content VARCHAR(64) NOT NULL,
            FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto"'
          ) Engine=Mroonga DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
          """)
      cnx.store_result()
      cnx.query(
          """INSERT INTO diaries VALUES ("2013-04-23", "ブラックコーヒーを飲んだ。")""")
      cnx.store_result()
      cnx.query(
          """
          SELECT *
            FROM diaries
           WHERE MATCH (content) AGAINST ("+ふらつく" IN BOOLEAN MODE)
          """)
      self.assertEqual((), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          SELECT *
            FROM diaries
           WHERE MATCH (content) AGAINST ("+ﾌﾞﾗｯｸ" IN BOOLEAN MODE)
          """)
      self.assertEqual(
          ((datetime.date(2013, 4, 23), 'ブラックコーヒーを飲んだ。'),),
          cnx.store_result().fetch_row(maxrows=2),
      )

  def test_mroonga_full_text_normalizer_TokenBigramSplitSymbolAlphaDigit(self) -> None:
    # Similar to as ERP5's testI18NSearch with erp5_full_text_mroonga_catalog
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query(
          """
            CREATE TABLE `full_text` (
              `uid` BIGINT UNSIGNED NOT NULL,
              `SearchableText` MEDIUMTEXT,
              PRIMARY KEY  (`uid`),
              FULLTEXT `SearchableText` (`SearchableText`) COMMENT 'parser "TokenBigramSplitSymbolAlphaDigit"'
            ) ENGINE=mroonga
          """)
      cnx.store_result()
      cnx.query(
          """
            INSERT INTO full_text VALUES
            (1, "Gabriel Fauré Quick brown fox jumps over the lazy dog"),
            (2, "武者小路 実篤 Slow white fox jumps over the diligent dog."),
            (3, "( - + )")""")
      cnx.store_result()
      cnx.query(
          """
          SELECT uid
            FROM full_text
            WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ Faure' IN BOOLEAN MODE)
          """)
      self.assertEqual(((1,),), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          SELECT uid
            FROM full_text
            WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ 武者' IN BOOLEAN MODE)
          """)
      self.assertEqual(((2,),), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          SELECT uid
            FROM full_text
            WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ +quick +fox +dog' IN BOOLEAN MODE)
          """)
      self.assertEqual(((1,),), cnx.store_result().fetch_row(maxrows=2))

  def test_mroonga_full_text_stem(self) -> None:
    # example from https://mroonga.org//docs/tutorial/storage.html#how-to-specify-the-token-filters
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query("SELECT mroonga_command('register token_filters/stem')")
      self.assertEqual(((b'true',),), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          CREATE TABLE memos (
            id INT NOT NULL PRIMARY KEY,
            content TEXT NOT NULL,
            FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto", token_filters "TokenFilterStem"'
          ) Engine=Mroonga DEFAULT CHARSET=utf8
          """)
      cnx.store_result()
      cnx.query(
          """INSERT INTO memos VALUES (1, "I develop Groonga"), (2, "I'm developing Groonga"), (3, "I developed Groonga")"""
      )
      cnx.store_result()
      cnx.query(
          """
          SELECT *
            FROM memos
           WHERE MATCH (content) AGAINST ("+develops" IN BOOLEAN MODE)
          """)
      self.assertEqual([
          (1, "I develop Groonga"),
          (2, "I'm developing Groonga"),
          (3, "I developed Groonga"),
      ], list(sorted(cnx.store_result().fetch_row(maxrows=4))))


class TestMariaDBReplication(MariaDBTestCase):
  force_bootstrap = False

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    return {
        'tcpv4-port': 3306,
        'max-slowqueries-threshold': 1,
        'slowest-query-threshold': 0.1,
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        'computer-memory-percent-threshold': 100,
    }

  @classmethod
  def requestDefaultInstance(cls, state="started"):
    software_url = cls.getSoftwareURL()
    software_type = cls.getInstanceSoftwareType()
    cls.logger.info("Requesting Mariadb Primary")
    cls._primary_parameter_dict=cls.getInstanceParameterDict()
    for i in range(2):
      primary = cls.slap.request(
        software_release=software_url,
        software_type=software_type,
        partition_reference='primary',
        partition_parameter_kw=cls._primary_parameter_dict,
        state=state,
      )
      if i:
        break
      cls.waitForInstance()
    cls.primary = primary
    primary_connectors = json.loads(primary.getConnectionParameterDict()['_'])
    primary_url = primary_connectors['replication-primary-url']
    replication_dict = {'primary-url': primary_url}
    if cls.force_bootstrap:
      # Force the primary to generate a backup for bootstrap,
      # as it may not have a backup ready yet.
      # Note: bootstrap is not needed because the primary is recent.
      primary_path = cls.getComputerPartitionPath(primary)
      backupscript = os.path.join(primary_path, 'bin', 'mariadb-backup-script')
      subprocess.check_output([backupscript])
      bootstrap_url = primary_connectors['replication-bootstrap-url']
      replication_dict['bootstrap-url'] = bootstrap_url
    replica_parameter_dict = cls._getInstanceParameterDict()
    replica_parameter_dict['tcpv4-port'] += 20
    replica_parameter_dict['replication'] = replication_dict
    cls._instance_parameter_dict = {'_': json.dumps(replica_parameter_dict)}
    cls.logger.info("Requesting Mariadb Replica")
    cls.replica = replica = cls.slap.request(
      software_release=software_url,
      software_type=software_type,
      partition_reference='replica',
      partition_parameter_kw=cls._instance_parameter_dict,
      state=state,
    )
    return replica

  def getReplicaStatus(self):
    cnx = self.getSocketDatabaseConnection(self.replica)
    with contextlib.closing(cnx):
      cursor = cnx.cursor()
      cursor.execute("SHOW SLAVE STATUS")
      return cursor.fetchone()

  def test_replica_state(self):
    replica_status = self.getReplicaStatus()
    try:
      self.assertTrue(replica_status)
      self.assertIsInstance(replica_status['Seconds_Behind_Master'], int)
    except (AssertionError, KeyError):
      self.logger.error('Replica is in bad state:\n%r', replica_status)
      raise

  def test_data_replication(self):
    cnx = self.getDatabaseConnection(self.primary)
    with contextlib.closing(cnx):
      cursor = cnx.cursor()
      cursor.execute(
          """
          CREATE TABLE test_replication (
            col1 CHAR(10)
          )
          """)
      cursor.execute(
          """
          insert into test_replication values ("a"), ("b")
          """)
      cnx.commit()
    cnx = self.getDatabaseConnection(self.primary)
    with contextlib.closing(cnx):
      cursor = cnx.cursor()
      cursor.execute(
          """
          select * from test_replication
          """)
      self.assertEqual((('a',), ('b',)), cursor.fetchall())
    time.sleep(2)
    for i in range(7):
      if self.getReplicaStatus()['Seconds_Behind_Master'] == 0:
        break
      time.sleep((i + 1) ** 2)
    cnx = self.getDatabaseConnection(self.replica)
    with contextlib.closing(cnx):
      cursor = cnx.cursor()
      cursor.execute(
          """
          select * from test_replication
          """)
      self.assertEqual((('a',), ('b',)), cursor.fetchall())


class TestMariaDBReplicationWithBootstrap(TestMariaDBReplication):
  force_bootstrap = True
