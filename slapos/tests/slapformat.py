# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
import glob
import logging
import slapos.format
import slapos.util
import slapos.manager.cpuset
import unittest

import netaddr
import shutil
import socket
# for mocking
import grp
import netifaces
import os
import pwd
import time
import mock

from .slapgrid import DummyManager

USER_LIST = []
GROUP_LIST = []
INTERFACE_DICT = {}


def file_content(file_path):
  """Read file(s) content."""
  if isinstance(file_path, (list, tuple)):
    return [file_content(fx) for fx in file_path]
  with open(file_path, "rt") as fi:
    return fi.read().strip()


def file_write(stuff, file_path):
  """Write stuff into file_path."""
  with open(file_path, "wt") as fo:
    fo.write(stuff)


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
      print argument_list
      global USER_LIST
      username = argument_list[-1]
      if username == '-r':
        username = argument_list[-2]
      USER_LIST.append(username)
    elif 'groupadd' in argument_list:
      global GROUP_LIST
      GROUP_LIST.append(argument_list[-1])
    elif argument_list[:3] == ['ip', 'addr', 'add']:
      ip, interface = argument_list[3], argument_list[5]
      if ':' not in ip:
        netmask = netaddr.strategy.ipv4.int_to_str(
          netaddr.strategy.ipv4.prefix_to_netmask[int(ip.split('/')[1])])
        ip = ip.split('/')[0]
        INTERFACE_DICT[interface][socket.AF_INET].append({'addr': ip, 'netmask': netmask})
      else:
        netmask = netaddr.strategy.ipv6.int_to_str(
          netaddr.strategy.ipv6.prefix_to_netmask[int(ip.split('/')[1])])
        ip = ip.split('/')[0]
        INTERFACE_DICT[interface][socket.AF_INET6].append({'addr': ip, 'netmask': netmask})
      # stabilise by mangling ip to just ip string
      argument_list[3] = 'ip/%s' % netmask
    elif argument_list[:3] == ['ip', 'addr', 'list'] or \
         argument_list[:4] == ['ip', '-6', 'addr', 'list']:
      retval = 0, str(INTERFACE_DICT)
    elif argument_list[:3] == ['ip', 'route', 'show']:
      retval = 0, 'OK'
    elif argument_list[:3] == ['route', 'add', '-host']:
      retval = 0, 'OK'
    elif argument_list[:2] == ['brctl', 'show']:
      retval = 0, "\n".join(("bridge name bridge id   STP enabled interfaces",
                             "bridge bridge bridge b001   000:000 1 fakeinterface",
                             "                                      fakeinterface2"
                             ""))
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
      class PwdResult:
        def __init__(self, name):
          self.pw_name = name
          self.pw_uid = self.pw_gid = USER_LIST.index(name)

        def __getitem__(self, index):
          if index == 0:
            return self.pw_name
          if index == 2:
            return self.pw_uid
          if index == 3:
            return self.pw_gid
      return PwdResult(name)
    raise KeyError("User \"{}\" not in global USER_LIST {!s}".format(name, USER_LIST))


class NetifacesMock:
  @classmethod
  def ifaddresses(self, name):
    global INTERFACE_DICT
    if name in INTERFACE_DICT:
      return INTERFACE_DICT[name]
    raise ValueError("Interface \"{}\" not in INTERFACE_DICT {!s}".format(
      name, INTERFACE_DICT))

  @classmethod
  def interfaces(self):
    global INTERFACE_DICT
    return INTERFACE_DICT.keys()

class SlaposUtilMock:
  @classmethod
  def chownDirectory(*args, **kw):
    pass

class SlapformatMixin(unittest.TestCase):
  # keep big diffs
  maxDiff = None

  def patchNetifaces(self):
    self.netifaces = NetifacesMock()
    self.saved_netifaces = {}
    for fake in vars(NetifacesMock):
      self.saved_netifaces[fake] = getattr(netifaces, fake, None)
      setattr(netifaces, fake, getattr(self.netifaces, fake))

  def restoreNetifaces(self):
    for name, original_value in self.saved_netifaces.items():
      setattr(netifaces, name, original_value)
    del self.saved_netifaces

  def patchPwd(self):
    self.saved_pwd = {}
    for fake in vars(PwdMock):
      self.saved_pwd[fake] = getattr(pwd, fake, None)
      setattr(pwd, fake, getattr(PwdMock, fake))

  def restorePwd(self):
    for name, original_value in self.saved_pwd.items():
      setattr(pwd, name, original_value)
    del self.saved_pwd

  def patchTime(self):
    self.saved_time = {}
    for fake in vars(TimeMock):
      self.saved_time[fake] = getattr(time, fake, None)
      setattr(time, fake, getattr(TimeMock, fake))

  def restoreTime(self):
    for name, original_value in self.saved_time.items():
      setattr(time, name, original_value)
    del self.saved_time

  def patchGrp(self):
    self.saved_grp = {}
    for fake in vars(GrpMock):
      self.saved_grp[fake] = getattr(grp, fake, None)
      setattr(grp, fake, getattr(GrpMock, fake))

  def restoreGrp(self):
    for name, original_value in self.saved_grp.items():
      setattr(grp, name, original_value)
    del self.saved_grp

  def patchOs(self, logger):
    self.saved_os = {}
    for fake in ['mkdir', 'chown', 'chmod', 'makedirs']:
      self.saved_os[fake] = getattr(os, fake, None)
      f = LoggableWrapper(logger, fake)
      setattr(os, fake, f)

  def restoreOs(self):
    if not hasattr(self, 'saved_os'):
      return  # os was never patched or already restored
    for name, original_value in self.saved_os.items():
      setattr(os, name, original_value)
    del self.saved_os

  def patchSlaposUtil(self):
    self.saved_slapos_util = {}
    for fake in ['chownDirectory']:
      self.saved_slapos_util[fake] = getattr(slapos.util, fake, None)
      setattr(slapos.util, fake, getattr(SlaposUtilMock, fake))

  def restoreSlaposUtil(self):
    for name, original_value in self.saved_slapos_util.items():
      setattr(slapos.util, name, original_value)
    del self.saved_slapos_util

  def setUp(self):
    config = FakeConfig()
    config.dry_run = True
    config.verbose = True
    logger = logging.getLogger('testcatch')
    logger.setLevel(logging.DEBUG)
    self.test_result = TestLoggerHandler()
    logger.addHandler(self.test_result)
    config.logger = logger
    if hasattr(self, "logger"):
      raise ValueError("{} already has logger attached".format(self.__class__.__name__))
    self.logger = logger
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
    self.patchSlaposUtil()

  def tearDown(self):
    self.restoreOs()
    self.restoreGrp()
    self.restoreTime()
    self.restorePwd()
    self.restoreNetifaces()
    self.restoreSlaposUtil()
    slapos.format.callAndRead = self.real_callAndRead


class TestComputer(SlapformatMixin):
  def test_getAddress_empty_computer(self):
    computer = slapos.format.Computer('computer', instance_root='/instance_root', software_root='software_root')
    self.assertEqual(computer.getAddress(), {'netmask': None, 'addr': None})

  @unittest.skip("Not implemented")
  def test_construct_empty(self):
    computer = slapos.format.Computer('computer', instance_root='/instance_root', software_root='software_root')
    computer.format()

  @unittest.skip("Not implemented")
  def test_construct_empty_prepared(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[])
    computer.format()
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft slapsoft -r'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[])
    computer.format(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
        'ip addr list bridge',
        'brctl show',
      ],
      self.fakeCallAndRead.external_command_list)

  @unittest.skip("Not implemented")
  def test_construct_empty_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[])
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chown('/software_root', 0, 0)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
      'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft slapsoft -r'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[])
    computer.format(alter_network=False, alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual([
        'ip addr list bridge',
        'brctl show',
      ],
      self.fakeCallAndRead.external_command_list)

  @unittest.skip("Not implemented")
  def test_construct_prepared(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [], tap=slapos.format.Tap('tap')),
        ])
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.format()
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
      'useradd -d /software_root -g slapsoft slapsoft -r',
      'groupadd testuser',
      'useradd -d /instance_root/partition -g testuser -G slapsoft testuser -r',
      'brctl show',
      'ip tuntap add dev tap mode tap user testuser',
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
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [], tap=slapos.format.Tap('tap')),
        ])
    global USER_LIST
    USER_LIST = ['testuser']
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.format(alter_user=False)
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
        'brctl show',
        'ip tuntap add dev tap mode tap user testuser',
        'ip link set tap up',
        'brctl show',
        'brctl show',
        'brctl addif bridge tap',
        'ip addr add ip/255.255.255.255 dev bridge',
        # 'ip addr list bridge',
        'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
        'ip -6 addr list bridge',
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared_tap_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      tap_gateway_interface='eth1',
      interface=slapos.format.Interface(
        logger=self.logger, name='iface', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [], 
            tap=slapos.format.Tap('tap')),
        ])
    global USER_LIST
    USER_LIST = ['testuser']
    global INTERFACE_DICT
    INTERFACE_DICT['iface'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }
    INTERFACE_DICT['eth1'] = {
      socket.AF_INET: [{'addr': '10.8.0.1', 'broadcast': '10.8.0.254',
        'netmask': '255.255.255.0'}]
    }

    computer.format(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)",
      "mkdir('/instance_root/partition', 488)",
      "chmod('/instance_root/partition', 488)"
    ],
      self.test_result.bucket)
    self.assertEqual([
        'ip addr list iface',
        'brctl show',
        'ip tuntap add dev tap mode tap user testuser',
        'ip link set tap up',
        'ip route show 10.8.0.2',
        'ip route add 10.8.0.2 dev tap',
        'ip addr add ip/255.255.255.255 dev iface',
        'ip addr add ip/ffff:ffff:ffff:ffff:: dev iface',
        'ip -6 addr list iface'
      ],
      self.fakeCallAndRead.external_command_list)
    partition = computer.partition_list[0]
    self.assertEqual(partition.tap.ipv4_addr, '10.8.0.2')
    self.assertEqual(partition.tap.ipv4_netmask, '255.255.255.0')
    self.assertEqual(partition.tap.ipv4_gateway, '10.8.0.1')
    self.assertEqual(partition.tap.ipv4_network, '10.8.0.0')

  @unittest.skip("Not implemented")
  def test_construct_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [],
            tap=slapos.format.Tap('tap')),
        ])
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }
    computer.format(alter_network=False)
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
      # 'ip addr list bridge',
      'groupadd slapsoft',
      'useradd -d /software_root -g slapsoft slapsoft -r',
      'groupadd testuser',
      'useradd -d /instance_root/partition -g testuser -G slapsoft testuser -r',
      # 'ip addr add ip/255.255.255.255 dev bridge',
      # 'ip addr list bridge',
      # 'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
      # 'ip addr list bridge',
    ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [],
            tap=slapos.format.Tap('tap')),
        ])
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.format(alter_network=False, alter_user=False)
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
        'brctl show',
        'ip addr add ip/255.255.255.255 dev bridge',
        # 'ip addr list bridge',
        'ip addr add ip/ffff:ffff:ffff:ffff:: dev bridge',
        'ip -6 addr list bridge',
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_use_unique_local_address_block(self):
    """
    Test that slapformat creates a unique local address in the interface.
    """
    global USER_LIST
    USER_LIST = ['root']
    computer = slapos.format.Computer('computer',
      instance_root='/instance_root',
      software_root='/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='myinterface', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/part_path', slapos.format.User('testuser'), [],
            tap=slapos.format.Tap('tap')),
        ])
    global INTERFACE_DICT
    INTERFACE_DICT['myinterface'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.format(use_unique_local_address_block=True, alter_user=False, create_tap=False)
    self.assertEqual([
        "makedirs('/instance_root', 493)",
        "makedirs('/software_root', 493)",
        "chmod('/software_root', 493)",
        "mkdir('/instance_root/partition', 488)",
        "chmod('/instance_root/partition', 488)"
      ],
      self.test_result.bucket)
    self.assertEqual([
        'ip addr list myinterface',
        'brctl show',
        'ip address add dev myinterface fd00::1/64',
        'ip addr add ip/255.255.255.255 dev myinterface',
        'ip addr add ip/ffff:ffff:ffff:ffff:: dev myinterface',
        'ip -6 addr list myinterface'
      ],
      self.fakeCallAndRead.external_command_list)


class SlapGridPartitionMock:

  def __init__(self, partition):
    self.partition = partition
    self.instance_path = partition.path

  def getUserGroupId(self):
    return (0, 0)


class TestComputerWithCPUSet(SlapformatMixin):

  cpuset_path = "/tmp/cpuset/"
  task_write_mode = "at"  # append insted of write tasks PIDs for the tests

  def setUp(self):
    logging.getLogger("slapos.manager.cpuset").addHandler(
      logging.StreamHandler())

    super(TestComputerWithCPUSet, self).setUp()
    self.restoreOs()

    if os.path.isdir("/tmp/slapgrid/"):
      shutil.rmtree("/tmp/slapgrid/")
    os.mkdir("/tmp/slapgrid/")

    if os.path.isdir(self.cpuset_path):
      shutil.rmtree(self.cpuset_path)
    os.mkdir(self.cpuset_path)
    file_write("0,1-3",
               os.path.join(self.cpuset_path, "cpuset.cpus"))
    file_write("\n".join(("1000", "1001", "1002", "")),
               os.path.join(self.cpuset_path, "tasks"))
    self.cpu_list = [0, 1, 2, 3]

    global USER_LIST, INTERFACE_DICT
    USER_LIST = ['testuser']
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [
        {'addr': '127.0.0.1', 'broadcast': '127.0.255.255', 'netmask': '255.255.0.0'}],
      socket.AF_INET6: [
        {'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    from slapos.manager.cpuset import Manager
    self.orig_cpuset_path = Manager.cpuset_path
    self.orig_task_write_mode = Manager.task_write_mode
    Manager.cpuset_path = self.cpuset_path
    Manager.task_write_mode = self.task_write_mode

    self.computer = slapos.format.Computer('computer',
      software_user='testuser',
      instance_root='/tmp/slapgrid/instance_root',
      software_root='/tmp/slapgrid/software_root',
      interface=slapos.format.Interface(
        logger=self.logger, name='bridge', ipv4_local_network='127.0.0.1/16'),
      partition_list=[
          slapos.format.Partition(
            'partition', '/tmp/slapgrid/instance_root/part1', slapos.format.User('testuser'), [], tap=None),
        ],
      config={
        "manager_list": "cpuset",
        "power_user_list": "testuser root"
      }
    )
    # self.patchOs(self.logger)

  def tearDown(self):
    """Cleanup temporary test folders."""
    from slapos.manager.cpuset import Manager
    Manager.cpuset_path = self.orig_cpuset_path
    Manager.task_write_mode = self.orig_task_write_mode

    super(TestComputerWithCPUSet, self).tearDown()
    shutil.rmtree("/tmp/slapgrid/")
    if self.cpuset_path.startswith("/tmp"):
      shutil.rmtree(self.cpuset_path)
    logging.getLogger("slapos.manager.cpuset")

  def test_positive_cgroups(self):
    """Positive test of cgroups."""
    # Test parsing "cpuset.cpus" file
    self.assertEqual(self.computer._manager_list[0]._cpu_id_list(), self.cpu_list)
    # This should created per-cpu groups and move all tasks in CPU pool into cpu0
    self.computer.format(alter_network=False, alter_user=False)
    # Test files creation for exclusive CPUs
    for cpu_id in self.cpu_list:
      cpu_n_path = os.path.join(self.cpuset_path, "cpu" + str(cpu_id))
      self.assertEqual(str(cpu_id), file_content(os.path.join(cpu_n_path, "cpuset.cpus")))
      self.assertEqual("1", file_content(os.path.join(cpu_n_path, "cpuset.cpu_exclusive")))
      if cpu_id > 0:
        self.assertEqual("", file_content(os.path.join(cpu_n_path, "tasks")))

    # Test moving tasks from generic core to private core
    # request PID 1001 to be moved to its private CPU
    request_file_path = os.path.join(self.computer.partition_list[0].path,
                                     slapos.manager.cpuset.Manager.cpu_exclusive_file)
    file_write("1001\n", request_file_path)
    # Simulate slapos instance call to perform the actual movement
    self.computer._manager_list[0].instance(
      SlapGridPartitionMock(self.computer.partition_list[0]))
    # Simulate cgroup behaviour - empty tasks in the pool
    file_write("", os.path.join(self.cpuset_path, "tasks"))
    # Test that format moved all PIDs from CPU pool into CPU0
    tasks_at_cpu0 = file_content(os.path.join(self.cpuset_path, "cpu0", "tasks")).split()
    self.assertIn("1000", tasks_at_cpu0)
    # test if the moving suceeded into any provate CPUS (id>0)
    self.assertTrue(any("1001" in file_content(exclusive_task)
                        for exclusive_task in glob.glob(os.path.join(self.cpuset_path, "cpu[1-9]", "tasks"))))
    self.assertIn("1002", tasks_at_cpu0)
    # slapformat should remove successfully moved PIDs from the .slapos-cpu-exclusive file
    self.assertEqual("", file_content(request_file_path).strip())


class TestPartition(SlapformatMixin):

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
      'useradd -d /doesnotexistsyet -g doesnotexistsyet -s /bin/sh '\
        'doesnotexistsyet -r',
      'passwd -l doesnotexistsyet'
    ],
      self.fakeCallAndRead.external_command_list)

  def test_create_additional_groups(self):
    user = slapos.format.User('doesnotexistsyet', ['additionalgroup1',
      'additionalgroup2'])
    user.setPath('/doesnotexistsyet')
    user.create()

    self.assertEqual([
      'groupadd doesnotexistsyet',
      'useradd -d /doesnotexistsyet -g doesnotexistsyet -s /bin/sh -G '\
        'additionalgroup1,additionalgroup2 doesnotexistsyet -r',
      'passwd -l doesnotexistsyet'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_create_group_exists(self):
    global GROUP_LIST
    GROUP_LIST = ['testuser']
    user = slapos.format.User('testuser')
    user.setPath('/testuser')
    user.create()

    self.assertEqual([
      'useradd -d /testuser -g testuser -s /bin/sh testuser -r',
      'passwd -l testuser'
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
      'usermod -d /testuser -g testuser -s /bin/sh -G '\
        'additionalgroup1,additionalgroup2 testuser',
      'passwd -l testuser'
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
      'usermod -d /testuser -g testuser -s /bin/sh testuser',
      'passwd -l testuser'
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
      'usermod -d /testuser -g testuser -s /bin/sh testuser',
      'passwd -l testuser'
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


class TestSlapformatManagerLifecycle(SlapformatMixin):

  def test_partition_format(self):
    computer = slapos.format.Computer('computer',
                                      instance_root='/instance_root',
                                      software_root='software_root')
    manager = DummyManager()
    computer._manager_list = [manager]

    computer.format(alter_user=False, alter_network=False)

    self.assertEqual(manager.sequence,
                     ['format', 'formatTearDown'])


if __name__ == '__main__':
      unittest.main()
