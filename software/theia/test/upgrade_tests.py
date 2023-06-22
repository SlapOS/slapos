import json
import os

from slapos.testing.testcase import (
  installSoftwareUrlList,
  makeModuleSetUpAndTestCaseClass,
  SlapOSNodeCommandError,
)

import test
import test_resiliency


stable_software_url = "https://lab.nexedi.com/nexedi/slapos/raw/1.0.324/software/theia/software.cfg"
dev_software_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))


software_url_list = [stable_software_url, dev_software_url]

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(stable_software_url)


class UpgradeTestCase(SlapOSInstanceTestCase):
  _current_software_url = stable_software_url

  @classmethod
  def getSoftwareURL(cls):
    return cls._current_software_url

  @classmethod
  def upgrade(cls):
    # request instance on dev software
    cls._current_software_url = dev_software_url
    cls.logger.debug('Requesting instance on dev software')
    cls.requestDefaultInstance()

    # wait for slapos node instance
    snapshot_name = "{}.{}.dev.setUpClass".format(cls.__module__, cls.__name__)
    with cls._snapshotManager(snapshot_name):
      try:
        for _ in range(2): # propagation
          cls.waitForInstance()
        cls.logger.debug("Instance on dev software done")
      except BaseException:
        cls.logger.exception("Error during instance on dev software")
        raise

    cls.computer_partition = cls.requestDefaultInstance()

  @classmethod
  def beforeUpgrade(cls):
    pass

  @classmethod
  def setUpClass(cls):
    # request and instantiate with old software url
    super().setUpClass()

    # before upgrade hook
    cls.beforeUpgrade()

    # upgrade
    cls.upgrade()


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    software_url_list,
    debug=SlapOSInstanceTestCase._debug,
  )


class TestTheia(UpgradeTestCase, test.TestTheia):
  pass


class TestTheiaWithEmbeddedInstance(
    UpgradeTestCase,
    test.TestTheiaWithEmbeddedInstance):
  pass


class TestTheiaResilientInterface(
    UpgradeTestCase,
    test.TestTheiaResilientInterface):
  pass


class TestTheiaResilientWithEmbeddedInstance(
    UpgradeTestCase,
    test.TestTheiaResilientWithEmbeddedInstance):
  pass


class TestTheiaResilienceWithInitialInstance(
    UpgradeTestCase,
    test_resiliency.TestTheiaResilienceWithInitialInstance):

  @classmethod
  def beforeUpgrade(cls):
    # Check initial embedded instance
    test.TestTheiaWithEmbeddedInstance.test(cls())


class TestResilientTheiaUpgradeWithInitialInstance(
    UpgradeTestCase,
    test_resiliency.ResilientTheiaTestCase,
    test_resiliency.TheiaSyncMixin):

  backup_max_tries = 70
  backup_wait_interval = 10

  old_flag_file = os.path.join('etc', 'embedded-instance-config.json.done')
  old_exitcode_file = os.path.join('etc', 'embedded-request-exitcode')

  flag_file = os.path.join('var', 'state', 'standalone-ran-before.flag')
  exitcode_file = os.path.join('var', 'state', 'embedded-request.exitcode')

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'initial-embedded-instance': json.dumps({
        'software-url': test_resiliency.dummy_software_url
      }),
    }

  def assertExists(self, path):
    self.assertTrue(os.path.exists(path))

  def assertNotFound(self, path):
    self.assertFalse(os.path.exists(path))

  @classmethod
  def beforeUpgrade(cls):
    self = cls()
    self.assertExists(cls.getPartitionPath('export', self.old_flag_file))
    self.assertExists(cls.getPartitionPath('export', self.old_exitcode_file))
    self.assertExists(self.getPartitionPath('import', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_exitcode_file))

  def _prepareExport(self): # after upgrade
    self.assertNotFound(self.getPartitionPath('export', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('export', self.old_exitcode_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_exitcode_file))

    self.assertExists(self.getPartitionPath('export', self.flag_file))
    self.assertExists(self.getPartitionPath('export', self.exitcode_file))
    self.assertExists(self.getPartitionPath('import', self.flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.exitcode_file))

  def _checkSync(self):
    self.assertExists(self.getPartitionPath('export', self.flag_file))
    self.assertExists(self.getPartitionPath('export', self.exitcode_file))
    self.assertExists(self.getPartitionPath('import', self.flag_file))
    self.assertExists(self.getPartitionPath('import', self.exitcode_file))

  def _checkTakeover(self):
    self.assertNotFound(self.getPartitionPath('export', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('export', self.old_exitcode_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_exitcode_file))

    self.assertExists(self.getPartitionPath('export', self.flag_file))
    self.assertExists(self.getPartitionPath('export', self.exitcode_file))
    self.assertExists(self.getPartitionPath('import', self.flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.exitcode_file))


class TestResilientTheiaUpgradeWithInitialInstanceAndSync(
    TestResilientTheiaUpgradeWithInitialInstance):

  @classmethod
  def beforeUpgrade(cls):
    cls()._doSync()

  def _prepareExport(self): # after upgrade
    self.assertNotFound(self.getPartitionPath('export', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('export', self.old_exitcode_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_flag_file))
    self.assertNotFound(self.getPartitionPath('import', self.old_exitcode_file))

    self.assertExists(self.getPartitionPath('export', self.flag_file))
    self.assertExists(self.getPartitionPath('export', self.exitcode_file))
    self.assertExists(self.getPartitionPath('import', self.flag_file))
    self.assertExists(self.getPartitionPath('import', self.exitcode_file))
