import logging
import slapos.format
import unittest

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

def raising_KeyError(name):
  raise KeyError

def returning_True(name):
  return True
class FakeClass:
  pass

class SlapformatMixin(unittest.TestCase):
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
      slapos.format.User('root'), [], None)
    self.partition._os = slapos.format.OS(config)
    global call_and_read_list
    call_and_read_list = []
    self.real_callAndRead = slapos.format.callAndRead
    slapos.format.callAndRead = fakeCallAndRead

  def tearDown(self):
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
    user = slapos.format.User('testuser')
    user._getpwnam = raising_KeyError
    grp = FakeClass()
    grp.getgrnam = raising_KeyError
    user._grp = grp
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'testuser'],
        ['useradd', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      call_and_read_list)

  def test_create_additional_groups(self):
    global call_and_read_list
    user = slapos.format.User('testuser', ['additionalgroup1',
      'additionalgroup2'])
    user._getpwnam = raising_KeyError
    grp = FakeClass()
    grp.getgrnam = raising_KeyError
    user._grp = grp
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['groupadd', 'testuser'],
        ['useradd', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          '-G', 'additionalgroup1,additionalgroup2', 'testuser']
      ],
      call_and_read_list)

  def test_create_group_exists(self):
    global call_and_read_list
    user = slapos.format.User('testuser')
    user._getpwnam = raising_KeyError
    grp = FakeClass()
    grp.getgrnam = returning_True
    user._grp = grp
    user.setPath('/testuser')
    user.create()

    self.assertEqual(
      [
        ['useradd', '-d', '/testuser', '-g', 'testuser', '-s', '/bin/false',
          'testuser']
      ],
      call_and_read_list)

  def test_create_user_exists_additional_groups(self):
    global call_and_read_list
    user = slapos.format.User('testuser', ['additionalgroup1',
      'additionalgroup2'])
    user._getpwnam = returning_True
    grp = FakeClass()
    grp.getgrnam = raising_KeyError
    user._grp = grp
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
    global call_and_read_list
    user = slapos.format.User('testuser')
    user._getpwnam = returning_True
    grp = FakeClass()
    grp.getgrnam = raising_KeyError
    user._grp = grp
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
    user._getpwnam = returning_True
    grp = FakeClass()
    grp.getgrnam = returning_True
    user._grp = grp
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
    user._getpwnam = returning_True
    grp = FakeClass()
    grp.getgrnam = returning_True
    user._grp = grp
    self.assertTrue(user.isAvailable())

  def test_isAvailable_notAvailable(self):
    user = slapos.format.User('testuser')
    user._getpwnam = raising_KeyError
    grp = FakeClass()
    grp.getgrnam = raising_KeyError
    user._grp = grp
    self.assertFalse(user.isAvailable())

if __name__ == '__main__':
      unittest.main()
