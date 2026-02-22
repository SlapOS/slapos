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
import tempfile
import unittest
import urllib.parse
import warnings

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import inotify_simple
import pexpect
import pymysql
import pymysql.cursors
import requests

from slapos.testing.utils import CrontabMixin, getPromisePluginParameterDict
from slapos.slap.standalone import SlapOSNodeCommandError
from slapos.slap.slap import ComputerPartition


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

  def getDatabaseConnection(self, computer_partition=None) -> pymysql.connections.Connection:
    computer_partition = computer_partition or self.computer_partition
    connection_parameter_dict = json.loads(
        computer_partition.getConnectionParameterDict()['_'])
    db_url = urllib.parse.urlparse(connection_parameter_dict['database-list'][0])
    self.assertEqual('mysql', db_url.scheme)
    self.assertTrue(db_url.path.startswith('/'))
    database_name = db_url.path[1:]
    return pymysql.connect(
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

  def getSocketDatabaseConnection(self, computer_partition=None) -> pymysql.connections.Connection:
    partition_path = self.getComputerPartitionPath(computer_partition)
    default_file = os.path.join(partition_path, 'etc', 'mariadb.cnf')
    return pymysql.connect(
        read_default_file=default_file,
        use_unicode=True,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )

  @classmethod
  def waitForCaucased(cls, instance, timeout):
    caucased = instance.getInstanceParameterDict().get('caucased', {})
    if not caucased.get('enabled', True):
      return
    partition_path = cls.getComputerPartitionPath(instance)
    watch_dir = os.path.join(partition_path, 'etc', 'mariadb-ssl')
    ca_path = os.path.join(watch_dir, 'mariadb-ca.pem')
    inotify = inotify_simple.INotify()
    wd = inotify.add_watch(watch_dir, inotify_simple.flags.CREATE)
    now = time.time()
    deadline = now + timeout
    while True:
      if timeout < 0 or os.path.exists(ca_path):
        return
      for event in inotify.read(timeout): # read all events
        pass
      now = time.time()
      timeout = deadline - now

  @classmethod
  def waitForInstance(cls) -> None:
    # Caucase may take a bit more time to grant certificates
    # Instead of increasing instance_max_retry, lets just wait
    try:
      cls.slap.waitForInstance(max_retry=cls.instance_max_retry - 1)
    except SlapOSNodeCommandError:
      instance = cls.getComputerPartition(cls.default_partition_reference)
      cls.waitForCaucased(instance, 60)
      cls.slap.waitForInstance(debug=cls._debug)


class TestCrontabs(MariaDBTestCase, CrontabMixin):
  _save_instance_file_pattern_list = \
    MariaDBTestCase._save_instance_file_pattern_list + (
      '*/srv/backup/*',
    )

  def test_full_backup(self) -> None:
    self._executeCrontabAtDate('mariadb-dump', '2050-01-01')
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

  def test_full_mariabackup(self) -> None:
    self._executeCrontabAtDate('mariabackup', '2050-01-01')
    self.assertTrue(glob.glob(
      os.path.join(
        self.computer_partition_root_path,
        'srv',
        'backup',
        'mariabackup',
        '205001010000??.full.xb.zstd',
    )))

  def test_logrotate_and_slow_query_digest(self) -> None:
    # slow query digest needs to run after logrotate, since it operates on the rotated
    # file, so this tests both logrotate and slow query digest.

    # run logrotate a first time so that it create state files
    self._executeCrontabAtDate('logrotate', '2000-01-01')

    # make two slow queries. We are using long-query-time=3, so the queries
    # must take more than 3 seconds to be logged.
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute("SELECT SLEEP(3.1)")
        cursor.execute("SELECT SLEEP(3.2)")

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
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE test_utf8_collation (
              col1 CHAR(10)
            )
            """)

        cursor.execute(
            """
            insert into test_utf8_collation values ("à"), ("あ")
            """)

        cursor.execute(
            """
            select * from test_utf8_collation where col1 = "a"
            """)
        self.assertEqual((('à',),), tuple(cursor.fetchall()))

  def test_timezone(self) -> None:
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute("SELECT CONVERT_TZ('2001-01-01', 'UTC', 'Europe/Paris')")
        self.assertEqual(
          ((datetime.datetime(2001, 1, 1, 1, 0),),),
          tuple(cursor.fetchall()),
        )


class TestMariaDBTLS(MariaDBTestCase):
  _client_cert_crt: str|None = None

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    subject = x509.Name(
      [x509.NameAttribute(NameOID.COMMON_NAME, cls.__name__)])
    key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
      backend=default_backend(),
    )
    with tempfile.NamedTemporaryFile(delete=False) as f:
      f.write(
        key.private_bytes(
          serialization.Encoding.PEM,
          serialization.PrivateFormat.PKCS8,
          serialization.NoEncryption()))
    cls._client_cert_key = f.name
    cls.addClassCleanup(os.unlink, cls._client_cert_key)

    csr = x509.CertificateSigningRequestBuilder(
    ).subject_name(
      subject
    ).sign(
      key,
      hashes.SHA256(),
      default_backend(),
    )
    cls._client_csr_txt = csr.public_bytes(serialization.Encoding.PEM).decode()

    parameter_dict = super()._getInstanceParameterDict()
    parameter_dict.setdefault('caucased', {})['csr-to-sign'] = cls._client_csr_txt
    return parameter_dict

  def _run_service(self, service_name:str, expected_output:str, when='now') -> None:
    """execute a service from etc/run/ and wait for expected output.
    """
    service = self.computer_partition_root_path / 'etc' / 'run' / service_name
    process = pexpect.spawnu(f"faketime {when} {service}")
    logger = self.logger
    class DebugLogFile:
      def write(self, msg):
        logger.info("output from %s: %s", service_name, msg)
      def flush(self):
        pass
    process.logfile = DebugLogFile()
    process.expect(expected_output)
    process.terminate()
    process.wait()

  def _client_cert(self) -> tuple[str, str]:
    if self._client_cert_crt is None:
      # get the certificate from caucase
      connection_parameter_dict = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])
      caucased_base_url = connection_parameter_dict['caucased-url']
      resp = requests.put(
        f"{caucased_base_url}/cas/csr", data=self._client_csr_txt)
      resp.raise_for_status()
      csr_id = resp.headers['Location']
      self._run_service('caucase-sign-csr', 'end of signed service CSRs')
      resp = requests.get(f"{caucased_base_url}/cas/crt/{csr_id}")
      resp.raise_for_status()
      with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(resp.text.encode())
      self._client_cert_crt = f.name
      self.addClassCleanup(os.unlink, self._client_cert_crt)
    return self._client_cert_crt, self._client_cert_key

  def getReplicationUserDatabaseConnection(self, ssl:dict | None) -> pymysql.connections.Connection:
    connection_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])
    db_url = urllib.parse.urlparse(
      connection_parameter_dict['replication-primary-url'])
    self.assertEqual('mysql', db_url.scheme)
    return pymysql.connect(
      user=db_url.username,
      passwd=db_url.password,
      host=db_url.hostname,
      port=db_url.port,
      use_unicode=True,
      ssl=ssl,
    )

  def test_replication_user_require_x509(self):
    with self.assertRaisesRegex(pymysql.err.OperationalError, 'SSL is required'):
      self.getReplicationUserDatabaseConnection(ssl=None).close()

    ssl = {'ca': str(self.computer_partition_root_path / 'etc' / 'mariadb-ssl' / 'mariadb-ca.pem')}
    with self.assertRaises(pymysql.err.OperationalError):
      self.getReplicationUserDatabaseConnection(ssl=ssl).close()

    ssl['cert'], ssl['key'] = self._client_cert()
    self.getReplicationUserDatabaseConnection(ssl=ssl).close()

  def test_proxysql_server_certificate_renewal(self):
    ssl = {'ca': str(self.computer_partition_root_path / 'etc' / 'mariadb-ssl' / 'mariadb-ca.pem')}
    ssl['cert'], ssl['key'] = self._client_cert()

    with contextlib.closing(self.getReplicationUserDatabaseConnection(ssl)) as cnx:
      cert_before = cnx._sock.getpeercert()
    self._run_service('caucase-mariadb-updater', '(?s)Renewing.*Next wake-up', '+63days')
    with contextlib.closing(self.getReplicationUserDatabaseConnection(ssl)) as cnx:
      cert_after = cnx._sock.getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])

  def test_mariadbackup_url_certificate_renewal(self):
    connection_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])
    mariabackup_url = connection_parameter_dict['replication-mariabackup-url']

    def _getpeercert():
      # XXX low level way to get the server certificate
      with requests.Session() as session:
        resp = session.get(
          mariabackup_url,
          verify=self.computer_partition_root_path / 'etc' / 'mariadb-ssl' / 'mariadb-ca.pem',
          cert=self._client_cert(),
        )
        resp.raise_for_status()
        with contextlib.closing(resp.raw._pool.pool.get()) as cnx:
          return cnx.sock._sslobj.getpeercert()

    cert_before = _getpeercert()
    self._run_service('caucase-mariadb-updater', '(?s)Renewing.*Next wake-up', '+63days')
    cert_after = _getpeercert()
    self.assertNotEqual(cert_before['notAfter'], cert_after['notAfter'])


class TestMroonga(MariaDBTestCase):
  def test_mroonga_plugin_loaded(self) -> None:
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute("show plugins")
        plugins = tuple(cursor.fetchall())
        self.assertIn(
            ('Mroonga', 'ACTIVE', 'STORAGE ENGINE', 'ha_mroonga.so', 'GPL'),
            plugins)

  def test_mroonga_normalize_udf(self) -> None:
    # example from https://mroonga.org/docs/reference/udf/mroonga_normalize.html#usage
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            SELECT mroonga_normalize("ABCDあぃうぇ㍑")
            """)
        # XXX this is returned as bytes by mroonga/mariadb (this might be a bug)
        self.assertEqual((('abcdあぃうぇリットル'.encode(),),),
                         tuple(cursor.fetchall()))

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
      with cnx.cursor() as cursor:
        cursor.execute("SET NAMES utf8")
        cursor.execute(
            """
            CREATE TABLE diaries (
              day DATE PRIMARY KEY,
              content VARCHAR(64) NOT NULL,
              FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto"'
            ) Engine=Mroonga DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
            """)
        cursor.execute(
            """INSERT INTO diaries VALUES ("2013-04-23", "ブラックコーヒーを飲んだ。")""")
        cursor.execute(
            """
            SELECT *
              FROM diaries
             WHERE MATCH (content) AGAINST ("+ふらつく" IN BOOLEAN MODE)
            """)
        self.assertEqual((), tuple(cursor.fetchall()))
        cursor.execute(
            """
            SELECT *
              FROM diaries
             WHERE MATCH (content) AGAINST ("+ﾌﾞﾗｯｸ" IN BOOLEAN MODE)
            """)
        self.assertEqual(
            ((datetime.date(2013, 4, 23), 'ブラックコーヒーを飲んだ。'),),
            tuple(cursor.fetchall()),
        )

  def test_mroonga_full_text_normalizer_TokenBigramSplitSymbolAlphaDigit(self) -> None:
    # Similar to as ERP5's testI18NSearch with erp5_full_text_mroonga_catalog
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
              CREATE TABLE `full_text` (
                `uid` BIGINT UNSIGNED NOT NULL,
                `SearchableText` MEDIUMTEXT,
                PRIMARY KEY  (`uid`),
                FULLTEXT `SearchableText` (`SearchableText`) COMMENT 'parser "TokenBigramSplitSymbolAlphaDigit"'
              ) ENGINE=mroonga
            """)
        cursor.execute(
            """
              INSERT INTO full_text VALUES
              (1, "Gabriel Fauré Quick brown fox jumps over the lazy dog"),
              (2, "武者小路 実篤 Slow white fox jumps over the diligent dog."),
              (3, "( - + )")""")
        cursor.execute(
            """
            SELECT uid
              FROM full_text
              WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ Faure' IN BOOLEAN MODE)
            """)
        self.assertEqual(((1,),), tuple(cursor.fetchall()))
        cursor.execute(
            """
            SELECT uid
              FROM full_text
              WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ 武者' IN BOOLEAN MODE)
            """)
        self.assertEqual(((2,),), tuple(cursor.fetchall()))
        cursor.execute(
            """
            SELECT uid
              FROM full_text
              WHERE MATCH (`full_text`.`SearchableText`) AGAINST ('*D+ +quick +fox +dog' IN BOOLEAN MODE)
            """)
        self.assertEqual(((1,),), tuple(cursor.fetchall()))

  def test_mroonga_full_text_stem(self) -> None:
    # example from https://mroonga.org//docs/tutorial/storage.html#how-to-specify-the-token-filters
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute("SELECT mroonga_command('register token_filters/stem')")
        self.assertEqual(((b'true',),), tuple(cursor.fetchall()))
        cursor.execute(
            """
            CREATE TABLE memos (
              id INT NOT NULL PRIMARY KEY,
              content TEXT NOT NULL,
              FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto", token_filters "TokenFilterStem"'
            ) Engine=Mroonga DEFAULT CHARSET=utf8
            """)
        cursor.execute(
            """INSERT INTO memos VALUES (1, "I develop Groonga"), (2, "I'm developing Groonga"), (3, "I developed Groonga")"""
        )
        cursor.execute(
            """
            SELECT *
              FROM memos
             WHERE MATCH (content) AGAINST ("+develops" IN BOOLEAN MODE)
            """)
        self.assertEqual([
            (1, "I develop Groonga"),
            (2, "I'm developing Groonga"),
            (3, "I developed Groonga"),
        ], list(sorted(cursor.fetchall())))



class MariaDBReplicationTestCase(MariaDBTestCase):
  # Map instance names to unique ports
  PORT_MAP = {}

  # Initial port value
  PORT = 3306

  # No default instance, requests happen in test
  request_instance = False

  @classmethod
  def waitForMariadb(cls, instance=None, max_retry=None, strict=True):
    max_retry = 10 if max_retry is None else max_retry
    try:
      cls.slap.waitForInstance(max_retry=max(max_retry - 1, 0))
    except SlapOSNodeCommandError:
      if instance is not None:
        cls.waitForCaucased(instance, 60)
    else:
      return
    try:
      cls.slap.waitForInstance(max_retry=0, debug=strict and cls._debug)
    except SlapOSNodeCommandError:
      if strict:
        raise

  @classmethod
  def waitForReport(cls, max_retry=None, strict=True):
    max_retry = 10 if max_retry is None else max_retry
    try:
      cls.slap.waitForReport(max_retry=max_retry, debug=strict and cls._debug)
    except SlapOSNodeCommandError:
      if strict:
        raise

  @classmethod
  def getMariadbParameterDict(cls) -> dict:
    return {
        'max-slowqueries-threshold': 1,
        'slowest-query-threshold': 0.1,
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        'computer-memory-percent-threshold': 100,
    }

  @classmethod
  def updateDict(cls, d, **kw):
    for k, v in kw.items():
      default = d.get(k)
      if isinstance(default, dict):
        cls.updateDict(default, **v)
      else:
        d[k] = v
    return d

  @classmethod
  def requestMariadb(cls, name, **kw):
    state = kw.pop('state', 'started')
    strict = kw.pop('strict', True)
    max_retry = kw.pop('max_retry', None)
    # caucased parameters
    caucased = kw.pop('caucased', True)
    if isinstance(caucased, ComputerPartition):
      downstream = json.loads(caucased.getConnectionParameterDict()['_'])
      caucased = {'csr-to-sign': downstream['caucased-csr-to-sign']}
      cls.updateDict(kw, caucased=caucased)
    elif caucased is False:
      caucased = {'enable': False}
      cls.updateDict(kw, caucased=caucased)
    elif isinstance(caucased, dict):
      cls.updateDict(kw, caucased=caucased)
    # reverse proxy parameters
    ipv6 = kw.pop('ipv6', True)
    if not ipv6:
      cls.updateDict(kw, **{'ipv6-reverse-proxy': {'enable': False}})
      replication = kw.get('replication')
      if replication:
        replication['replicate-with-tls'] = False
    # unique port
    port = cls.PORT_MAP.setdefault(name, cls.PORT + 10 * len(cls.PORT_MAP))
    parameter_dict = cls.getMariadbParameterDict()
    parameter_dict['tcpv4-port'] = port
    # apply kwarg updates
    parameter_dict = cls.updateDict(parameter_dict, **kw)
    cls.logger.debug("Requesting mariadb %s with %r" %(name, parameter_dict))
    for i in range(2):
      mariadb = cls.slap.request(
        software_release=cls.getSoftwareURL(),
        software_type=cls.getInstanceSoftwareType(),
        partition_reference=name,
        partition_parameter_kw={'_': json.dumps(parameter_dict)},
        state=state,
      )
      # request, process partition and re-request
      if not i:
        cls.waitForMariadb(mariadb, max_retry, strict)
    return mariadb

  @classmethod
  def requestPrimary(cls, name='primary', **kw):
    return cls.requestMariadb(name, **kw)

  @classmethod
  def requestReplica(cls, primary, name='replica', **kw):
    bootstrap = kw.pop('bootstrap', None)
    upstream = json.loads(primary.getConnectionParameterDict()['_'])
    replication = {'upstream-mariadb-url': upstream['replication-primary-url']}
    if bootstrap:
      replication['upstream-' + bootstrap] = upstream['replication-' + bootstrap]
    caucased_url = upstream['caucased-url']
    if caucased_url:
      replication['upstream-caucased-url'] = caucased_url
    cls.updateDict(kw, replication=replication)
    return cls.requestMariadb(name, **kw)

  @classmethod
  def runBackup(cls, mariadb, script='mariabackup-script'):
    subprocess.check_output(
      (os.path.join(cls.getComputerPartitionPath(mariadb), 'bin', script),),
      stderr=subprocess.STDOUT,
    )

  @classmethod
  def runTakoever(cls, mariadb):
    script = 'mariadb-replica-become-primary'
    subprocess.check_output(
      (os.path.join(cls.getComputerPartitionPath(mariadb), 'bin', script),),
      stderr=subprocess.STDOUT,
    )

  @classmethod
  def runSlapos(cls, command, timestamp=None):
    args = []
    if timestamp:
      args.extend(('faketime', '-f', timestamp))
    args.append(cls.slap._slapos_bin)
    args.extend(command.split())
    args.extend(('--cfg', cls.slap._slapos_config))
    return subprocess.check_output(args, stderr=subprocess.STDOUT)

  @classmethod
  def getPromiseStatus(cls, mariadb, promise='mariadb_replication'):
    path = os.path.join(
      cls.getComputerPartitionPath(mariadb),
      '.slapgrid', 'promise', 'result',
      promise + '.status.json'
    )
    with open(path) as f:
      status = json.load(f)
    return status

  @classmethod
  def getPromiseDigest(cls, mariadb, promise='mariadb_replication'):
    result = cls.getPromiseStatus(mariadb, promise)['result']
    return not result['failed'], result['message']

  @classmethod
  def destroyMariaDBInstances(cls):
    for name in cls.PORT_MAP:
      cls.slap.request(
        software_release=cls.getSoftwareURL(),
        software_type=cls.getInstanceSoftwareType(),
        partition_reference=name,
        partition_parameter_kw={'_': json.dumps({})},
        state='destroyed',
      )
    for _ in range(3):
      cls.waitForMariadb(strict=False)
      cls.waitForReport(strict=False)
    cls.PORT_MAP.clear()

  @classmethod
  def tearDownClass(cls):
    cls.destroyMariaDBInstances()
    super(MariaDBReplicationTestCase, cls).tearDownClass()

  def getReplicaStatus(self, replica):
    cnx = self.getSocketDatabaseConnection(replica)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute("SHOW SLAVE STATUS")
        return cursor.fetchone()

  def checkReplicaState(self, replica):
    replica_status = self.getReplicaStatus(replica)
    try:
      self.assertTrue(replica_status)
      seconds_behind_master = replica_status['Seconds_Behind_Master']
      self.assertIsInstance(seconds_behind_master, int)
      return seconds_behind_master
    except (AssertionError, KeyError):
      self.fail('Replica is in bad state:\n%r', replica_status)

  def checkDataReplication(self, primary, *replicas):
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE test_replication (
              col1 CHAR(10)
            )
            """)
        cursor.execute(
            """
            INSERT INTO test_replication VALUES ("a"), ("b")
            """)
        cnx.commit()
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM test_replication
            """)
        self.assertEqual((('a',), ('b',)), cursor.fetchall())
    time.sleep(2)
    for replica in replicas:
      for i in range(7):
        if self.checkReplicaState(replica) == 0:
          break
        time.sleep((i + 1) ** 2)
      cnx = self.getDatabaseConnection(replica)
      with contextlib.closing(cnx):
        with cnx.cursor() as cursor:
          cursor.execute(
              """
              SELECT * FROM test_replication
              """)
          self.assertEqual((('a',), ('b',)), cursor.fetchall())


class TestMariaDBReplication(MariaDBReplicationTestCase):
  def checkReplication(self, caucased=True, bootstrap=None, backups=1, **kw):
    kw.setdefault('ipv6', True)
    # Request primary Mariadb
    primary = self.requestPrimary(caucased=caucased, **kw)
    connectors = json.loads(primary.getConnectionParameterDict()['_'])
    if caucased:
      # Assert bootstrap http server requires mTLS over IPv6
      bootstrap_url = connectors['replication-mariabackup-url']
      with warnings.catch_warnings():
        warnings.simplefilter("ignore") # verify=False triggers warning
        self.assertRaises(
          requests.exceptions.SSLError,
          requests.get,
          bootstrap_url,
          verify=False,
        )
    else:
      # Assert disabling caucase disables the HTTP backup due to lack of mTLS
      self.assertEqual(connectors['caucased-url'], '')
      self.assertEqual(connectors['replication-mariabackup-url'], '')
      self.assertEqual(connectors['replication-bootstrap-url'], '')
    # Generate backups on primary
    if bootstrap:
      script = 'mariabackup' if 'mariabackup' in bootstrap else 'mariadb-dump'
      for _ in range(backups):
        self.runBackup(primary, script + '-script')
    # Request replica Mariadb
    replica = self.requestReplica(
      primary,
      strict=not caucased, # allow promises to fail
      bootstrap=bootstrap,
      **kw,
    )
    # Let primary sign replica CSR
    # This asserts that all partitions, including replica, converge
    if caucased:
      primary = self.requestPrimary(caucased=replica, **kw)
    # Check (primary --> replica) replication
    self.checkReplicaState(replica)
    self.checkDataReplication(primary, replica)

  def tearDown(self):
    self.destroyMariaDBInstances()

  def test_caucase_no_bootstrap(self):
    # Check disabled mysql-dump & mariabackup along the way
    self.checkReplication(
      bootstrap=None,
      backup={
        'logical': {'enable': False},
        'physical': {'enable': False},
      },
    )

  def test_caucase_bootstrap_from_dump(self):
    self.checkReplication(bootstrap='bootstrap-url')

  def test_caucase_bootstrap_from_mariabackup(self):
    self.checkReplication(bootstrap='mariabackup-url')

  def test_caucase_bootstrap_from_mariabackup_incremental(self):
    self.checkReplication(bootstrap='mariabackup-url', backups=3)

  def test_no_ssl_ipv4_no_bootstrap(self):
    self.checkReplication(caucase=False, bootstrap=None)

  def test_caucase_ipv4_no_bootstrap(self):
    self.checkReplication(ipv6=False, bootstrap=None)

  def test_caucase_ipv4_bootstrap_from_dump(self):
    self.checkReplication(ipv6=False, bootstrap='bootstrap-url')

  def test_caucase_ipv4_bootstrap_from_mariabackup(self):
    self.checkReplication(ipv6=False, bootstrap='mariabackup-url')

  def test_caucase_ipv4_bootstrap_from_mariabackup_incremental(self):
    self.checkReplication(ipv6=False, bootstrap='mariabackup-url', backups=3)

  def test_takeover(self):
    # Request primary Mariadb
    primary = self.requestPrimary(caucased=False)
    # Request replica Mariadb
    replica = self.requestReplica(primary, caucased=False)
    # Check (primary --> replica) replication
    self.checkReplicaState(replica)
    self.checkDataReplication(primary, replica)
    ok, _ = self.getPromiseDigest(replica)
    self.assertTrue(ok)
    # Takeover replica
    self.runTakoever(replica)
    # Check replication promise now fails
    self.runSlapos('node instance', '+120s')
    ok, message = self.getPromiseDigest(replica)
    self.assertFalse(ok)
    self.assertIn("Mariadb is not in replica mode", message)
    # Check replication promise does not bang
    self.waitForMariadb() # if a bang occured, this would raise
    # Update replica parameters into a primary, fixing the promise
    self.requestPrimary(name='replica', caucased=False)

  def test_mariabackup_mroonga_backup_and_incremental_backup(self):
    # Request primary Mariadb
    primary = self.requestPrimary(caucased=False)
    # Add fulltext data powered by Mroonga
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE test_mroonga_replication (
              `uid` BIGINT UNSIGNED NOT NULL,
              `SearchableText` MEDIUMTEXT,
              PRIMARY KEY  (`uid`),
              FULLTEXT `SearchableText` (`SearchableText`) COMMENT 'parser "TokenBigramSplitSymbolAlphaDigit"'
            ) Engine=Mroonga
            """)
        cursor.execute(
            """INSERT INTO test_mroonga_replication VALUES (1, "Hello")""")
        cnx.commit()
    # Generate mariabackup in primary
    self.runBackup(primary, 'mariabackup-script')
    # Add data in incremental mariabackup
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """REPLACE INTO test_mroonga_replication VALUES (1, "Hi")""")
        cursor.execute(
            """INSERT INTO test_mroonga_replication VALUES (2, "What's up?")""")
        cnx.commit()
    # Generate incremental mariabackup in primary
    self.runBackup(primary, 'mariabackup-script')
    # Request replica Mariadb
    replica = self.requestReplica(
      primary,
      caucased=False,
      bootstrap='mariabackup-url',
    )
    self.checkReplicaState(replica)
    self.checkDataReplication(primary, replica)
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """REPLACE INTO test_mroonga_replication VALUES (1, "Hey")""")
        cursor.execute(
            """INSERT INTO test_mroonga_replication VALUES (3, "Bye")""")
        cnx.commit()
        cnx.commit()
    time.sleep(2)
    for i in range(7):
      if self.checkReplicaState(replica) == 0:
        break
      time.sleep((i + 1) ** 2)
    cnx = self.getDatabaseConnection(replica)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM test_mroonga_replication
            """)
        self.assertEqual(
          ((1, "Hey"),(2, "What's up?"),(3, "Bye"),),
          cursor.fetchall()
        )


class TestMariaDBExternalCaucased(MariaDBReplicationTestCase):
  def test(self):
    # Request a Mariadb used only for its caucased server
    caucased = self.requestPrimary(name='caucased')
    external_caucased_url = json.loads(
      caucased.getConnectionParameterDict()['_']
    )['caucased-url']
    # Request a Mariadb using the first mariadb's caucased as external caucased
    primary = self.requestPrimary(
      caucased={'external-caucased-url': external_caucased_url},
      strict=False,
    )
    # Locate primary's mariadb csr to let the external caucased sign it
    with open(os.path.join(
        self.getComputerPartitionPath(primary),
        'srv', 'caucase', 'mariadb', 'good.csr.pem'), 'rb') as f:
      csr = f.read().decode('ascii')
    # Let external caucased sign primary's mariadb csr
    # This asserts that all partitions, including primary, converge
    self.requestPrimary(name='caucased', caucased={'csr-to-sign': csr})
    # Request replica Mariadb
    replica = self.requestReplica(primary, strict=False)
    # Let external caucased sign replica CSR
    # This asserts that all partitions, including replica, converge
    self.requestPrimary(name='caucased', caucased=replica)
    # Check (primary --> replica) replication
    self.checkReplicaState(replica)
    self.checkDataReplication(primary, replica)


class TestMariaDBReplicationChain(MariaDBReplicationTestCase):
  def test(self):
    primary = upstream = self.requestPrimary(caucased=False)
    cnx = self.getDatabaseConnection(primary)
    with contextlib.closing(cnx):
      with cnx.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE test_replication2 (
              col1 INT
            )
            """)
        cursor.execute(
            """
            INSERT INTO test_replication2 VALUES (1), (2)
            """)
        cnx.commit()
    replicas = []
    for i in range(3):
      replica = upstream = self.requestReplica(
        upstream,
        name='replica%d' % i,
        caucased=False,
      )
      replicas.append(replica)
      for i in range(7):
        if self.checkReplicaState(replica) == 0:
          break
        time.sleep((i + 1) ** 2)
      cnx = self.getDatabaseConnection(replica)
      with contextlib.closing(cnx):
        with cnx.cursor() as cursor:
          cursor.execute(
              """
              SELECT * FROM test_replication2
              """)
          self.assertEqual(((1,), (2,)), cursor.fetchall())
    self.checkDataReplication(primary, *replicas)
