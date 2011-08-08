import logging
import slapos.format
import unittest

# for mocking
import grp
import os
import pwd

USER_LIST = []
EXTERNAL_COMMAND_LIST = []

class FakeConfig:
  pass

class TestLoggerHandler(logging.Handler):
  def __init__(self, *args, **kwargs):
    self.bucket = []
    logging.Handler.__init__(self, *args, **kwargs)

  def emit(self, record):
    self.bucket.append(record.msg)

def fakeCallAndRead(argument_list, raise_on_error=True):
  if 'useradd' in argument_list:
    global USER_LIST
    USER_LIST.append(argument_list[-1])
  global EXTERNAL_COMMAND_LIST
  EXTERNAL_COMMAND_LIST.append(argument_list)
  return 0, 'UP'

class LoggableWrapper:
  def __init__(self, logger, name):
    self.__logger = logger
    self.__name = name

  def __call__(self, *args, **kwargs):
    arg_list = [repr(x) for x in args] + [
      '%s=%r' % (x, y) for x, y in kwargs.iteritems()]
    self.__logger.debug('%s(%s)' % (self.__name, ', '.join(arg_list)))

class GrpMock:
  @classmethod
  def getgrnam(self, name):
    if name == 'testuser':
      return True
    raise KeyError

class PwdMock:
  @classmethod
  def getpwnam(self, name):
    global USER_LIST
    if name in USER_LIST:
      class result:
        pw_uid = 0
        pw_gid = 0
      return result
    raise KeyError

class SlapformatMixin(unittest.TestCase):

  @classmethod
  def raisingKeyError(self, *args, **kwargs):
    raise KeyError

  def patchPwd(self):
    self.saved_pwd = dict()
    for fake in vars(PwdMock):
      self.saved_pwd[fake] = getattr(pwd, fake, None)
      setattr(pwd, fake, getattr(PwdMock, fake))

  def restorePwd(self):
    for name, original_value in self.saved_pwd.items():
      setattr(pwd, name, original_value)
    del self.saved_pwd

  def patchGrp(self):
    self.saved_grp = dict()
    for fake in vars(GrpMock):
      self.saved_grp[fake] = getattr(grp, fake, None)
      setattr(grp, fake, getattr(GrpMock, fake))

  def restoreGrp(self):
    for name, original_value in self.saved_grp.items():
      setattr(grp, name, original_value)
    del self.saved_grp

  def patchOs(self, logger):
    self.saved_os = dict()
    for fake in ['mkdir', 'chown', 'chmod', 'makedirs']:
      self.saved_os[fake] = getattr(os, fake, None)
      f = LoggableWrapper(logger, fake)
      setattr(os, fake, f)

  def restoreOs(self):
    for name, original_value in self.saved_os.items():
      setattr(os, name, original_value)
    del self.saved_os

  def setUp(self):
    config = FakeConfig()
    config.dry_run = True
    config.verbose = True
    logger = logging.getLogger('testcatch')
    logger.setLevel(logging.DEBUG)
    self.test_result = TestLoggerHandler()
    logger.addHandler(self.test_result)
    config.logger = logger
    self.partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    global EXTERNAL_COMMAND_LIST
    global USER_LIST
    EXTERNAL_COMMAND_LIST = []
    USER_LIST = ['testuser']

    self.real_callAndRead = slapos.format.callAndRead
    slapos.format.callAndRead = fakeCallAndRead
    self.patchOs(logger)
    self.patchGrp()
    self.patchPwd()

  def tearDown(self):
    self.restoreOs()
    self.restoreGrp()
    self.restorePwd()
    global EXTERNAL_COMMAND_LIST
    global USER_LIST
    EXTERNAL_COMMAND_LIST = []
    USER_LIST = ['testuser']
    slapos.format.callAndRead = self.real_callAndRead

class TestComputer(SlapformatMixin):
  def test_getAddress_empty_computer(self):
    computer = slapos.format.Computer('computer')
    self.assertEqual(computer.getAddress(), {'netmask': None, 'addr': None})

  def test_construct_empty(self):
    computer = slapos.format.Computer('computer')
    computer.construct()
    raise NotImplementedError

  def test_construct_empty_prepared(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16', 'eth0'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct()
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    global EXTERNAL_COMMAND_LIST
    self.assertEqual([
      ['ip', 'addr', 'list', 'bridge'],
      ['groupadd', 'slapsoft'],
      ['useradd', '-d', '/software_root', '-g', 'slapsoft', '-s',
        '/bin/false', 'slapsoft']],
      EXTERNAL_COMMAND_LIST)

  def test_construct_empty_prepared_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16', 'eth0'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    global EXTERNAL_COMMAND_LIST
    self.assertEqual([
      ['ip', 'addr', 'list', 'bridge'],],
      EXTERNAL_COMMAND_LIST)

  def test_construct_empty_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16', 'eth0'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_network=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    global EXTERNAL_COMMAND_LIST
    self.assertEqual([
      ['ip', 'addr', 'list', 'bridge'],
      ['groupadd', 'slapsoft'],
      ['useradd', '-d', '/software_root', '-g', 'slapsoft', '-s',
        '/bin/false', 'slapsoft']],
      EXTERNAL_COMMAND_LIST)

  def test_construct_empty_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16', 'eth0'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_network=False, alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    global EXTERNAL_COMMAND_LIST
    self.assertEqual([
      ['ip', 'addr', 'list', 'bridge'],
      ],
      EXTERNAL_COMMAND_LIST)

class TestPartition(SlapformatMixin):

  def test_createPath(self):
    self.partition.createPath()
    self.assertEqual(
      [
        "mkdir('/part_path', 488)",
        "chown('/part_path', 0, 0)",
        "chmod('/part_path', 488)"
      ],
      self.test_result.bucket
    )

  def test_createPath_no_alter_user(self):
    self.partition.createPath(False)
    self.assertEqual(
      [
        "mkdir('/part_path', 488)",
        "chmod('/part_path', 488)"
      ],
      self.test_result.bucket
    )

class TestUser(SlapformatMixin):
  def test_create(self):
    global EXTERNAL_COMMAND_LIST
    user = slapos.format.User('doesnotexistsyet')
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'doesnotexistsyet'],
        ['useradd', '-d', '/doesnotexistsyet', '-g', 'doesnotexistsyet', '-s',
          '/bin/false', 'doesnotexistsyet']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_create_additional_groups(self):
    global EXTERNAL_COMMAND_LIST
    user = slapos.format.User('doesnotexistsyet', ['additionalgroup1',
      'additionalgroup2'])
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'doesnotexistsyet'],
        ['useradd', '-d', '/doesnotexistsyet', '-g', 'doesnotexistsyet', '-s',
          '/bin/false', '-G', 'additionalgroup1,additionalgroup2',
          'doesnotexistsyet']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_create_group_exists(self):
    pwd.getpwnam = self.raisingKeyError
    global EXTERNAL_COMMAND_LIST

    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['useradd', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_create_user_exists_additional_groups(self):
    grp.getgrnam = self.raisingKeyError
    global EXTERNAL_COMMAND_LIST
    user = slapos.format.User('testuser', ['additionalgroup1',
      'additionalgroup2'])
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'testuser'],
        ['usermod', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          '-G', 'additionalgroup1,additionalgroup2', 'testuser']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_create_user_exists(self):
    grp.getgrnam = self.raisingKeyError
    global EXTERNAL_COMMAND_LIST
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'testuser'],
        ['usermod', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_create_user_group_exists(self):
    global EXTERNAL_COMMAND_LIST
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['usermod', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      EXTERNAL_COMMAND_LIST)

  def test_isAvailable(self):
    user = slapos.format.User('testuser')
    self.assertTrue(user.isAvailable())

  def test_isAvailable_notAvailable(self):
    user = slapos.format.User('doesnotexistsyet')
    self.assertFalse(user.isAvailable())

if __name__ == '__main__':
      unittest.main()
