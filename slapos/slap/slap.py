# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
__all__ = ["slap", "ComputerPartition", "Computer", "SoftwareRelease",
           "Supply", "OpenOrder", "NotFoundError", "Unauthorized",
           "ResourceNotReady"]

from interface import slap as interface
from xml_marshaller import xml_marshaller
import httplib
import socket
import ssl
import urllib
import urlparse
import zope.interface

"""
Simple, easy to (un)marshall classes for slap client/server communication
"""

# httplib.HTTPSConnection with key verification
class HTTPSConnectionCA(httplib.HTTPSConnection):
  """Patched version of HTTPSConnection which verifies server certificate"""
  def __init__(self, *args, **kwargs):
    self.ca_file = kwargs.pop('ca_file')
    if self.ca_file is None:
      raise ValueError('ca_file is required argument.')
    httplib.HTTPSConnection.__init__(self, *args, **kwargs)

  def connect(self):
    "Connect to a host on a given (SSL) port and verify its certificate."

    sock = socket.create_connection((self.host, self.port),
                                    self.timeout, self.source_address)
    if self._tunnel_host:
      self.sock = sock
      self._tunnel()
    self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
        ca_certs=self.ca_file, cert_reqs=ssl.CERT_REQUIRED)


class SlapDocument:
  pass

class SoftwareRelease(SlapDocument):
  """
  Contains Software Release information
  """

  zope.interface.implements(interface.ISoftwareRelease)

  def __init__(self, software_release=None, computer_guid=None, **kw):
    """
    Makes easy initialisation of class parameters

    XXX **kw args only kept for compatibility
    """
    self._software_instance_list = []
    if software_release is not None:
      software_release = software_release.encode('UTF-8')
    self._software_release = software_release
    self._computer_guid = computer_guid

  def __getinitargs__(self):
    return (self._software_release, self._computer_guid, )

  def error(self, error_log):
    # Does not follow interface
    self._connection_helper.POST('/softwareReleaseError', {
      'url': self._software_release,
      'computer_id' : self._computer_guid,
      'error_log': error_log})

  def getURI(self):
    return self._software_release

  def available(self):
    self._connection_helper.POST('/availableSoftwareRelease', {
      'url': self._software_release, 
      'computer_id': self._computer_guid})

  def building(self):
    self._connection_helper.POST('/buildingSoftwareRelease', {
      'url': self._software_release, 
      'computer_id': self._computer_guid})

# XXX What is this SoftwareInstance class?
class SoftwareInstance(SlapDocument):
  """
  Contains Software Instance information
  """

  def __init__(self, **kwargs):
    """
    Makes easy initialisation of class parameters
    """
    for k, v in kwargs.iteritems():
      setattr(self, k, v)

"""Exposed exceptions"""
# XXX Why do we need to expose exceptions?
class ResourceNotReady(Exception):
  pass

class ServerError(Exception):
  pass

class NotFoundError(Exception):
  zope.interface.implements(interface.INotFoundError)

class Unauthorized(Exception):
  zope.interface.implements(interface.IUnauthorized)

class Supply(SlapDocument):

  zope.interface.implements(interface.ISupply)

  def supply(self, software_release, computer_guid=None):
    self._connection_helper.POST('/supplySupply', {
      'url': software_release,
      'computer_id': computer_guid})

class OpenOrder(SlapDocument):

  zope.interface.implements(interface.IOpenOrder)

  def request(self, software_release, partition_reference,
      partition_parameter_kw=None, software_type=None, filter_kw=None,
      state=None, shared=False):
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    if filter_kw is None:
      filter_kw = {}
    request_dict = {
        'software_release': software_release,
        'partition_reference': partition_reference,
        'partition_parameter_xml': xml_marshaller.dumps(partition_parameter_kw),
        'filter_xml': xml_marshaller.dumps(filter_kw),
        'state': xml_marshaller.dumps(state),
        'shared_xml': xml_marshaller.dumps(shared),
      }
    if software_type is not None:
      request_dict['software_type'] = software_type
    try:
      self._connection_helper.POST('/requestComputerPartition', request_dict)
    except ResourceNotReady:
      return ComputerPartition(request_dict=request_dict)
    else:
      xml = self._connection_helper.response.read()
      software_instance = xml_marshaller.loads(xml)
      computer_partition = ComputerPartition(
        software_instance.slap_computer_id.encode('UTF-8'),
        software_instance.slap_computer_partition_id.encode('UTF-8'))
      if shared:
        computer_partition._synced = True
        computer_partition._connection_dict = software_instance._connection_dict
        computer_partition._parameter_dict = software_instance._parameter_dict
      return computer_partition

def _syncComputerInformation(func):
  """
  Synchronize computer object with server information
  """
  def decorated(self, *args, **kw):
    computer = self._connection_helper.getComputerInformation(self._computer_id)
    for key, value in computer.__dict__.items():
      if isinstance(value, unicode):
        # convert unicode to utf-8
        setattr(self, key, value.encode('utf-8'))
      else:
        setattr(self, key, value)
    return func(self, *args, **kw)
  return decorated 

class Computer(SlapDocument):

  zope.interface.implements(interface.IComputer)

  def __init__(self, computer_id):
    self._computer_id = computer_id

  def __getinitargs__(self):
    return (self._computer_id, )

  @_syncComputerInformation
  def getSoftwareReleaseList(self):
    """
    Returns the list of software release which has to be supplied by the
    computer.

    Raise an INotFoundError if computer_guid doesn't exist.
    """
    return self._software_release_list

  @_syncComputerInformation
  def getComputerPartitionList(self):
    return [x for x in self._computer_partition_list if x._need_modification]

  def reportUsage(self, computer_usage):
    if computer_usage == "":
      return
    self._connection_helper.POST('/useComputer', {
      'computer_id': self._computer_id,
      'use_string': computer_usage})

  def updateConfiguration(self, xml):
    self._connection_helper.POST(
        '/loadComputerConfigurationFromXML', { 'xml' : xml })
    return self._connection_helper.response.read()

  def bang(self, message):
    self._connection_helper.POST('/computerBang', {
      'computer_id': self._computer_id,
      'message': message})

def _syncComputerPartitionInformation(func):
  """
  Synchronize computer partition object with server information
  """
  def decorated(self, *args, **kw):
    if getattr(self, '_synced', 0):
      return func(self, *args, **kw)
    computer = self._connection_helper.getComputerInformation(self._computer_id)
    found_computer_partition = None
    for computer_partition in computer._computer_partition_list:
      if computer_partition.getId() == self.getId():
        found_computer_partition = computer_partition
        break
    if found_computer_partition is None:
      raise NotFoundError("No software release information for partition %s" %
          self.getId())
    else:
      for key, value in found_computer_partition.__dict__.items():
        if isinstance(value, unicode):
          # convert unicode to utf-8
          setattr(self, key, value.encode('utf-8'))
        if isinstance(value, dict):
          new_dict = {}
          for ink, inv in value.iteritems():
            if isinstance(inv, (list, tuple)):
              new_inv = []
              for elt in inv:
                if isinstance(elt, (list, tuple)):
                  new_inv.append([x.encode('utf-8') for x in elt])
                elif isinstance(elt, dict):
                  new_inv.append(dict([(x.encode('utf-8'),
                    y and y.encode("utf-8")) for x,y in elt.iteritems()]))
                else:
                  new_inv.append(elt.encode('utf-8'))
              new_dict[ink.encode('utf-8')] = new_inv
            elif inv is None:
              new_dict[ink.encode('utf-8')] = None
            else:
              new_dict[ink.encode('utf-8')] = inv.encode('utf-8')
          setattr(self, key, new_dict)
        else:
          setattr(self, key, value)
    return func(self, *args, **kw)
  return decorated


class ComputerPartition(SlapDocument):

  zope.interface.implements(interface.IComputerPartition)

  def __init__(self, computer_id=None, partition_id=None, request_dict=None):
    if request_dict is not None and (computer_id is not None or
        partition_id is not None):
      raise TypeError('request_dict conflicts with computer_id and '
        'partition_id')
    if request_dict is None and (computer_id is None or partition_id is None):
      raise TypeError('computer_id and partition_id or request_dict are '
        'required')
    self._computer_id = computer_id
    self._partition_id = partition_id
    self._request_dict = request_dict

  def __getinitargs__(self):
    return (self._computer_id, self._partition_id, )

  # XXX: As request is decorated with _syncComputerPartitionInformation it
  #      will raise ResourceNotReady really early -- just after requesting,
  #      and not when try to access to real partition is required.
  #      To have later raising (like in case of calling methods), the way how
  #      Computer Partition data are fetch from server shall be delayed
  @_syncComputerPartitionInformation
  def request(self, software_release, software_type, partition_reference,
              shared=False, partition_parameter_kw=None, filter_kw=None,
              state=None):
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    elif not isinstance(partition_parameter_kw, dict):
      raise ValueError("Unexpected type of partition_parameter_kw '%s'" % \
                       partition_parameter_kw)

    if filter_kw is None:
      filter_kw = {}
    elif not isinstance(filter_kw, dict):
      raise ValueError("Unexpected type of filter_kw '%s'" % \
                       filter_kw)

    request_dict = { 'computer_id': self._computer_id,
        'computer_partition_id': self._partition_id,
        'software_release': software_release,
        'software_type': software_type,
        'partition_reference': partition_reference,
        'shared_xml': xml_marshaller.dumps(shared),
        'partition_parameter_xml': xml_marshaller.dumps(
                                        partition_parameter_kw),
        'filter_xml': xml_marshaller.dumps(filter_kw),
        'state': xml_marshaller.dumps(state),
      }
    try:
      self._connection_helper.POST('/requestComputerPartition', request_dict)
    except ResourceNotReady:
      return ComputerPartition(request_dict=request_dict)
    else:
      xml = self._connection_helper.response.read()
      software_instance = xml_marshaller.loads(xml)
      computer_partition = ComputerPartition(
        software_instance.slap_computer_id.encode('UTF-8'),
        software_instance.slap_computer_partition_id.encode('UTF-8'))
      if shared:
        computer_partition._synced = True
        computer_partition._connection_dict = software_instance._connection_dict
        computer_partition._parameter_dict = software_instance._parameter_dict
      return computer_partition

  def building(self):
    self._connection_helper.POST('/buildingComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id})

  def available(self):
    self._connection_helper.POST('/availableComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id})

  def destroyed(self):
    self._connection_helper.POST('/destroyedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      })

  def started(self):
    self._connection_helper.POST('/startedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      })

  def stopped(self):
    self._connection_helper.POST('/stoppedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      })

  def error(self, error_log):
    self._connection_helper.POST('/softwareInstanceError', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      'error_log': error_log})

  def bang(self, message):
    self._connection_helper.POST('/softwareInstanceBang', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      'message': message})

  def rename(self, new_name, slave_reference=None):
    post_dict = dict(
      computer_id=self._computer_id,
      computer_partition_id=self._partition_id,
      new_name=new_name,
    )
    if slave_reference is not None:
      post_dict.update(slave_reference=slave_reference)
    self._connection_helper.POST('/softwareInstanceRename', post_dict)

  def getId(self):
    return self._partition_id

  @_syncComputerPartitionInformation
  def getState(self):
    return self._requested_state

  @_syncComputerPartitionInformation
  def getInstanceParameterDict(self):
    return getattr(self, '_parameter_dict', None) or {}

  @_syncComputerPartitionInformation
  def getSoftwareRelease(self):
    """
    Returns the software release associate to the computer partition.
    """
    if self._software_release_document is None:
      raise NotFoundError("No software release information for partition %s" %
          self.getId())
    else:
      return self._software_release_document

  def setConnectionDict(self, connection_dict, slave_reference=None):
    self._connection_helper.POST('/setComputerPartitionConnectionXml', {
      'computer_id': self._computer_id,
      'computer_partition_id': self._partition_id,
      'connection_xml': xml_marshaller.dumps(connection_dict),
      'slave_reference': slave_reference})

  @_syncComputerPartitionInformation
  def getConnectionParameter(self, key):
    connection_dict = getattr(self, '_connection_dict', None) or {}
    if key in connection_dict:
      return connection_dict[key]
    else:
      raise NotFoundError("%s not found" % key)

  def setUsage(self, usage_log):
    # XXX: this implementation has not been reviewed
    self.usage = usage_log

  def getCertificate(self):
    self._connection_helper.GET(
        '/getComputerPartitionCertificate?computer_id=%s&'
        'computer_partition_id=%s' % (self._computer_id, self._partition_id))
    return xml_marshaller.loads(self._connection_helper.response.read())

# def lazyMethod(func):
#   """
#   Return a function which stores a computed value in an instance
#   at the first call.
#   """
#   key = '_cache_' + str(id(func))
#   def decorated(self, *args, **kw):
#     try:
#       return getattr(self, key)
#     except AttributeError:
#       result = func(self, *args, **kw)
#       setattr(self, key, result)
#       return result
#   return decorated 

class ConnectionHelper:
  error_message_connect_fail = "Couldn't connect to the server. Please double \
check given master-url argument, and make sure that IPv6 is enabled on \
your machine and that the server is available. The original error was:"
  def __init__(self, connection_wrapper, host, path, key_file=None,
      cert_file=None, master_ca_file=None, timeout=None):
    self.connection_wrapper = connection_wrapper
    self.host = host
    self.path = path
    self.key_file = key_file
    self.cert_file = cert_file
    self.master_ca_file = master_ca_file
    self.timeout = timeout

  def getComputerInformation(self, computer_id):
    self.GET('/getComputerInformation?computer_id=%s' % computer_id)
    return xml_marshaller.loads(self.response.read())

  def connect(self):
    connection_dict = dict(
        host=self.host)
    if self.key_file and self.cert_file:
      connection_dict.update(
        key_file=self.key_file,
        cert_file=self.cert_file)
    if self.master_ca_file is not None:
      connection_dict.update(ca_file=self.master_ca_file)
    self.connection = self.connection_wrapper(**connection_dict)

  def GET(self, path):
    try:
      default_timeout = socket.getdefaulttimeout()
      socket.setdefaulttimeout(self.timeout)
      try:
        self.connect()
        self.connection.request('GET', self.path + path)
        self.response = self.connection.getresponse()
      except socket.error, e:
        raise socket.error(self.error_message_connect_fail + str(e))
      # check self.response.status and raise exception early
      if self.response.status == httplib.REQUEST_TIMEOUT:
        # resource is not ready
        raise ResourceNotReady(path)
      elif self.response.status == httplib.NOT_FOUND:
        raise NotFoundError(path)
      elif self.response.status == httplib.FORBIDDEN:
        raise Unauthorized(path)
      elif self.response.status != httplib.OK:
        message = 'Server responded with wrong code %s with %s' % \
                                           (self.response.status, path)
        raise ServerError(message)
    finally:
      socket.setdefaulttimeout(default_timeout)

  def POST(self, path, parameter_dict,
      content_type="application/x-www-form-urlencoded"):
    try:
      default_timeout = socket.getdefaulttimeout()
      socket.setdefaulttimeout(self.timeout)
      try:
        self.connect()
        header_dict = {'Content-type': content_type}
        self.connection.request("POST", self.path + path,
            urllib.urlencode(parameter_dict), header_dict)
      except socket.error, e:
        raise socket.error(self.error_message_connect_fail + str(e))
      self.response = self.connection.getresponse()
      # check self.response.status and raise exception early
      if self.response.status == httplib.REQUEST_TIMEOUT:
        # resource is not ready
        raise ResourceNotReady("%s - %s" % (path, parameter_dict))
      elif self.response.status == httplib.NOT_FOUND:
        raise NotFoundError("%s - %s" % (path, parameter_dict))
      elif self.response.status == httplib.FORBIDDEN:
        raise Unauthorized("%s - %s" % (path, parameter_dict))
      elif self.response.status != httplib.OK:
        message = 'Server responded with wrong code %s with %s' % \
                                           (self.response.status, path)
        raise ServerError(message)
    finally:
      socket.setdefaulttimeout(default_timeout)

class slap:

  zope.interface.implements(interface.slap)

  def initializeConnection(self, slapgrid_uri, key_file=None, cert_file=None,
      master_ca_file=None, timeout=60):
    self._initialiseConnectionHelper(slapgrid_uri, key_file, cert_file,
        master_ca_file, timeout)

  def _initialiseConnectionHelper(self, slapgrid_uri, key_file, cert_file,
      master_ca_file, timeout):
    SlapDocument._slapgrid_uri = slapgrid_uri
    scheme, netloc, path, query, fragment = urlparse.urlsplit(
        SlapDocument._slapgrid_uri)
    if not(query == '' and fragment == ''):
      raise AttributeError('Passed URL %r issue: not parseable'%
          SlapDocument._slapgrid_uri)
    if scheme not in ('http', 'https'):
      raise AttributeError('Passed URL %r issue: there is no support for %r p'
          'rotocol' % (SlapDocument._slapgrid_uri, scheme))

    if scheme == 'http':
      connection_wrapper = httplib.HTTPConnection
    else:
      if master_ca_file is not None:
        connection_wrapper = HTTPSConnectionCA
      else:
        connection_wrapper = httplib.HTTPSConnection
    slap._connection_helper = \
      SlapDocument._connection_helper = ConnectionHelper(connection_wrapper,
          netloc, path, key_file, cert_file, master_ca_file, timeout)

  def _register(self, klass, *registration_argument_list):
    if len(registration_argument_list) == 1 and type(
        registration_argument_list[0]) == type([]):
      # in case if list is explicitly passed and there is only one
      # argument in registration convert it to list
      registration_argument_list = registration_argument_list[0]
    document = klass(*registration_argument_list)
    return document

  def registerSoftwareRelease(self, software_release):
    """
    Registers connected representation of software release and
    returns SoftwareRelease class object
    """
    return SoftwareRelease(software_release=software_release)

  def registerComputer(self, computer_guid):
    """
    Registers connected representation of computer and
    returns Computer class object
    """
    self.computer_guid = computer_guid
    return self._register(Computer, computer_guid)

  def registerComputerPartition(self, computer_guid, partition_id):
    """
    Registers connected representation of computer partition and
    returns Computer Partition class object
    """
    self._connection_helper.GET('/registerComputerPartition?' \
        'computer_reference=%s&computer_partition_reference=%s' % (
          computer_guid, partition_id))
    xml = self._connection_helper.response.read()
    return xml_marshaller.loads(xml)

  def registerOpenOrder(self):
    return OpenOrder()

  def registerSupply(self):
    return Supply()
