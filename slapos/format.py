# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2011 Vifib SARL and Contributors. All Rights Reserved.
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
from optparse import OptionParser, Option
from xml_marshaller import xml_marshaller
import ConfigParser
import grp
import logging
import netaddr
import netifaces
import os
import pwd
import random
import slapos.slap as slap
import socket
import subprocess
import sys
import time

class OS(object):
  _os = os

  def __init__(self, config):
    self._dry_run = config.dry_run
    self._verbose = config.verbose
    self._logger = config.logger
    add = self._addWrapper
    add('chown')
    add('chmod')
    add('makedirs')
    add('mkdir')

  def _addWrapper(self, name):
    def wrapper(*args, **kw):
      if self._verbose:
        arg_list = [repr(x) for x in args] + [
          '%s=%r' % (x, y) for x, y in kw.iteritems()]
        self._logger.debug('%s(%s)' % (
          name,
          ', '.join(arg_list)
        ))
      if not self._dry_run:
        getattr(self._os, name)(*args, **kw)
    setattr(self, name, wrapper)

  def __getattr__(self, name):
    return getattr(self._os, name)

class UsageError(Exception):
  pass

class NoAddressOnInterface(Exception):
  """
  Exception raised if there's not address on the interface to construct IPv6
  address with.

  Attributes:
    brige: String, the name of the interface.
  """

  def __init__(self, interface):
    super(NoAddressOnInterface, self).__init__(
      'No IPv6 found on interface %s to construct IPv6 with.' % (interface, )
    )

class AddressGenerationError(Exception):
  """
  Exception raised if the generation of an IPv6 based on the prefix obtained
  from the interface failed.

  Attributes:
    addr: String, the invalid address the exception is raised for.
  """
  def __init__(self, addr):
    super(AddressGenerationError, self).__init__(
      'Generated IPv6 %s seems not to be a valid IP.' % addr
    )

def callAndRead(argument_list, raise_on_error=True):
  popen = subprocess.Popen(argument_list, stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT)
  result = popen.communicate()[0]
  if raise_on_error and popen.returncode != 0:
    raise ValueError('Issue during invoking %r, result was:\n%s' % (
      argument_list, result))
  return popen.returncode, result

def isGlobalScopeAddress(a):
  """Returns True if a is global scope IP v4/6 address"""
  ip = netaddr.IPAddress(a)
  return not ip.is_link_local() and not ip.is_loopback() and \
      not ip.is_reserved() and ip.is_unicast()

def netmaskToPrefixIPv4(netmask):
  """Convert string represented netmask to its integer prefix"""
  return netaddr.strategy.ipv4.netmask_to_prefix[
          netaddr.strategy.ipv4.str_to_int(netmask)]

def netmaskToPrefixIPv6(netmask):
  """Convert string represented netmask to its integer prefix"""
  return netaddr.strategy.ipv6.netmask_to_prefix[
          netaddr.strategy.ipv6.str_to_int(netmask)]

def _getDict(instance):
  """
  Serialize an object instance into dictionaries. List and dict will remains
  the same, basic type too. But encapsulated object will be returned as dict.
  Set, collections and other aren't handle for now.

  Args:
    instance: an object of any type.

  Returns:
    A dictionary if the given object wasn't a list, a list otherwise.
  """
  if isinstance(instance, list):
    return [_getDict(item) for item in instance]

  elif isinstance(instance, dict):
    result = {}
    for key in instance:
      result[key] = _getDict(instance[key])
    return result

  else:
    try:
      dikt = instance.__dict__
    except AttributeError:
      return instance
    result = {}
    for key, value in dikt.iteritems():
      result[key] = _getDict(value)
    return result

class Computer(object):
  "Object representing the computer"
  instance_root = None
  software_root = None

  def __init__(self, reference, interface=None, addr=None, netmask=None,
    ipv6_interface=None, software_user='slapsoft'):
    """
    Attributes:
      reference: String, the reference of the computer.
      interface: String, the name of the computer's used interface.
    """
    self.reference = str(reference)
    self.interface = interface
    self.partition_list = []
    self.address = addr
    self.netmask = netmask
    self.ipv6_interface = ipv6_interface
    self.software_user = software_user

  def __getinitargs__(self):
    return (self.reference, self.interface)

  def getAddress(self):
    """
    Return a list of the interface address not attributed to any partition, (which
    are therefore free for the computer itself).

    Returns:
      False if the interface isn't available, else the list of the free addresses.
    """
    if self.interface is None:
      return dict(addr=self.address, netmask=self.netmask)

    computer_partition_address_list = []
    for partition in self.partition_list:
      for address in partition.address_list:
        if netaddr.valid_ipv6(address['addr']):
          computer_partition_address_list.append(address['addr'])
    # Going through addresses of the computer's interface
    for address_dict in self.interface.getGlobalScopeAddressList():
      # Comparing with computer's partition addresses
      if address_dict['addr'] not in computer_partition_address_list:
        return address_dict

    # all addresses on interface are for partition, so lets add new one
    computer_tap = Tap('compdummy')
    computer_tap.createWithOwner(User('root'), attach_to_tap=True)
    self.interface.addTap(computer_tap)
    return self.interface.addAddr()

  def send(self, config):
    """
    Send a marshalled dictionary of the computer object serialized via_getDict.
    """

    slap_instance = slap.slap()
    connection_dict = {}
    if config.key_file and config.cert_file:
      connection_dict.update(
        key_file=config.key_file,
        cert_file=config.cert_file)
    slap_instance.initializeConnection(config.master_url,
      **connection_dict)
    slap_computer = slap_instance.registerComputer(self.reference)
    if config.dry_run:
      return
    return slap_computer.updateConfiguration(
        xml_marshaller.dumps(_getDict(self)))

  def dump(self, path_to_xml):
    """
    Dump the computer object to an xml file via xml_marshaller.

    Args:
      path_to_xml: String, path to the file to load.
      users: List of User, list of user needed to be add to the dump
          (even if they are not related to any tap interface).
    """

    computer_dict = _getDict(self)
    output_file = open(path_to_xml,'w')
    output_file.write(xml_marshaller.dumps(computer_dict))
    output_file.close()

  @classmethod
  def load(cls, path_to_xml, reference, ipv6_interface):
    """
    Create a computer object from a valid xml file.

    Arg:
      path_to_xml: String, a path to a valid file containing
          a valid configuration.

    Return:
      A Computer object.
    """

    dumped_dict = xml_marshaller.loads(open(path_to_xml).read())

    # Reconstructing the computer object from the xml
    computer = Computer(
        reference = reference,
        addr = dumped_dict['address'],
        netmask = dumped_dict['netmask'],
        ipv6_interface=ipv6_interface,
        software_user=dumped_dict.get('software_user', 'slapsoft'),
    )

    for partition_dict in dumped_dict['partition_list']:

      if partition_dict['user']:
        user = User(partition_dict['user']['name'])
      else:
        user = User('root')

      if partition_dict['tap']:
        tap = Tap(partition_dict['tap']['name'])
      else:
        tap = Tap(partition_dict['reference'])

      address_list = partition_dict['address_list']

      partition = Partition(
          reference = partition_dict['reference'],
          path = partition_dict['path'],
          user = user,
          address_list = address_list,
          tap = tap,
      )

      computer.partition_list.append(partition)

    return computer

  def construct(self, alter_user=True, alter_network=True, create_tap=True):
    """
    Construct the computer object as it is.
    """
    if alter_network and self.address is not None:
      self.interface.addAddr(self.address, self.netmask)

    for path in self.instance_root, self.software_root: 
      if not os.path.exists(path):
        os.makedirs(path, 0755)
      else:
        os.chmod(path, 0755)

    # own self.software_root by software user
    slapsoft = User(self.software_user)
    slapsoft.path = self.software_root
    if alter_user:
      slapsoft.create()
      slapsoft_pw = pwd.getpwnam(slapsoft.name)
      os.chown(self.software_root, slapsoft_pw.pw_uid, slapsoft_pw.pw_gid)
    os.chmod(self.software_root, 0755)

    try:
      for partition_index, partition in enumerate(self.partition_list):
        # Reconstructing User's
        partition.path = os.path.join(self.instance_root, partition.reference)
        partition.user.setPath(partition.path)
        partition.user.additional_group_list = [slapsoft.name]
        if alter_user:
          partition.user.create()

        # Reconstructing Tap
        if partition.user and partition.user.isAvailable():
          owner = partition.user
        else:
          owner = User('root')

        if alter_network and create_tap:
          # In case it has to be  attached to the TAP network device, only one
          # is necessary for the interface to assert carrier
          if self.interface.attach_to_tap and partition_index == 0:
            partition.tap.createWithOwner(owner, attach_to_tap=True)
          else:
            partition.tap.createWithOwner(owner)

          self.interface.addTap(partition.tap)

        # Reconstructing partition's directory
        partition.createPath(alter_user)

        # Reconstructing partition's address
        # There should be two addresses on each Computer Partition:
        #  * global IPv6
        #  * local IPv4, took from slapformat:ipv4_local_network
        if len(partition.address_list) == 0:
          # regenerate
          partition.address_list.append(self.interface.addIPv4LocalAddress())
          partition.address_list.append(self.interface.addAddr())
        elif alter_network:
          # regenerate list of addresses
          old_partition_address_list = partition.address_list
          partition.address_list = []
          if len(old_partition_address_list) != 2:
            raise ValueError('There should be exactly 2 stored addresses')
          if not any([netaddr.valid_ipv6(q['addr'])
              for q in old_partition_address_list]):
            raise ValueError('Not valid ipv6 addresses loaded')
          if not any([netaddr.valid_ipv4(q['addr'])
              for q in old_partition_address_list]):
            raise ValueError('Not valid ipv6 addresses loaded')
          for address in old_partition_address_list:
            if netaddr.valid_ipv6(address['addr']):
              partition.address_list.append(self.interface.addAddr(
                address['addr'],
                address['netmask']))
            elif netaddr.valid_ipv4(address['addr']):
              partition.address_list.append(self.interface.addIPv4LocalAddress(
                address['addr']))
            else:
              raise ValueError('Address %r is incorrect' % address['addr'])
    finally:
      if alter_network and create_tap and self.interface.attach_to_tap:
        try:
          self.partition_list[0].tap.detach()
        except IndexError:
          pass

class Partition(object):
  "Represent a computer partition"

  def __init__(self, reference, path, user, address_list, tap):
    """
    Attributes:
      reference: String, the name of the partition.
      path: String, the path to the partition folder.
      user: User, the user linked to this partition.
      address_list: List of associated IP addresses.
      tap: Tap, the tap interface linked to this partition.
    """

    self.reference = str(reference)
    self.path = str(path)
    self.user = user
    self.address_list = address_list or []
    self.tap = tap

  def __getinitargs__(self):
    return (self.reference, self.path, self.user, self.address_list, self.tap)

  def createPath(self, alter_user=True):
    """
    Create the directory of the partition, assign to the partition user and
    give it the 750 permission. In case if path exists just modifies it.
    """

    self.path = os.path.abspath(self.path)
    owner = self.user if self.user else User('root')
    if not os.path.exists(self.path):
      os.mkdir(self.path, 0750)
    if alter_user:
      owner_pw = pwd.getpwnam(owner.name)
      os.chown(self.path, owner_pw.pw_uid, owner_pw.pw_gid)
    os.chmod(self.path, 0750)

class User(object):
  "User: represent and manipulate a user on the system."
  path = None

  def __init__(self, user_name, additional_group_list=None):
    """
    Attributes:
        user_name: string, the name of the user, who will have is home in
    """
    self.name = str(user_name)
    self.additional_group_list = additional_group_list

  def __getinitargs__(self):
    return (self.name,)

  def setPath(self, path):
    self.path = path

  def create(self):
    """
    Create a user on the system who will be named after the self.name with its
    own group and directory.

    Returns:
        True: if the user creation went right
    """
    # XXX: This method shall be no-op in case if all is correctly setup
    #      This method shall check if all is correctly done
    #      This method shall not reset groups, just add them
    try:
      grp.getgrnam(self.name)
    except KeyError:
      callAndRead(['groupadd', self.name])

    user_parameter_list = ['-d', self.path, '-g', self.name, '-s',
      '/bin/false']
    if self.additional_group_list is not None:
      user_parameter_list.extend(['-G', ','.join(self.additional_group_list)])
    user_parameter_list.append(self.name)
    try:
      pwd.getpwnam(self.name)
    except KeyError:
      callAndRead(['useradd'] + user_parameter_list)
    else:
      callAndRead(['usermod'] + user_parameter_list)

    return True

  def isAvailable(self):
    """
    Determine the availability of a user on the system

    Return:
        True: if available
        False: otherwise
    """

    try:
      pwd.getpwnam(self.name)
      return True

    except KeyError:
      return False

import struct
import fcntl
import errno
import threading

class Tap(object):
  "Tap represent a tap interface on the system"
  IFF_TAP = 0x0002
  TUNSETIFF = 0x400454ca
  KEEP_TAP_ATTACHED_EVENT = threading.Event()

  def __init__(self, tap_name):
    """
    Attributes:
        tap_name: String, the name of the tap interface.
    """

    self.name = str(tap_name)

  def __getinitargs__(self):
    return (self.name,)

  def attach(self):
    """
    Attach to the TAP interface, meaning  that it just opens the TAP interface
    and wait for the caller to notify that it can be safely detached.

    Linux  distinguishes administrative  and operational  state of  an network
    interface.  The  former can be set  manually by running ``ip  link set dev
    <dev> up|down'', whereas the latter states that the interface can actually
    transmit  data (for  a wired  network interface,  it basically  means that
    there is  carrier, e.g.  the network  cable is plugged  into a  switch for
    example).

    In case of bridge:
    In order  to be able to check  the uniqueness of IPv6  address assigned to
    the bridge, the network interface  must be up from an administrative *and*
    operational point of view.

    However,  from  Linux  2.6.39,  the  bridge  reflects  the  state  of  the
    underlying device (e.g.  the bridge asserts carrier if at least one of its
    ports has carrier) whereas it  always asserted carrier before. This should
    work fine for "real" network interface,  but will not work properly if the
    bridge only binds TAP interfaces, which, from 2.6.36, reports carrier only
    and only if an userspace program is attached.
    """
    tap_fd = os.open("/dev/net/tun", os.O_RDWR)

    try:
      # Attach to the TAP interface which has previously been created
      fcntl.ioctl(tap_fd, self.TUNSETIFF,
                  struct.pack("16sI", self.name, self.IFF_TAP))

    except IOError, error:
      # If  EBUSY, it  means another  program is  already attached,  thus just
      # ignore it...
      if error.errno != errno.EBUSY:
        os.close(tap_fd)
        raise
    else:
      # Block until the  caller send an event stating that  the program can be
      # now detached safely,  thus bringing down the TAP  device (from 2.6.36)
      # and the bridge at the same time (from 2.6.39)
      self.KEEP_TAP_ATTACHED_EVENT.wait()
    finally:
      os.close(tap_fd)

  def detach(self):
    """
    Detach to the  TAP network interface by notifying  the thread which attach
    to the TAP and closing the TAP file descriptor
    """
    self.KEEP_TAP_ATTACHED_EVENT.set()

  def createWithOwner(self, owner, attach_to_tap=False):
    """
    Create a tap interface on the system.
    """

    # some systems does not have -p switch for tunctl
    #callAndRead(['tunctl', '-p', '-t', self.name, '-u', owner.name])
    check_file = '/sys/devices/virtual/net/%s/owner' % self.name
    owner_id = None
    if os.path.exists(check_file):
      owner_id = open(check_file).read().strip()
      try:
        owner_id = int(owner_id)
      except ValueError:
        pass
    if owner_id != pwd.getpwnam(owner.name).pw_uid:
      callAndRead(['tunctl', '-t', self.name, '-u', owner.name])
    callAndRead(['ip', 'link', 'set', self.name, 'up'])

    if attach_to_tap:
      threading.Thread(target=self.attach).start()

class Interface(object):
  "Interface represent a interface on the system"

  def __init__(self, name, ipv4_local_network, ipv6_interface=None):
    """
    Attributes:
        name: String, the name of the interface
    """

    self.name = str(name)
    self.ipv4_local_network = ipv4_local_network
    self.ipv6_interface = ipv6_interface

    # Attach to TAP  network interface, only if the  interface interface does not
    # report carrier
    _, result = callAndRead(['ip', 'addr', 'list', self.name])
    self.attach_to_tap = 'DOWN' in result.split('\n', 1)[0]

  def __getinitargs__(self):
    return (self.name,)

  def getIPv4LocalAddressList(self):
    """
    Returns currently configured local IPv4 addresses which are in
    ipv4_local_network
    """
    if not socket.AF_INET in netifaces.ifaddresses(self.name):
      return []
    return [dict(addr=q['addr'], netmask=q['netmask']) for q in
      netifaces.ifaddresses(self.name)[socket.AF_INET] if netaddr.IPAddress(
        q['addr'], 4) in netaddr.glob_to_iprange(
          netaddr.cidr_to_glob(self.ipv4_local_network))]

  def getGlobalScopeAddressList(self):
    """Returns currently configured global scope IPv6 addresses"""
    if self.ipv6_interface:
      interface_name = self.ipv6_interface
    else:
      interface_name = self.name
    try:
      address_list = [q
        for q in netifaces.ifaddresses(interface_name)[socket.AF_INET6]
        if isGlobalScopeAddress(q['addr'].split('%')[0])]
    except KeyError:
      raise ValueError("%s must have at least one IPv6 address assigned" % \
                         interface_name)
    # XXX: Missing implementation of Unique Local IPv6 Unicast Addresses as
    # defined in http://www.rfc-editor.org/rfc/rfc4193.txt
    # XXX: XXX: XXX: IT IS DISALLOWED TO IMPLEMENT link-local addresses as
    # Linux and BSD are possibly wrongly implementing it -- it is "too local"
    # it is impossible to listen or access it on same node
    # XXX: IT IS DISALLOWED to implement ad hoc solution like inventing node
    # local addresses or anything which does not exists in RFC!
    return address_list

  def getInterfaceList(self):
    """Returns list of interfaces already present on bridge"""
    interface_list = []
    _, result = callAndRead(['brctl', 'show'])
    in_interface = False
    for line in result.split('\n'):
      if len(line.split()) > 1:
        if self.name in line:
          interface_list.append(line.split()[-1])
          in_interface = True
          continue
        if in_interface:
          break
      elif in_interface:
        if line.strip():
          interface_list.append(line.strip())

    return interface_list

  def addTap(self, tap):
    """
    Add the tap interface tap to the bridge.

    Args:
      tap: Tap, the tap interface.
    """
    if tap.name not in self.getInterfaceList():
      callAndRead(['brctl', 'addif', self.name, tap.name])

  def _addSystemAddress(self, address, netmask, ipv6=True):
    """Adds system address to interface
    
    Returns True if address was added successfully.

    Returns False if there was issue.
    """
    if ipv6:
      address_string = '%s/%s' % (address, netmaskToPrefixIPv6(netmask))
      af = socket.AF_INET6
      if self.ipv6_interface:
        interface_name = self.ipv6_interface
      else:
        interface_name = self.name
    else:
      af = socket.AF_INET
      address_string = '%s/%s' % (address, netmaskToPrefixIPv4(netmask))
      interface_name = self.name

    # check if address is already took by any other interface
    for interface in netifaces.interfaces():
      if interface != interface_name:
        address_dict = netifaces.ifaddresses(interface)
        if af in address_dict:
          if address in [q['addr'].split('%')[0] for q in address_dict[af]]:
            return False

    if not af in netifaces.ifaddresses(interface_name) \
        or not address in [q['addr'].split('%')[0]
          for q in netifaces.ifaddresses(interface_name)[af]]:
      # add an address
      callAndRead(['ip', 'addr', 'add', address_string, 'dev', interface_name])
      # wait few moments
      time.sleep(2)
    # check existence on interface
    _, result = callAndRead(['ip', 'addr', 'list', interface_name])
    for l in result.split('\n'):
      if address in l:
        if 'tentative' in l:
          # duplicate, remove
          callAndRead(['ip', 'addr', 'del', address_string, 'dev',
            interface_name])
          return False
        # found and clean
        return True
    # even when added not found, this is bad...
    return False

  def _generateRandomIPv4Address(self, netmask):
    # no addresses found, generate new one
    # Try 10 times to add address, raise in case if not possible
    try_num = 10
    while try_num > 0:
      addr = random.choice([q for q in netaddr.glob_to_iprange(
        netaddr.cidr_to_glob(self.ipv4_local_network))]).format()
      if dict(addr=addr, netmask=netmask) not in \
          self.getIPv4LocalAddressList():
        # Checking the validity of the IPv6 address
        if self._addSystemAddress(addr, netmask, False):
          return dict(addr=addr, netmask=netmask)
        try_num -= 1

    raise AddressGenerationError(addr)

  def addIPv4LocalAddress(self, addr=None):
    """Adds local IPv4 address in ipv4_local_network"""
    netmask = '255.255.255.255'
    local_address_list = self.getIPv4LocalAddressList()
    if addr is None:
      return self._generateRandomIPv4Address(netmask)
    elif dict(addr=addr, netmask=netmask) not in local_address_list:
      if self._addSystemAddress(addr, netmask, False):
        return dict(addr=addr, netmask=netmask)
      else:
        return self._generateRandomIPv4Address(netmask)
    else:
      # confirmed to be configured
      return dict(addr=addr, netmask=netmask)

  def addAddr(self, addr = None, netmask = None):
    """
    Adds IP address to interface.

    If addr is specified and exists already on interface does nothing.

    If addr is specified and does not exists on interface, tries to add given
    address. If it is not possible (ex. because network changed) calculates new
    address.

    Args:
      addr: Wished address to be added to interface.
      netmask: Wished netmask to be used.

    Returns:
      Tuple of (address, netmask).

    Raises:
      AddressGenerationError: Couldn't construct valid address with existing
          one's on the interface.
      NoAddressOnInterface: There's no address on the interface to construct
          an address with.
    """
    # Getting one address of the interface as base of the next addresses
    if self.ipv6_interface:
      interface_name = self.ipv6_interface
    else:
      interface_name = self.name
    interface_addr_list = self.getGlobalScopeAddressList()

    # No address found
    if len(interface_addr_list) == 0:
      raise NoAddressOnInterface(interface_name)
    address_dict = interface_addr_list[0]

    if addr is not None:
      if dict(addr=addr, netmask=netmask) in interface_addr_list:
        # confirmed to be configured
        return dict(addr=addr, netmask=netmask)
      if netmask == address_dict['netmask']:
        # same netmask, so there is a chance to add good one
        interface_network = netaddr.ip.IPNetwork('%s/%s' % (address_dict['addr'],
          netmaskToPrefixIPv6(address_dict['netmask'])))
        requested_network = netaddr.ip.IPNetwork('%s/%s' % (addr,
          netmaskToPrefixIPv6(netmask)))
        if interface_network.network == requested_network.network:
          # same network, try to add
          if self._addSystemAddress(addr, netmask):
            # succeed, return it
            return dict(addr=addr, netmask=netmask)

    # Try 10 times to add address, raise in case if not possible
    try_num = 10
    netmask = address_dict['netmask']
    while try_num > 0:
      addr = ':'.join(address_dict['addr'].split(':')[:-1] + ['%x' % (
        random.randint(1, 65000), )])
      socket.inet_pton(socket.AF_INET6, addr)
      if dict(addr=addr, netmask=netmask) not in \
          self.getGlobalScopeAddressList():
        # Checking the validity of the IPv6 address
        if self._addSystemAddress(addr, netmask):
          return dict(addr=addr, netmask=netmask)
        try_num -= 1

    raise AddressGenerationError(addr)

class Parser(OptionParser):
  """
  Parse all arguments.
  """
  def __init__(self, usage=None, version=None):
    """
    Initialize all options possibles.
    """
    OptionParser.__init__(self, usage=usage, version=version,
                          option_list=[
      Option("-x", "--computer_xml",
             help="Path to file with computer's XML. If does not exists, "
                  "will be created",
             default=None,
             type=str),
      Option("-l", "--log_file",
             help="The path to the log file used by the script.",
             type=str),
      Option("-i", "--input_definition_file",
             help="Path to file to read definition of computer instead of "
             "declaration. Using definition file allows to disable "
             "'discovery' of machine services and allows to define computer "
             "configuration in fully controlled manner.",
             type=str),
      Option("-o", "--output_definition_file",
             help="Path to file to write definition of computer from "
             "declaration.",
             type=str),
      Option("-n", "--dry_run",
             help="Don't actually do anything.",
             default=False,
             action="store_true"),
      Option("-b", "--no_bridge",
             help="Don't use bridge but use real interface like eth0.",
             default=False,
             action="store_true"),
      Option("-v", "--verbose",
             default=False,
             action="store_true",
             help="Verbose output."),
      Option("-c", "--console",
             default=False,
             action="store_true",
             help="Console output."),
      Option('--alter_user', choices=['True', 'False'],
        help="Shall slapformat alter user database [default: True]"),
      Option('--alter_network', choices=['True', 'False'],
        help="Shall slapformat alter network configuration [default: True]"),
      ])

  def check_args(self, args):
    """
    Check arguments
    """
    if args:
      (options, args) = self.parse_args(list(args))
    else:
      (options, args) = self.parse_args()
    if len(args) != 1:
      self.error("Incorrect number of arguments")
    return options, args[0]

def run(config):
  # Define the computer
  if config.input_definition_file:
    filepath = os.path.abspath(config.input_definition_file)
    config.logger.info('Using definition file %r' % filepath)
    computer_definition = ConfigParser.RawConfigParser({
      'software_user': 'slapsoft',
    })
    computer_definition.read(filepath)
    interface = None
    address = None
    netmask = None
    if computer_definition.has_option('computer', 'address'):
      address, netmask = computer_definition.get('computer',
        'address').split('/')
    if config.alter_network and config.interface_name is not None \
        and config.ipv4_local_network is not None:
      interface = Interface(config.interface_name, config.ipv4_local_network,
        config.ipv6_interface)
    computer = Computer(
        reference=config.computer_id,
        interface=interface,
        addr=address,
        netmask=netmask,
        ipv6_interface=config.ipv6_interface,
        software_user=computer_definition.get('computer', 'software_user'),
      )
    partition_list = []
    for partition_number in range(int(config.partition_amount)):
      section = 'partition_%s' % partition_number
      user = User(computer_definition.get(section, 'user'))
      address_list = []
      for a in computer_definition.get(section, 'address').split():
        address, netmask = a.split('/')
        address_list.append(dict(addr=address, netmask=netmask))
      tap = Tap(computer_definition.get(section, 'network_interface'))
      partition_list.append(Partition(reference=computer_definition.get(
        section, 'pathname'),
          path=os.path.join(config.instance_root, computer_definition.get(
            section, 'pathname')),
          user=user,
          address_list=address_list,
          tap=tap,
          ))
    computer.partition_list = partition_list
  else:
    # no definition file, figure out computer
    if os.path.exists(config.computer_xml):
      config.logger.info('Loading previous computer data from %r' % (
        config.computer_xml, ))
      computer = Computer.load(config.computer_xml,
        reference=config.computer_id, ipv6_interface=config.ipv6_interface)
      # Connect to the interface defined by the configuration
      computer.interface = Interface(config.interface_name, config.ipv4_local_network,
          config.ipv6_interface)
    else:
      # If no pre-existent configuration found, creating a new computer object
      config.logger.warning('Creating new data computer with id %r' % (
        config.computer_id, ))
      computer = Computer(
        reference=config.computer_id,
        interface=Interface(config.interface_name, config.ipv4_local_network,
          config.ipv6_interface),
        addr=None,
        netmask=None,
        ipv6_interface=config.ipv6_interface,
        software_user=config.software_user,
      )

    partition_amount = int(config.partition_amount)
    existing_partition_amount = len(computer.partition_list)
    if existing_partition_amount > partition_amount:
      raise ValueError('Requested amount of computer partitions (%s) is lower '
          'then already configured (%s), cannot continue' % (partition_amount,
            len(computer.partition_list)))

    config.logger.info('Adding %s new partitions' %
        (partition_amount-existing_partition_amount))
    for nb_iter in range(existing_partition_amount, partition_amount):
      # add new ones
      user = User("%s%s" % (config.user_base_name, nb_iter))

      tap = Tap("%s%s" % (config.tap_base_name, nb_iter))

      path = os.path.join(config.instance_root, "%s%s" % (
                           config.partition_base_name, nb_iter))
      computer.partition_list.append(
        Partition(
          reference="%s%s" % (config.partition_base_name, nb_iter),
          path=path,
          user=user,
          address_list=None,
          tap=tap,
          ))

  computer.instance_root = config.instance_root
  computer.software_root = config.software_root
  config.logger.info('Updating computer')
  address = computer.getAddress()
  computer.address = address['addr']
  computer.netmask = address['netmask']

  if config.output_definition_file:
    computer_definition = ConfigParser.RawConfigParser()
    computer_definition.add_section('computer')
    if computer.address is not None and computer.netmask is not None:
      computer_definition.set('computer', 'address', '/'.join(
        [computer.address, computer.netmask]))
    partition_number = 0
    for partition in computer.partition_list:
      section = 'partition_%s' % partition_number
      computer_definition.add_section(section)
      address_list = []
      for address in partition.address_list:
        address_list.append('/'.join([address['addr'], address['netmask']]))
      computer_definition.set(section, 'address', ' '.join(address_list))
      computer_definition.set(section, 'user', partition.user.name)
      computer_definition.set(section, 'user', partition.user.name)
      computer_definition.set(section, 'network_interface', partition.tap.name)
      computer_definition.set(section, 'pathname', partition.reference)
      partition_number += 1
    filepath = os.path.abspath(config.output_definition_file)
    computer_definition.write(open(filepath, 'w'))
    config.logger.info('Stored computer definition in %r' % filepath)
  computer.construct(alter_user=config.alter_user,
      alter_network=config.alter_network, create_tap=not config.no_bridge)

  # Dumping and sending to the erp5 the current configuration
  if not config.dry_run:
    computer.dump(config.computer_xml)
  config.logger.info('Posting information to %r' % config.master_url)
  computer.send(config)

class Config(object):
  key_file = None
  cert_file = None
  alter_network = None
  alter_user = None
  computer_xml = None
  logger = None
  log_file = None
  verbose = None
  dry_run = None
  console = None
  software_user = None

  @staticmethod
  def checkRequiredBinary(binary_list):
    missing_binary_list = []
    for b in binary_list:
      try:
        callAndRead([b])
      except ValueError:
        pass
      except OSError:
        missing_binary_list.append(b)
    if missing_binary_list:
      raise UsageError('Some required binaries are missing or not '
          'functional: %s' % (','.join(missing_binary_list), ))

  def setConfig(self, option_dict, configuration_file_path):
    """
    Set options given by parameters.
    """
    self.key_file = None
    self.cert_file = None
    # Set options parameters
    for option, value in option_dict.__dict__.items():
      setattr(self, option, value)

    # Load configuration file
    configuration_parser = ConfigParser.SafeConfigParser()
    configuration_parser.read(configuration_file_path)
    # Merges the arguments and configuration
    for section in ("slapformat", "slapos"):
      configuration_dict = dict(configuration_parser.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])

    # setup some nones
    for parameter in ['interface_name', 'partition_base_name', 'user_base_name',
        'tap_base_name', 'ipv4_local_network', 'ipv6_interface']:
      if getattr(self, parameter, None) is None:
        setattr(self, parameter, None)
        
    # Backward compatibility
    if not getattr(self, "interface_name", None) \
        and getattr(self, "bridge_name", None):
      setattr(self, "interface_name", self.bridge_name)

    # Set defaults lately
    if self.alter_network is None:
      self.alter_network = 'True'
    if self.alter_user is None:
      self.alter_user = 'True'
    if self.software_user is None:
      self.software_user = 'slapsoft'

    # set up logging
    self.logger = logging.getLogger("slapformat")
    self.logger.setLevel(logging.INFO)
    if self.console:
      self.logger.addHandler(logging.StreamHandler())

    # Convert strings to booleans
    root_needed = False
    for o in ['alter_network', 'alter_user']:
      if getattr(self, o).lower() == 'true':
        root_needed = True
        setattr(self, o, True)
      elif getattr(self, o).lower() == 'false':
        setattr(self, o, False)
      else:
        message = 'Option %r needs to be "True" or "False", wrong value: ' \
            '%r' % (o, getattr(self, o))
        self.logger.error(message)
        raise UsageError(message)

    if not self.dry_run:
      if self.alter_user:
        self.checkRequiredBinary(['groupadd', 'useradd', 'usermod'])
      if self.alter_network:
        self.checkRequiredBinary(['ip', 'tunctl'])
    # Required, even for dry run
    if self.alter_network:
      self.checkRequiredBinary(['brctl'])

    if self.dry_run:
      root_needed = False
    
    # check root
    if root_needed and os.getuid() != 0:
      message = "Root rights are needed"
      self.logger.error(message)
      raise UsageError(message)

    if self.log_file:
      if not os.path.isdir(os.path.dirname(self.log_file)):
        # fallback to console only if directory for logs does not exists and
        # continue to run
        raise ValueError('Please create directory %r to store %r log file' % (
          os.path.dirname(self.log_file), self.log_file))
      else:
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - "
          "%(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(file_handler)
        self.logger.info('Configured logging to file %r' % self.log_file)
    # Check mandatory options
    for parameter in ('computer_id', 'instance_root', 'master_url',
                      'software_root', 'computer_xml'):
      if not getattr(self, parameter, None):
        raise UsageError("Parameter '%s' is not defined." % parameter)

    self.logger.info("Started.")
    if self.verbose:
      self.logger.setLevel(logging.DEBUG)
      self.logger.debug("Verbose mode enabled.")
    if self.dry_run:
      self.logger.info("Dry-run mode enabled.")
    if self.no_bridge:
      self.logger.info("No-bridge mode enabled.")

    # Calculate path once
    self.computer_xml = os.path.abspath(self.computer_xml)


def main(*args):
  "Run default configuration."
  global os
  global callAndRead
  real_callAndRead = callAndRead
  usage = "usage: %s [options] CONFIGURATION_FILE" % sys.argv[0]

  # Parse arguments
  options, configuration_file_path = Parser(usage=usage).check_args(args)
  config = Config()
  try:
    config.setConfig(options, configuration_file_path)
  except UsageError, err:
    print >>sys.stderr, err.message
    print >>sys.stderr, "For help use --help"
    sys.exit(1)
  os = OS(config)
  if config.dry_run:
    def dry_callAndRead(argument_list, raise_on_error=True):
      if argument_list == ['brctl', 'show']:
        return real_callAndRead(argument_list, raise_on_error)
      else:
        return 0, ''
    callAndRead = dry_callAndRead
    real_addSystemAddress = Interface._addSystemAddress
    def fake_addSystemAddress(*args, **kw):
      real_addSystemAddress(*args, **kw)
      # Fake success
      return True
    Interface._addSystemAddress = fake_addSystemAddress
    def fake_getpwnam(user):
      class result(object):
        pw_uid = 12345
        pw_gid = 54321
      return result
    pwd.getpwnam = fake_getpwnam
  else:
    dry_callAndRead = real_callAndRead
  if config.verbose:
    def logging_callAndRead(argument_list, raise_on_error=True):
      config.logger.debug(' '.join(argument_list))
      return dry_callAndRead(argument_list, raise_on_error)
    callAndRead = logging_callAndRead
  try:
    run(config)
  except:
    config.logger.exception('Uncaught exception:')
    raise
