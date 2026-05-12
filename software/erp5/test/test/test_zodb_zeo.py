import gzip
import contextlib
import json
import pathlib
import shutil
import subprocess
import tempfile

import zodburi
from ZODB.DB import DB
from slapos.testing.utils import CrontabMixin


from . import ERP5InstanceTestCase, default, matrix, setUpModule, ERP5PY3

_ = setUpModule


class ZEOTestCase(ERP5InstanceTestCase):
  __test_matrix__ = matrix((default,))

  @classmethod
  def getInstanceSoftwareType(cls) -> str:
    return "zodb-zeo"

  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    return {
      "tcpv4-port": 8000,
      "computer-memory-percent-threshold": 100,
      "name": cls.__name__,
      "monitor-passwd": "secret",
      "zodb-dict": {"root": {}},
    }

  @classmethod
  def getInstanceParameterDict(cls) -> dict:
    return {"_": json.dumps(cls._getInstanceParameterDict())}

  def setUp(self) -> None:
    self.storage_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )["storage-dict"]

  def db(self) -> contextlib.AbstractContextManager[DB]:
    root = self.storage_dict["root"]
    zeo_uri = f"zeo://{root['server']}?storage={root['storage']}"
    storage_factory, dbkw = zodburi.resolve_uri(zeo_uri)
    return contextlib.closing(DB(storage_factory(), **dbkw))


class TestRepozo(ZEOTestCase, CrontabMixin):
  __partition_reference__ = "rpz"

  def test_backup_and_restore(self) -> None:
    def check_state():
      (self.computer_partition_root_path / ".timestamp").unlink()
      self.waitForInstance()
      if ERP5PY3:
        with self.db() as db:
          with db.transaction() as cnx:
            self.assertEqual(cnx.root.state, "before backup")

    if ERP5PY3:
      # as it is not possible to connect to a python2 ZEO server
      # from a python3 client, we check more when the server is python3
      with self.db() as db:
        with db.transaction() as cnx:
          cnx.root.state = "before backup"

    check_state()
    self._executeCrontabAtDate("tidstorage", "2000-01-01 UTC")
    dat, fsz, index, index_latest = sorted(
      [
        p.name
        for p in (
          self.computer_partition_root_path / "srv" / "backup" / "zodb" / "root"
        ).glob("*")
      ]
    )
    self.assertRegex(dat, r'2000-01-01-00-\d\d-\d\d.dat')
    self.assertRegex(fsz, r'2000-01-01-00-\d\d-\d\d.fsz')
    self.assertRegex(index, r'2000-01-01-00-\d\d-\d\d.index')
    self.assertEqual(index_latest, 'index.latest')

    if ERP5PY3:
      with self.db() as db:
        with db.transaction() as cnx:
          cnx.root.state = "after backup"

    restore_script = self.computer_partition_root_path / "srv" / "runner-import-restore"
    self.assertTrue(restore_script.exists())
    status, restore_output = subprocess.getstatusoutput(str(restore_script))
    self.assertEqual(status, 1)
    self.assertIn("Zeo is already running", restore_output)

    with self.slap.instance_supervisor_rpc as supervisor:
      supervisor.stopAllProcesses()
    restore_output = subprocess.check_output(restore_script)
    check_state()

    if ERP5PY3:
      with self.db() as db:
        with db.transaction() as cnx:
          cnx.root.state = "make a change to force a new backup"

      self._executeCrontabAtDate("tidstorage", "2000-01-02 UTC")
      dat, fsz, deltafsz, index, index_latest = sorted(
        [
          p.name
          for p in (
            self.computer_partition_root_path / "srv" / "backup" / "zodb" / "root"
          ).glob("*")
        ]
      )
      self.assertRegex(dat, r'2000-01-01-00-\d\d-\d\d.dat')
      self.assertRegex(fsz, r'2000-01-01-00-\d\d-\d\d.fsz')
      self.assertRegex(deltafsz, r'2000-01-02-00-\d\d-\d\d.deltafsz')
      self.assertRegex(index, r'2000-01-02-00-\d\d-\d\d.index')
      self.assertEqual(index_latest, 'index.latest')


class TestBackupDirectory(ZEOTestCase, CrontabMixin):
  @classmethod
  def _getInstanceParameterDict(cls) -> dict:
    cls._zeo_backup_dir = pathlib.Path(cls.enterClassContext(tempfile.TemporaryDirectory()))
    parameter_dict = super(TestBackupDirectory, cls)._getInstanceParameterDict()
    parameter_dict['zodb-dict']['root'] = {
      "family": "1",
      "backup": f"{cls._zeo_backup_dir}/%(name)s",
    }
    return parameter_dict

  def test_backup_directory(self):
    self._executeCrontabAtDate("tidstorage", "2000-01-01 UTC")
    self.assertRegex(
      sorted([f.name for f in (self._zeo_backup_dir / "root").glob("*")])[-2],
      r'2000-01-01-00-\d\d-\d\d.index',
    )
    self.assertFalse(list((self.computer_partition_root_path / "srv" / "backup" / "zodb" / "root").glob("*")))


class TestCheckBackup(ZEOTestCase, CrontabMixin):
  def test_check_backup(self):
    self._executeCrontabAtDate("tidstorage", "2000-01-01 UTC")
    self._executeCrontabAtDate("check-backup", "2000-01-02 UTC")  # no error
    if ERP5PY3:
      # simulate a ZODB different from repozo's dat file (only supported by recent repozo)
      file_storage= self.computer_partition_root_path / "srv" / "zodb" / "root.fs"
      file_storage.with_suffix(".save").write_bytes(file_storage.read_bytes())
      file_storage.write_bytes(b"corrupted")
      try:
        self._executeCrontabAtDate("check-backup", "2000-01-02 UTC")
      except subprocess.CalledProcessError as e:
        self.assertRegex(
          e.output.decode(),
          r"Checking backup for root ...\n"
          r".*/srv/zodb/root.fs between \d+ and \d+ has checksum"
          " [0-9a-f]{32} instead of [0-9a-f]{32}\n"
          r"ERROR: root Backup check failed\.")
      # restore the original file, to not break next assertions
      file_storage.with_suffix(".save").rename(file_storage)

    # simulate a corrupted backup fsz
    fsz, = list((self.computer_partition_root_path / "srv" / "backup" / "zodb" / "root").glob("*.fsz"))
    with gzip.open(fsz, "wb") as f:
      f.write(b"crpt")
    try:
      self._executeCrontabAtDate("check-backup", "2000-01-02 UTC")
    except subprocess.CalledProcessError as e:
      self.assertRegex(
        e.output.decode(),
        r"Checking backup for root ...\n"
        r".*/srv/backup/zodb/root/2000-01-01-00-\d{2}-\d{2}\.fsz has checksum [0-9a-f]{32} \(when uncompressed\) "
        r"instead of [0-9a-f]{32}\n"
        r"ERROR: root Backup check failed\.")
