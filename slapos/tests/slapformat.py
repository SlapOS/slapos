import logging
import slapos.format
import unittest

import netaddr

# for mocking
import grp
import netifaces
import os
import pwd
import time

USER_LIST = []
GROUP_LIST = []
INTERFACE_DICT = {}

class FakeConfig:
  pass

class TestLoggerHandler(logging.Handler):
  def __init__(self, *args, **kwargs):
    self.bucket = []
    logging.Handler.__init__(self, *args, **kwargs)

  def emit(self, record):
    self.bucket.append(record.msg)

class FakeCallAndRead:
  def __init__(self):
    self.external_command_list = []

  def __call__(self, argument_list, raise_on_error=True):
    retval = 0, 'UP'
    global INTERFACE_DICT
    if 'useradd' in argument_list:
      global USER_LIST
      USER_LIST.append(argument_list[-1])
    elif 'groupadd' in argument_list:
      global GROUP_LIST
      GROUP_LIST.append(argument_list[-1])
    elif argument_list[:3] == ['ip', 'addr', 'add']:
      ip, interface = argument_list[3], argument_list[5]
      if ':' not in ip:
        netmask = netaddr.strategy.ipv4.int_to_str(
          netaddr.strategy.ipv4.prefix_to_netmask[int(ip.split('/')[1])])
        ip = ip.split('/')[0]
        INTERFACE_DICT[interface][2].append({'addr': ip, 'netmask': netmask})
      else:
        netmask = netaddr.strategy.ipv6.int_to_str(
          netaddr.strategy.ipv6.prefix_to_netmask[int(ip.split('/')[1])])
        ip = ip.split('/')[0]
        INTERFACE_DICT[interface][10].append({'addr': ip, 'netmask': netmask})
      # stabilise by mangling ip to just ip string
      argument_list[3] = 'ip/%s' % netmask
    elif argument_list[:3] == ['ip', 'addr', 'list']:
      retval = 0, str(INTERFACE_DICT)
    self.external_command_list.append(' '.join(argument_list))
    return retval

class LoggableWrapper:
  def __init__(self, logger, name):
    self.__logger = logger
    self.__name = name

  def __call__(self, *args, **kwargs):
    arg_list = [repr(x) for x in args] + [
      '%s=%r' % (x, y) for x, y in kwargs.iteritems()]
    self.__logger.debug('%s(%s)' % (self.__name, ', '.join(arg_list)))

class TimeMock:
  @classmethod
  def sleep(self, seconds):
    return

class GrpMock:
  @classmethod
  def getgrnam(self, name):
    global GROUP_LIST
    if name in GROUP_LIST:
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

class NetifacesMock:
  @classmethod
  def ifaddresses(self, name):
    global INTERFACE_DICT
    if name in INTERFACE_DICT:
      return INTERFACE_DICT[name]
    raise ValueError

  @classmethod
  def interfaces(self):
    global INTERFACE_DICT
    return INTERFACE_DICT.keys()

class SlapformatMixin(unittest.TestCase):
  # keep big diffs
  maxDiff = None
  def patchNetifaces(self):
    self.netifaces = NetifacesMock()
    self.saved_netifaces = dict()
    for fake in vars(NetifacesMock):
      self.saved_netifaces[fake] = getattr(netifaces, fake, None)
      setattr(netifaces, fake, getattr(self.netifaces, fake))

  def restoreNetifaces(self):
    for name, original_value in self.saved_netifaces.items():
      setattr(netifaces, name, original_value)
    del self.saved_netifaces

  def patchPwd(self):
    self.saved_pwd = dict()
    for fake in vars(PwdMock):
      self.saved_pwd[fake] = getattr(pwd, fake, None)
      setattr(pwd, fake, getattr(PwdMock, fake))

  def restorePwd(self):
    for name, original_value in self.saved_pwd.items():
      setattr(pwd, name, original_value)
    del self.saved_pwd

  def patchTime(self):
    self.saved_time = dict()
    for fake in vars(TimeMock):
      self.saved_time[fake] = getattr(time, fake, None)
      setattr(time, fake, getattr(TimeMock, fake))

  def restoreTime(self):
    for name, original_value in self.saved_time.items():
      setattr(time, name, original_value)
    del self.saved_time

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
    global USER_LIST
    USER_LIST = []
    global GROUP_LIST
    GROUP_LIST = []
    global INTERFACE_DICT
    INTERFACE_DICT = {}

    self.real_callAndRead = slapos.format.callAndRead
    self.fakeCallAndRead = FakeCallAndRead()
    slapos.format.callAndRead = self.fakeCallAndRead
    self.patchOs(logger)
    self.patchGrp()
    self.patchTime()
    self.patchPwd()
    self.patchNetifaces()

  def tearDown(self):
    self.restoreOs()
    self.restoreGrp()
    self.restoreTime()
    self.restorePwd()
    self.restoreNetifaces()
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
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct()
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft -s /bin/false slapsoft'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_network=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft -s /bin/false slapsoft'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_network=False, alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      2: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      10: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.construct()
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)",
      "mkdir('/instance_root/partition', 488)",
      "chown('/instance_root/partition', 0, 0)",
      "chmod('/instance_root/partition', 488)"
    ],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft -s /bin/false slapsoft',
      'groupadd testuser',
      'useradd -d /instance_root/partition -g testuser -s /bin/false -G slapsoft testuser',
      'tunctl -t tap -u testuser',
      'ip link set tap up',
      'brctl show',
      'brctl addif bridge tap',
      'ip addr add ip/255.255.255.255 dev bridge',
      'ip addr list bridge',
      'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
      'ip addr list bridge',
    ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      2: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      10: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.construct(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)",
      "mkdir('/instance_root/partition', 488)",
      "chmod('/instance_root/partition', 488)"
    ],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'tunctl -t tap -u root',
      'ip link set tap up',
      'brctl show',
      'brctl addif bridge tap',
      'ip addr add ip/255.255.255.255 dev bridge',
      'ip addr list bridge',
      'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
      'ip addr list bridge',
    ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      2: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      10: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.construct(alter_network=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)",
      "mkdir('/instance_root/partition', 488)",
      "chown('/instance_root/partition', 0, 0)",
      "chmod('/instance_root/partition', 488)"
    ],
      self.test_result.bucket)
    self.assertEqual([
#      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft -s /bin/false slapsoft',
      'groupadd testuser',
      'useradd -d /instance_root/partition -g testuser -s /bin/false -G slapsoft testuser',
#      'ip addr add ip/255.255.255.255 dev bridge',
#      'ip addr list bridge',
#      'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
#      'ip addr list bridge',
    ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      bridge=slapos.format.Bridge('bridge', '127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      2: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      10: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.construct(alter_network=False, alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)",
      "mkdir('/instance_root/partition', 488)",
      "chmod('/instance_root/partition', 488)"
    ],
      self.test_result.bucket)
    self.assertEqual([
#      'ip addr list bridge',
#      'ip addr add ip/255.255.255.255 dev bridge',
#      'ip addr list bridge',
#      'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
#      'ip addr list bridge',
    ],
      self.fakeCallAndRead.external_command_list)

class TestPartition(SlapformatMixin):

  def test_createPath(self):
    global USER_LIST
    USER_LIST = ['testuser']
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
    user = slapos.format.User('doesnotexistsyet')
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual([
      'groupadd doesnotexistsyet',
      'useradd -d /doesnotexistsyet -g doesnotexistsyet -s /bin/false '\
        'doesnotexistsyet'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_create_additional_groups(self):
    user = slapos.format.User('doesnotexistsyet', ['additionalgroup1',
      'additionalgroup2'])
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual([
      'groupadd doesnotexistsyet',
      'useradd -d /doesnotexistsyet -g doesnotexistsyet -s /bin/false -G '\
        'additionalgroup1,additionalgroup2 doesnotexistsyet'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_create_group_exists(self):
    global GROUP_LIST
    GROUP_LIST = ['testuser']
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual([
      'useradd -d /testuser -g testuser -s /bin/false testuser'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_create_user_exists_additional_groups(self):
    global USER_LIST
    USER_LIST = ['testuser']
    user = slapos.format.User('testuser', ['additionalgroup1',
      'additionalgroup2'])
    user.setPath('/testuser')
    user.create()

    self.assertEqual([
      'groupadd testuser',
      'usermod -d /testuser -g testuser -s /bin/false -G '\
        'additionalgroup1,additionalgroup2 testuser'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_create_user_exists(self):
    global USER_LIST
    USER_LIST = ['testuser']
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual([
      'groupadd testuser',
      'usermod -d /testuser -g testuser -s /bin/false testuser'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_create_user_group_exists(self):
    global USER_LIST
    USER_LIST = ['testuser']
    global GROUP_LIST
    GROUP_LIST = ['testuser']
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual([
      'usermod -d /testuser -g testuser -s /bin/false testuser'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_isAvailable(self):
    global USER_LIST
    USER_LIST = ['testuser']
    user = slapos.format.User('testuser')
    self.assertTrue(user.isAvailable())

  def test_isAvailable_notAvailable(self):
    user = slapos.format.User('doesnotexistsyet')
    self.assertFalse(user.isAvailable())

if __name__ == '__main__':
      unittest.main()
