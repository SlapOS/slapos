import logging
import slapos.format
import unittest

# for mocking
import grp
import os
import pwd

class FakeConfig:
  pass

class TestLoggerHandler(logging.Handler):
  def __init__(self, *args, **kwargs):
    self.bucket = []
    logging.Handler.__init__(self, *args, **kwargs)

  def emit(self, record):
    self.bucket.append(record.msg)

call_and_read_list = []
def fakeCallAndRead(argument_list, raise_on_error=True):
  global call_and_read_list
  call_and_read_list.append(argument_list)

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
    if name == 'testuser':
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
    config.dry_run = False
    config.verbose = True
    logger = logging.getLogger('testcatch')
    logger.setLevel(logging.DEBUG)
    self.test_result = TestLoggerHandler()
    logger.addHandler(self.test_result)
    config.logger = logger
    self.partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    global call_and_read_list
    call_and_read_list = []
    self.real_callAndRead = slapos.format.callAndRead
    slapos.format.callAndRead = fakeCallAndRead
    self.patchOs(logger)
    self.patchGrp()
    self.patchPwd()

  def tearDown(self):
    self.restoreOs()
    self.restoreGrp()
    self.restorePwd()
    global call_and_read_list
    call_and_read_list = []
    slapos.format.callAndRead = self.real_callAndRead


class TestComputer(SlapformatMixin):
  def test_getAddress_empty_computer(self):
    computer = slapos.format.Computer('computer')
    self.assertEqual(computer.getAddress(), {'netmask': None, 'addr': None})

  def test_construct_empty(self):
    computer = slapos.format.Computer('computer')
    computer.construct()

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
    global call_and_read_list
    user = slapos.format.User('doesnotexistsyet')
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'doesnotexistsyet'],
        ['useradd', '-d', '/doesnotexistsyet', '-g', 'doesnotexistsyet', '-s',
          '/bin/false', 'doesnotexistsyet']
      ],
      call_and_read_list)

  def test_create_additional_groups(self):
    global call_and_read_list
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
      call_and_read_list)

  def test_create_group_exists(self):
    pwd.getpwnam = self.raisingKeyError
    global call_and_read_list

    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['useradd', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      call_and_read_list)

  def test_create_user_exists_additional_groups(self):
    grp.getgrnam = self.raisingKeyError
    global call_and_read_list
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
      call_and_read_list)

  def test_create_user_exists(self):
    grp.getgrnam = self.raisingKeyError
    global call_and_read_list
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'testuser'],
        ['usermod', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      call_and_read_list)

  def test_create_user_group_exists(self):
    global call_and_read_list
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['usermod', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      call_and_read_list)

  def test_isAvailable(self):
    user = slapos.format.User('testuser')
    self.assertTrue(user.isAvailable())

  def test_isAvailable_notAvailable(self):
    user = slapos.format.User('doesnotexistsyet')
    self.assertFalse(user.isAvailable())

if __name__ == '__main__':
      unittest.main()
