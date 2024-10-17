import contextlib
import subprocess
import json

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
    dat, fsz, index = sorted(
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

    if ERP5PY3:
      with self.db() as db:
        with db.transaction() as cnx:
          cnx.root.state = "after backup"
      db.close()

    restore_script = self.computer_partition_root_path / "srv" / "runner-import-restore"
    self.assertTrue(restore_script.exists())
    status, restore_output = subprocess.getstatusoutput(str(restore_script))
    self.assertEqual(status, 1)
    self.assertIn("Zeo is already running", restore_output)

    with self.slap.instance_supervisor_rpc as supervisor:
      supervisor.stopAllProcesses()
    restore_output = subprocess.check_output(restore_script)
    check_state()
