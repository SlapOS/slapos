# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
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

import ConfigParser
import errno
import fcntl
import grp
import json
import logging
import netaddr
import netifaces
import os
import pwd
import random
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
import zipfile

import lxml.etree
import xml_marshaller.xml_marshaller

from slapos.util import chownDirectory
from slapos.util import mkdir_p
import slapos.slap as slap


def prettify_xml(xml):
  root = lxml.etree.fromstring(xml)
  return lxml.etree.tostring(root, pretty_print=True)


class OS(object):
  """Wrap parts of the 'os' module to provide logging of performed actions."""

  _os = os

  def __init__(self, conf):
    self._dry_run = conf.dry_run
    self._logger = conf.logger
    add = self._addWrapper
    add('chown')
    add('chmod')
    add('makedirs')
    add('mkdir')

  def _addWrapper(self, name):
    def wrapper(*args, **kw):
      arg_list = [repr(x) for x in args] + [
          '%s=%r' % (x, y) for x, y in kw.iteritems()
      ]
      self._logger.debug('%s(%s)' % (name, ', '.join(arg_list)))
      if not self._dry_run:
        getattr(self._os, name)(*args, **kw)
    setattr(self, name, wrapper)

  def __getattr__(self, name):
    return getattr(self._os, name)


class UsageError(Exception):
  pass


class NoAddressOnInterface(Exception):
  """
  Exception raised if there is no address on the interface to construct IPv6
  address with.

  Attributes:
    brige: String, the name of the interface.
  """

  def __init__(self, interface):
    super(NoAddressOnInterface, self).__init__(
      'No IPv6 found on interface %s to construct IPv6 with.' % interface
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
  popen = subprocess.Popen(argument_list,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
  result = popen.communicate()[0]
  if raise_on_error and popen.returncode != 0:
    raise ValueError('Issue while invoking %r, result was:\n%s' % (
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


def _getDict(obj):
  """
  Serialize an object into dictionaries. List and dict will remains
  the same, basic type too. But encapsulated object will be returned as dict.
  Set, collections and other aren't handle for now.

  Args:
    obj: an object of any type.

  Returns:
    A dictionary if the given object wasn't a list, a list otherwise.
  """
  if isinstance(obj, list):
    return [_getDict(item) for item in obj]

  if isinstance(obj, dict):
    dikt = obj
  else:
    try:
      dikt = obj.__dict__
    except AttributeError:
      return obj

  return {
    key: _getDict(value)
    for key, value in dikt.iteritems()
    # do not attempt to serialize logger: it is both useless and recursive.
    if not isinstance(value, logging.Logger)
  }


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

  def getAddress(self, allow_tap=False):
    """
    Return a list of the interface address not attributed to any partition (which
    are therefore free for the computer itself).

    Returns:
      False if the interface isn't available, else the list of the free addresses.
    """
    if self.interface is None:
      return {'addr': self.address, 'netmask': self.netmask}

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

    if allow_tap:
      # all addresses on interface are for partition, so let's add new one
      computer_tap = Tap('compdummy')
      computer_tap.createWithOwner(User('root'), attach_to_tap=True)
      self.interface.addTap(computer_tap)
      return self.interface.addAddr()

    # Can't find address
    raise NoAddressOnInterface('No valid IPv6 found on %s.' % self.interface.name)

  def send(self, conf):
    """
    Send a marshalled dictionary of the computer object serialized via_getDict.
    """

    slap_instance = slap.slap()
    connection_dict = {}
    if conf.key_file and conf.cert_file:
      connection_dict['key_file'] = conf.key_file
      connection_dict['cert_file'] = conf.cert_file
    slap_instance.initializeConnection(conf.master_url,
                                       **connection_dict)
    slap_computer = slap_instance.registerComputer(self.reference)

    if conf.dry_run:
      return
    try:
      slap_computer.updateConfiguration(xml_marshaller.xml_marshaller.dumps(_getDict(self)))
    except slap.NotFoundError as error:
      raise slap.NotFoundError("%s\nERROR: This SlapOS node is not recognised by "
          "SlapOS Master and/or computer_id and certificates don't match. "
          "Please make sure computer_id of slapos.cfg looks "
          "like 'COMP-123' and is correct.\nError is : 404 Not Found." % error)

  def dump(self, path_to_xml, path_to_json, logger):
    """
    Dump the computer object to an xml file via xml_marshaller.

    Args:
      path_to_xml: String, path to the file to load.
      path_to_json: String, path to the JSON version to save.
    """

    computer_dict = _getDict(self)

    if path_to_json:
      with open(path_to_json, 'wb') as fout:
        fout.write(json.dumps(computer_dict, sort_keys=True, indent=2))

    new_xml = xml_marshaller.xml_marshaller.dumps(computer_dict)
    new_pretty_xml = prettify_xml(new_xml)

    path_to_archive = path_to_xml + '.zip'

    if os.path.exists(path_to_archive) and os.path.exists(path_to_xml):
      # the archive file exists, we only backup if something has changed
      with open(path_to_xml, 'rb') as fin:
        if fin.read() == new_pretty_xml:
          # computer configuration did not change, nothing to write
          return

    if os.path.exists(path_to_xml):
      try:
        self.backup_xml(path_to_archive, path_to_xml)
      except:
        # might be a corrupted zip file. let's move it out of the way and retry.
        shutil.move(path_to_archive,
                    path_to_archive + time.strftime('_broken_%Y%m%d-%H:%M'))
        try:
          self.backup_xml(path_to_archive, path_to_xml)
        except:
          # give up trying
          logger.exception("Can't backup %s:", path_to_xml)

    with open(path_to_xml, 'wb') as fout:
      fout.write(new_pretty_xml)

  def backup_xml(self, path_to_archive, path_to_xml):
    """
    Stores a copy of the current xml file to an historical archive.
    """
    xml_content = open(path_to_xml).read()
    saved_filename = os.path.basename(path_to_xml) + time.strftime('.%Y%m%d-%H:%M')

    with zipfile.ZipFile(path_to_archive, 'a') as archive:
      archive.writestr(saved_filename, xml_content, zipfile.ZIP_DEFLATED)

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

    dumped_dict = xml_marshaller.xml_marshaller.loads(open(path_to_xml).read())

    # Reconstructing the computer object from the xml
    computer = Computer(
        reference=reference,
        addr=dumped_dict['address'],
        netmask=dumped_dict['netmask'],
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
          reference=partition_dict['reference'],
          path=partition_dict['path'],
          user=user,
          address_list=address_list,
          tap=tap,
      )

      computer.partition_list.append(partition)

    return computer

  def _speedHackAddAllOldIpsToInterface(self):
    """
    Speed hack:
    Blindly add all IPs from existing configuration, just to speed up actual
    computer configuration later on.
    """
    # XXX-TODO: only add an address if it doesn't already exist.
    if self.ipv6_interface:
      interface_name = self.ipv6_interface
    elif self.interface:
      interface_name = self.interface.name
    else:
      return

    for partition in self.partition_list:
      try:
        for address in partition.address_list:
          try:
            netmask = netmaskToPrefixIPv6(address['netmask'])
          except:
            continue
          callAndRead(['ip', 'addr', 'add',
                       '%s/%s' % (address['addr'], netmask),
                       'dev', interface_name])
      except ValueError:
        pass

  def construct(self, alter_user=True, alter_network=True, create_tap=True):
    """
    Construct the computer object as it is.
    """
    if alter_network and self.address is not None:
      self.interface.addAddr(self.address, self.netmask)

    for path in self.instance_root, self.software_root:
      if not os.path.exists(path):
        os.makedirs(path, 0o755)
      else:
        os.chmod(path, 0o755)

    # own self.software_root by software user
    slapsoft = User(self.software_user)
    slapsoft.path = self.software_root
    if alter_user:
      slapsoft.create()
      slapsoft_pw = pwd.getpwnam(slapsoft.name)
      chownDirectory(slapsoft.path, slapsoft_pw.pw_uid, slapsoft_pw.pw_gid)
    os.chmod(self.software_root, 0o755)

    if alter_network:
      self._speedHackAddAllOldIpsToInterface()

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
        if not partition.address_list:
          # regenerate
          partition.address_list.append(self.interface.addIPv4LocalAddress())
          partition.address_list.append(self.interface.addAddr())
        elif alter_network:
          # regenerate list of addresses
          old_partition_address_list = partition.address_list
          partition.address_list = []
          if len(old_partition_address_list) != 2:
            raise ValueError(
              'There should be exactly 2 stored addresses. Got: %r' %
              (old_partition_address_list,))
          if not any(netaddr.valid_ipv6(q['addr'])
                     for q in old_partition_address_list):
            raise ValueError('Not valid ipv6 addresses loaded')
          if not any(netaddr.valid_ipv4(q['addr'])
                     for q in old_partition_address_list):
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
      os.mkdir(self.path, 0o750)
    if alter_user:
      owner_pw = pwd.getpwnam(owner.name)
      chownDirectory(self.path, owner_pw.pw_uid, owner_pw.pw_gid)
    os.chmod(self.path, 0o750)


class User(object):
  """User: represent and manipulate a user on the system."""

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
    grpname = 'grp_' + self.name if sys.platform == 'cygwin' else self.name
    try:
      grp.getgrnam(grpname)
    except KeyError:
      callAndRead(['groupadd', grpname])

    user_parameter_list = ['-d', self.path, '-g', self.name]
    if self.additional_group_list is not None:
      user_parameter_list.extend(['-G', ','.join(self.additional_group_list)])
    user_parameter_list.append(self.name)
    try:
      pwd.getpwnam(self.name)
    except KeyError:
      user_parameter_list.append('-r')
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
    and waits for the caller to notify that it can be safely detached.

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

    except IOError as error:
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
  """Represent a network interface on the system"""

  def __init__(self, logger, name, ipv4_local_network, ipv6_interface=None):
    """
    Attributes:
        name: String, the name of the interface
    """

    self.logger = logger
    self.name = str(name)
    self.ipv4_local_network = ipv4_local_network
    self.ipv6_interface = ipv6_interface

    # Attach to TAP  network interface, only if the  interface interface does not
    # report carrier
    _, result = callAndRead(['ip', 'addr', 'list', self.name])
    self.attach_to_tap = 'DOWN' in result.split('\n', 1)[0]

  # XXX no __getinitargs__, as instances of this class are never deserialized.

  def getIPv4LocalAddressList(self):
    """
    Returns currently configured local IPv4 addresses which are in
    ipv4_local_network
    """
    if not socket.AF_INET in netifaces.ifaddresses(self.name):
      return []
    return [
            {
                'addr': q['addr'],
                'netmask': q['netmask']
                }
            for q in netifaces.ifaddresses(self.name)[socket.AF_INET]
            if netaddr.IPAddress(q['addr'], 4) in netaddr.glob_to_iprange(
                netaddr.cidr_to_glob(self.ipv4_local_network))
            ]

  def getGlobalScopeAddressList(self):
    """Returns currently configured global scope IPv6 addresses"""
    if self.ipv6_interface:
      interface_name = self.ipv6_interface
    else:
      interface_name = self.name
    try:
      address_list = [
          q
          for q in netifaces.ifaddresses(interface_name)[socket.AF_INET6]
          if isGlobalScopeAddress(q['addr'].split('%')[0])
      ]
    except KeyError:
      raise ValueError("%s must have at least one IPv6 address assigned" %
                         interface_name)
    if sys.platform == 'cygwin':
      for q in address_list:
        q.setdefault('netmask', 'FFFF:FFFF:FFFF:FFFF::')
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
                           for q in netifaces.ifaddresses(interface_name)[af]
                           ]:
      # add an address
      callAndRead(['ip', 'addr', 'add', address_string, 'dev', interface_name])

      # Fake success for local ipv4
      if not ipv6:
        return True

      # wait few moments
      time.sleep(2)

    # Fake success for local ipv4
    if not ipv6:
      return True

    # check existence on interface for ipv6
    _, result = callAndRead(['ip', '-6', 'addr', 'list', interface_name])
    for l in result.split('\n'):
      if address in l:
        if 'tentative' in l:
          # duplicate, remove
          callAndRead(['ip', 'addr', 'del', address_string, 'dev', interface_name])
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
      if (dict(addr=addr, netmask=netmask) not in
            self.getIPv4LocalAddressList()):
        # Checking the validity of the IPv6 address
        if self._addSystemAddress(addr, netmask, False):
          return dict(addr=addr, netmask=netmask)
        try_num -= 1

    raise AddressGenerationError(addr)

  def addIPv4LocalAddress(self, addr=None):
    """Adds local IPv4 address in ipv4_local_network"""
    netmask = str(netaddr.IPNetwork(self.ipv4_local_network).netmask) if sys.platform == 'cygwin' \
             else '255.255.255.255'
    local_address_list = self.getIPv4LocalAddressList()
    if addr is None:
      return self._generateRandomIPv4Address(netmask)
    elif dict(addr=addr, netmask=netmask) not in local_address_list:
      if self._addSystemAddress(addr, netmask, False):
        return dict(addr=addr, netmask=netmask)
      else:
        self.logger.warning('Impossible to add old local IPv4 %s. Generating '
            'new IPv4 address.' % addr)
        return self._generateRandomIPv4Address(netmask)
    else:
      # confirmed to be configured
      return dict(addr=addr, netmask=netmask)

  def addAddr(self, addr=None, netmask=None):
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
          else:
            self.logger.warning('Impossible to add old public IPv6 %s. '
                'Generating new IPv6 address.' % addr)

    # Try 10 times to add address, raise in case if not possible
    try_num = 10
    netmask = address_dict['netmask']
    while try_num > 0:
      addr = ':'.join(address_dict['addr'].split(':')[:-1] + ['%x' % (
        random.randint(1, 65000), )])
      socket.inet_pton(socket.AF_INET6, addr)
      if (dict(addr=addr, netmask=netmask) not in
            self.getGlobalScopeAddressList()):
        # Checking the validity of the IPv6 address
        if self._addSystemAddress(addr, netmask):
          return dict(addr=addr, netmask=netmask)
        try_num -= 1

    raise AddressGenerationError(addr)


def parse_computer_definition(conf, definition_path):
  conf.logger.info('Using definition file %r' % definition_path)
  computer_definition = ConfigParser.RawConfigParser({
    'software_user': 'slapsoft',
  })
  computer_definition.read(definition_path)
  interface = None
  address = None
  netmask = None
  if computer_definition.has_option('computer', 'address'):
    address, netmask = computer_definition.get('computer', 'address').split('/')
  if (conf.alter_network and conf.interface_name is not None
        and conf.ipv4_local_network is not None):
    interface = Interface(logger=conf.logger,
                          name=conf.interface_name,
                          ipv4_local_network=conf.ipv4_local_network,
                          ipv6_interface=conf.ipv6_interface)
  computer = Computer(
      reference=conf.computer_id,
      interface=interface,
      addr=address,
      netmask=netmask,
      ipv6_interface=conf.ipv6_interface,
      software_user=computer_definition.get('computer', 'software_user'),
  )
  partition_list = []
  for partition_number in range(int(conf.partition_amount)):
    section = 'partition_%s' % partition_number
    user = User(computer_definition.get(section, 'user'))
    address_list = []
    for a in computer_definition.get(section, 'address').split():
      address, netmask = a.split('/')
      address_list.append(dict(addr=address, netmask=netmask))
    tap = Tap(computer_definition.get(section, 'network_interface'))
    partition = Partition(reference=computer_definition.get(section, 'pathname'),
                          path=os.path.join(conf.instance_root,
                                            computer_definition.get(section, 'pathname')),
                          user=user,
                          address_list=address_list,
                          tap=tap)
    partition_list.append(partition)
  computer.partition_list = partition_list
  return computer


def parse_computer_xml(conf, xml_path):
  interface = Interface(logger=conf.logger,
                        name=conf.interface_name,
                        ipv4_local_network=conf.ipv4_local_network,
                        ipv6_interface=conf.ipv6_interface)

  if os.path.exists(xml_path):
    conf.logger.debug('Loading previous computer data from %r' % xml_path)
    computer = Computer.load(xml_path,
                             reference=conf.computer_id,
                             ipv6_interface=conf.ipv6_interface)
    # Connect to the interface defined by the configuration
    computer.interface = interface
  else:
    # If no pre-existent configuration found, create a new computer object
    conf.logger.warning('Creating new computer data with id %r', conf.computer_id)
    computer = Computer(
      reference=conf.computer_id,
      interface=interface,
      addr=None,
      netmask=None,
      ipv6_interface=conf.ipv6_interface,
      software_user=conf.software_user,
    )

  partition_amount = int(conf.partition_amount)
  existing_partition_amount = len(computer.partition_list)

  if partition_amount < existing_partition_amount:
    conf.logger.critical('Requested amount of computer partitions (%s) is lower '
                         'than already configured (%s), cannot continue',
                         partition_amount, existing_partition_amount)
    sys.exit(1)
  elif partition_amount > existing_partition_amount:
    conf.logger.info('Adding %s new partitions',
                     partition_amount - existing_partition_amount)

  for i in range(existing_partition_amount, partition_amount):
    # add new partitions
    partition = Partition(
        reference='%s%s' % (conf.partition_base_name, i),
        path=os.path.join(conf.instance_root, '%s%s' % (
          conf.partition_base_name, i)),
        user=User('%s%s' % (conf.user_base_name, i)),
        address_list=None,
        tap=Tap('%s%s' % (conf.tap_base_name, i))
    )
    computer.partition_list.append(partition)

  return computer


def write_computer_definition(conf, computer):
  computer_definition = ConfigParser.RawConfigParser()
  computer_definition.add_section('computer')
  if computer.address is not None and computer.netmask is not None:
    computer_definition.set('computer', 'address', '/'.join(
      [computer.address, computer.netmask]))
  for partition_number, partition in enumerate(computer.partition_list):
    section = 'partition_%s' % partition_number
    computer_definition.add_section(section)
    address_list = []
    for address in partition.address_list:
      address_list.append('/'.join([address['addr'], address['netmask']]))
    computer_definition.set(section, 'address', ' '.join(address_list))
    computer_definition.set(section, 'user', partition.user.name)
    computer_definition.set(section, 'network_interface', partition.tap.name)
    computer_definition.set(section, 'pathname', partition.reference)
  computer_definition.write(open(conf.output_definition_file, 'w'))
  conf.logger.info('Stored computer definition in %r' % conf.output_definition_file)


def random_delay(conf):
  # Add delay between 0 and 1 hour
  # XXX should be the contrary: now by default, and cron should have
  # --maximal-delay=3600
  if not conf.now:
    duration = float(60 * 60) * random.random()
    conf.logger.info('Sleeping for %s seconds. To disable this feature, '
                     'use with --now parameter in manual.' % duration)
    time.sleep(duration)


def do_format(conf):
  random_delay(conf)

  if conf.input_definition_file:
    computer = parse_computer_definition(conf, conf.input_definition_file)
  else:
    # no definition file, figure out computer
    computer = parse_computer_xml(conf, conf.computer_xml)

  computer.instance_root = conf.instance_root
  computer.software_root = conf.software_root
  conf.logger.info('Updating computer')
  address = computer.getAddress(conf.create_tap)
  computer.address = address['addr']
  computer.netmask = address['netmask']

  if conf.output_definition_file:
    write_computer_definition(conf, computer)

  computer.construct(alter_user=conf.alter_user,
                     alter_network=conf.alter_network,
                     create_tap=conf.create_tap)

  if getattr(conf, 'certificate_repository_path', None):
    mkdir_p(conf.certificate_repository_path, mode=0o700)

  # Dumping and sending to the erp5 the current configuration
  if not conf.dry_run:
    computer.dump(path_to_xml=conf.computer_xml,
                  path_to_json=conf.computer_json,
                  logger=conf.logger)
  conf.logger.info('Posting information to %r' % conf.master_url)
  computer.send(conf)
  conf.logger.info('slapos successfully prepared the computer.')


class FormatConfig(object):
  key_file = None
  cert_file = None
  alter_network = None
  alter_user = None
  create_tap = None
  computer_xml = None
  computer_json = None
  input_definition_file = None
  log_file = None
  output_definition_file = None
  dry_run = None
  software_user = None

  def __init__(self, logger):
    self.logger = logger

  @staticmethod
  def checkRequiredBinary(binary_list):
    missing_binary_list = []
    for b in binary_list:
      if type(b) != type([]):
        b = [b]
      try:
        callAndRead(b)
      except ValueError:
        pass
      except OSError:
        missing_binary_list.append(b[0])
    if missing_binary_list:
      raise UsageError('Some required binaries are missing or not '
          'functional: %s' % (','.join(missing_binary_list), ))

  def mergeConfig(self, args, configp):
    """
    Set options given by parameters.
    Must be executed before setting up the logger.
    """
    self.key_file = None
    self.cert_file = None

    # Set argument parameters
    for key, value in args.__dict__.items():
      setattr(self, key, value)

    # Merges the arguments and configuration
    for section in ("slapformat", "slapos"):
      configuration_dict = dict(configp.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])

  def setConfig(self):
    # setup some nones
    for parameter in ['interface_name', 'partition_base_name', 'user_base_name',
          'tap_base_name', 'ipv4_local_network', 'ipv6_interface']:
      if getattr(self, parameter, None) is None:
        setattr(self, parameter, None)

    # Backward compatibility
    if not getattr(self, "interface_name", None) \
          and getattr(self, "bridge_name", None):
      setattr(self, "interface_name", self.bridge_name)
      self.logger.warning('bridge_name option is deprecated and should be '
          'replaced by interface_name.')
    if not getattr(self, "create_tap", None) \
          and getattr(self, "no_bridge", None):
      setattr(self, "create_tap", not self.no_bridge)
      self.logger.warning('no_bridge option is deprecated and should be '
          'replaced by create_tap.')

    # Set defaults lately
    if self.alter_network is None:
      self.alter_network = 'True'
    if self.alter_user is None:
      self.alter_user = 'True'
    if self.software_user is None:
      self.software_user = 'slapsoft'
    if self.create_tap is None:
      self.create_tap = True

    # Convert strings to booleans
    for option in ['alter_network', 'alter_user', 'create_tap']:
      attr = getattr(self, option)
      if isinstance(attr, str):
        if attr.lower() == 'true':
          root_needed = True
          setattr(self, option, True)
        elif attr.lower() == 'false':
          setattr(self, option, False)
        else:
          message = 'Option %r needs to be "True" or "False", wrong value: ' \
              '%r' % (option, getattr(self, option))
          self.logger.error(message)
          raise UsageError(message)

    if not self.dry_run:
      if self.alter_user:
        self.checkRequiredBinary(['groupadd', 'useradd', 'usermod'])
      if self.create_tap:
        self.checkRequiredBinary([['tunctl', '-d']])
      if self.alter_network:
        self.checkRequiredBinary(['ip'])

    # Required, even for dry run
    if self.alter_network and self.create_tap:
      self.checkRequiredBinary(['brctl'])

    # Check mandatory options
    for parameter in ('computer_id', 'instance_root', 'master_url',
                      'software_root', 'computer_xml'):
      if not getattr(self, parameter, None):
        raise UsageError("Parameter '%s' is not defined." % parameter)

    # Check existence of SSL certificate files, if defined
    for attribute in ['key_file', 'cert_file', 'master_ca_file']:
      file_location = getattr(self, attribute, None)
      if file_location is not None:
        if not os.path.exists(file_location):
          self.logger.fatal('File %r does not exist or is not readable.' %
              file_location)
          sys.exit(1)

    self.logger.debug('Started.')
    if self.dry_run:
      self.logger.info("Dry-run mode enabled.")
    if self.create_tap:
      self.logger.info("Tap creation mode enabled.")

    # Calculate path once
    self.computer_xml = os.path.abspath(self.computer_xml)

    if self.input_definition_file:
      self.input_definition_file = os.path.abspath(self.input_definition_file)

    if self.output_definition_file:
      self.output_definition_file = os.path.abspath(self.output_definition_file)


def tracing_monkeypatch(conf):
  """Substitute os module and callAndRead function with tracing wrappers."""
  global os
  global callAndRead

  real_callAndRead = callAndRead

  os = OS(conf)
  if conf.dry_run:
    def dry_callAndRead(argument_list, raise_on_error=True):
      if argument_list == ['brctl', 'show']:
        return real_callAndRead(argument_list, raise_on_error)
      else:
        return 0, ''
    callAndRead = dry_callAndRead

    def fake_getpwnam(user):
      class result(object):
        pw_uid = 12345
        pw_gid = 54321
      return result
    pwd.getpwnam = fake_getpwnam
  else:
    dry_callAndRead = real_callAndRead

  def logging_callAndRead(argument_list, raise_on_error=True):
    conf.logger.debug(' '.join(argument_list))
    return dry_callAndRead(argument_list, raise_on_error)
  callAndRead = logging_callAndRead
