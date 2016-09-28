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

import logging
import slapos.format
import slapos.util
import unittest

import netaddr
import socket

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
    computer = slapos.format.Computer('computer')
    self.assertEqual(computer.getAddress(), {'netmask': None, 'addr': None})

  @unittest.skip("Not implemented")
  def test_construct_empty(self):
    computer = slapos.format.Computer('computer')
    computer.construct()

  @unittest.skip("Not implemented")
  def test_construct_empty_prepared(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
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
      'useradd -d /software_root -g slapsoft slapsoft -r'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_user(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    computer.construct(alter_user=False)
    self.assertEqual([
      "makedirs('/instance_root', 493)",
      "makedirs('/software_root', 493)",
      "chmod('/software_root', 493)"],
      self.test_result.bucket)
    self.assertEqual(['ip addr list bridge'],
                     self.fakeCallAndRead.external_command_list)

  @unittest.skip("Not implemented")
  def test_construct_empty_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
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
      'useradd -d /software_root -g slapsoft slapsoft -r'
      ],
      self.fakeCallAndRead.external_command_list)

  def test_construct_empty_prepared_no_alter_network_user(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
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

  @unittest.skip("Not implemented")
  def test_construct_prepared(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
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
      'useradd -d /software_root -g slapsoft slapsoft -r',
      'groupadd testuser',
      'useradd -d /instance_root/partition -g testuser -G slapsoft testuser -r',
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
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    global USER_LIST
    USER_LIST = ['testuser']
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
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
      'tunctl -t tap -u testuser',
      'ip link set tap up',
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
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='iface',
                                        ipv4_local_network='127.0.0.1/16'),
                                        tap_gateway_interface='eth1')
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    global USER_LIST
    USER_LIST = ['testuser']
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
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
        'ip addr list iface',
        'tunctl -t tap -u testuser',
        'ip link set tap up',
        'ip route show 10.8.0.2',
        'route add -host 10.8.0.2 dev tap',
        'ip addr add ip/255.255.255.255 dev iface',
        'ip addr add ip/ffff:ffff:ffff:ffff:: dev iface',
        'ip -6 addr list iface'
      ],
      self.fakeCallAndRead.external_command_list)
    self.assertEqual(partition.tap.ipv4_addr, '10.8.0.2')
    self.assertEqual(partition.tap.ipv4_netmask, '255.255.255.0')
    self.assertEqual(partition.tap.ipv4_gateway, '10.8.0.1')
    self.assertEqual(partition.tap.ipv4_network, '10.8.0.0')

  @unittest.skip("Not implemented")
  def test_construct_prepared_no_alter_network(self):
    computer = slapos.format.Computer('computer',
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
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
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='bridge',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['bridge'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
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
      'ip addr list bridge',
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
      interface=slapos.format.Interface(logger=self.test_result,
                                        name='myinterface',
                                        ipv4_local_network='127.0.0.1/16'))
    computer.instance_root = '/instance_root'
    computer.software_root = '/software_root'
    partition = slapos.format.Partition('partition', '/part_path',
      slapos.format.User('testuser'), [], None)
    partition.tap = slapos.format.Tap('tap')
    computer.partition_list = [partition]
    global INTERFACE_DICT
    INTERFACE_DICT['myinterface'] = {
      socket.AF_INET: [{'addr': '192.168.242.77', 'broadcast': '127.0.0.1',
        'netmask': '255.255.255.0'}],
      socket.AF_INET6: [{'addr': '2a01:e35:2e27::e59c', 'netmask': 'ffff:ffff:ffff:ffff::'}]
    }

    computer.construct(use_unique_local_address_block=True, alter_user=False, create_tap=False)
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
      'ip address add dev myinterface fd00::1/64',
      'ip addr add ip/255.255.255.255 dev myinterface',
      'ip addr add ip/ffff:ffff:ffff:ffff:: dev myinterface',
      'ip -6 addr list myinterface'
    ],
      self.fakeCallAndRead.external_command_list)

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

if __name__ == '__main__':
      unittest.main()
