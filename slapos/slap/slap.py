# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
"""
Simple, easy to (un)marshall classes for slap client/server communication
"""

__all__ = ["slap", "ComputerPartition", "Computer", "SoftwareRelease",
           "Supply", "OpenOrder", "NotFoundError", "Unauthorized",
           "ResourceNotReady", "ServerError"]

import httplib
import logging
import re
import socket
import ssl
import urllib
import urlparse

from xml.sax import saxutils
import zope.interface
from interface import slap as interface
from xml_marshaller import xml_marshaller

# XXX fallback_logger to be deprecated together with the old CLI entry points.
fallback_logger = logging.getLogger(__name__)
fallback_handler = logging.StreamHandler()
fallback_logger.setLevel(logging.INFO)
fallback_logger.addHandler(fallback_handler)


DEFAULT_SOFTWARE_TYPE = 'RootSoftwareInstance'


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
  def __init__(self, connection_helper=None):
    if connection_helper is not None:
      # Do not require connection_helper to be provided, but when it's not,
      # cause failures when accessing _connection_helper property.
      self._connection_helper = connection_helper


class SlapRequester(SlapDocument):
  """
  Abstract class that allow to factor method for subclasses that use "request()"
  """
  def _requestComputerPartition(self, request_dict):
    try:
      xml = self._connection_helper.POST('/requestComputerPartition', request_dict)
    except ResourceNotReady:
      return ComputerPartition(
        request_dict=request_dict,
        connection_helper=self._connection_helper,
      )
    software_instance = xml_marshaller.loads(xml)
    computer_partition = ComputerPartition(
      software_instance.slap_computer_id.encode('UTF-8'),
      software_instance.slap_computer_partition_id.encode('UTF-8'),
      connection_helper=self._connection_helper,
    )
    # Hack to give all object attributes to the ComputerPartition instance
    # XXX Should be removed by correctly specifying difference between
    # ComputerPartition and SoftwareInstance
    computer_partition.__dict__ = dict(computer_partition.__dict__.items() +
                                       software_instance.__dict__.items())
    # XXX not generic enough.
    if xml_marshaller.loads(request_dict['shared_xml']):
      computer_partition._synced = True
      computer_partition._connection_dict = software_instance._connection_dict
      computer_partition._parameter_dict = software_instance._parameter_dict
    return computer_partition


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
    SlapDocument.__init__(self, kw.pop('connection_helper', None))
    self._software_instance_list = []
    if software_release is not None:
      software_release = software_release.encode('UTF-8')
    self._software_release = software_release
    self._computer_guid = computer_guid

  def __getinitargs__(self):
    return (self._software_release, self._computer_guid, )

  def getComputerId(self):
    if not self._computer_guid:
      raise NameError('computer_guid has not been defined.')
    else:
      return self._computer_guid

  def getURI(self):
    if not self._software_release:
      raise NameError('software_release has not been defined.')
    else:
      return self._software_release

  def error(self, error_log, logger=None):
    try:
      # Does not follow interface
      self._connection_helper.POST('/softwareReleaseError', {
        'url': self.getURI(),
        'computer_id': self.getComputerId(),
        'error_log': error_log})
    except Exception:
      (logger or fallback_logger).exception('')

  def available(self):
    self._connection_helper.POST('/availableSoftwareRelease', {
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def building(self):
    self._connection_helper.POST('/buildingSoftwareRelease', {
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def destroyed(self):
    self._connection_helper.POST('/destroyedSoftwareRelease', {
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def getState(self):
    return getattr(self, '_requested_state', 'available')


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
  zope.interface.implements(interface.IResourceNotReady)


class ServerError(Exception):
  zope.interface.implements(interface.IServerError)


class NotFoundError(Exception):
  zope.interface.implements(interface.INotFoundError)


class Unauthorized(Exception):
  zope.interface.implements(interface.IUnauthorized)


class Supply(SlapDocument):
  zope.interface.implements(interface.ISupply)

  def supply(self, software_release, computer_guid=None, state='available'):
    try:
      self._connection_helper.POST('/supplySupply', {
        'url': software_release,
        'computer_id': computer_guid,
        'state': state})
    except NotFoundError:
      raise NotFoundError("Computer %s has not been found by SlapOS Master."
          % computer_guid)


class OpenOrder(SlapRequester):
  zope.interface.implements(interface.IOpenOrder)

  def request(self, software_release, partition_reference,
              partition_parameter_kw=None, software_type=None,
              filter_kw=None, state=None, shared=False):
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    if filter_kw is None:
      filter_kw = {}
    request_dict = {
        'software_release': software_release,
        'partition_reference': partition_reference,
        'partition_parameter_xml': xml_marshaller.dumps(partition_parameter_kw),
        'filter_xml': xml_marshaller.dumps(filter_kw),
        # XXX Cedric: Why state and shared are marshalled? First is a string
        #             And second is a boolean.
        'state': xml_marshaller.dumps(state),
        'shared_xml': xml_marshaller.dumps(shared),
    }
    if software_type is not None:
      request_dict['software_type'] = software_type
    else:
      # Let's enforce a default software type
      request_dict['software_type'] = DEFAULT_SOFTWARE_TYPE
    return self._requestComputerPartition(request_dict)

  def requestComputer(self, computer_reference):
    """
    Requests a computer.
    """
    xml = self._connection_helper.POST('/requestComputer',
      {'computer_title': computer_reference})
    computer = xml_marshaller.loads(xml)
    computer._connection_helper = self._connection_helper
    return computer


def _syncComputerInformation(func):
  """
  Synchronize computer object with server information
  """
  def decorated(self, *args, **kw):
    if getattr(self, '_synced', 0):
      return func(self, *args, **kw)
    computer = self._connection_helper.getFullComputerInformation(self._computer_id)
    for key, value in computer.__dict__.items():
      if isinstance(value, unicode):
        # convert unicode to utf-8
        setattr(self, key, value.encode('utf-8'))
      else:
        setattr(self, key, value)
    setattr(self, '_synced', True)
    for computer_partition in self.getComputerPartitionList():
      setattr(computer_partition, '_synced', True)
    return func(self, *args, **kw)
  return decorated


class Computer(SlapDocument):
  zope.interface.implements(interface.IComputer)

  def __init__(self, computer_id, connection_helper=None):
    SlapDocument.__init__(self, connection_helper)
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
    for software_relase in self._software_release_list:
      software_relase._connection_helper = self._connection_helper
    return self._software_release_list

  @_syncComputerInformation
  def getComputerPartitionList(self):
    for computer_partition in self._computer_partition_list:
      computer_partition._connection_helper = self._connection_helper
    return [x for x in self._computer_partition_list]

  def reportUsage(self, computer_usage):
    if computer_usage == "":
      return
    self._connection_helper.POST('/useComputer', {
      'computer_id': self._computer_id,
      'use_string': computer_usage})

  def updateConfiguration(self, xml):
    return self._connection_helper.POST(
        '/loadComputerConfigurationFromXML', {'xml': xml})

  def bang(self, message):
    self._connection_helper.POST('/computerBang', {
      'computer_id': self._computer_id,
      'message': message})

  def getStatus(self):
    xml = self._connection_helper.GET(
        '/getComputerStatus?computer_id=%s' % self._computer_id)
    return xml_marshaller.loads(xml)

  def revokeCertificate(self):
    self._connection_helper.POST('/revokeComputerCertificate', {
      'computer_id': self._computer_id})

  def generateCertificate(self):
    xml = self._connection_helper.POST('/generateComputerCertificate', {
      'computer_id': self._computer_id})
    return xml_marshaller.loads(xml)

  def reportNetDriveUsage(self, xml):
    self._connection_helper.POST(
        '/reportNetDriveUsageFromXML', { 'xml' : xml })
    return self._connection_helper.response.read()

def parsed_error_message(status, body, path):
  m = re.search('(Error Value:\n.*)', body, re.MULTILINE)
  if m:
    match = ' '.join(line.strip() for line in m.group(0).split('\n'))
    return '%s (status %s while calling %s)' % (
                saxutils.unescape(match),
                status,
                path
            )
  else:
    return 'Server responded with wrong code %s with %s' % (status, path)


class ComputerPartition(SlapRequester):
  zope.interface.implements(interface.IComputerPartition)

  def __init__(self, computer_id=None, partition_id=None,
               request_dict=None, connection_helper=None):
    SlapDocument.__init__(self, connection_helper)
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

  def request(self, software_release, software_type, partition_reference,
              shared=False, partition_parameter_kw=None, filter_kw=None,
              state=None):
    if partition_parameter_kw is None:
      partition_parameter_kw = {}
    elif not isinstance(partition_parameter_kw, dict):
      raise ValueError("Unexpected type of partition_parameter_kw '%s'" %
                       partition_parameter_kw)

    if filter_kw is None:
      filter_kw = {}
    elif not isinstance(filter_kw, dict):
      raise ValueError("Unexpected type of filter_kw '%s'" %
                       filter_kw)

    # Let enforce a default software type
    if software_type is None:
      software_type = DEFAULT_SOFTWARE_TYPE

    request_dict = {
        'computer_id': self._computer_id,
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
    return self._requestComputerPartition(request_dict)

  def building(self):
    self._connection_helper.POST('/buildingComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId()})

  def available(self):
    self._connection_helper.POST('/availableComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId()})

  def destroyed(self):
    self._connection_helper.POST('/destroyedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def started(self):
    self._connection_helper.POST('/startedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def stopped(self):
    self._connection_helper.POST('/stoppedComputerPartition', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def error(self, error_log, logger=None):
    try:
      self._connection_helper.POST('/softwareInstanceError', {
        'computer_id': self._computer_id,
        'computer_partition_id': self.getId(),
        'error_log': error_log})
    except Exception:
      (logger or fallback_logger).exception('')

  def bang(self, message):
    self._connection_helper.POST('/softwareInstanceBang', {
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      'message': message})

  def rename(self, new_name, slave_reference=None):
    post_dict = {
            'computer_id': self._computer_id,
            'computer_partition_id': self.getId(),
            'new_name': new_name,
            }
    if slave_reference:
      post_dict['slave_reference'] = slave_reference
    self._connection_helper.POST('/softwareInstanceRename', post_dict)

  def getId(self):
    if not getattr(self, '_partition_id', None):
      raise ResourceNotReady()
    return self._partition_id

  def getInstanceGuid(self):
    """Return instance_guid. Raise ResourceNotReady if it doesn't exist."""
    if not getattr(self, '_instance_guid', None):
      raise ResourceNotReady()
    return self._instance_guid

  def getState(self):
    """return _requested_state. Raise ResourceNotReady if it doesn't exist."""
    if not getattr(self, '_requested_state', None):
      raise ResourceNotReady()
    return self._requested_state

  def getType(self):
    """
    return the Software Type of the instance.
    Raise RessourceNotReady if not present.
    """
    # XXX: software type should not belong to the parameter dict.
    software_type = self.getInstanceParameterDict().get(
        'slap_software_type', None)
    if not software_type:
      raise ResourceNotReady()
    return software_type

  def getInstanceParameterDict(self):
    return getattr(self, '_parameter_dict', None) or {}

  def getConnectionParameterDict(self):
    return getattr(self, '_connection_dict', None) or {}

  def getSoftwareRelease(self):
    """
    Returns the software release associate to the computer partition.
    """
    if not getattr(self, '_software_release_document', None):
      raise NotFoundError("No software release information for partition %s" %
          self.getId())
    else:
      return self._software_release_document

  def setConnectionDict(self, connection_dict, slave_reference=None):
    if self.getConnectionParameterDict() != connection_dict:
      self._connection_helper.POST('/setComputerPartitionConnectionXml', {
          'computer_id': self._computer_id,
          'computer_partition_id': self._partition_id,
          'connection_xml': xml_marshaller.dumps(connection_dict),
          'slave_reference': slave_reference})

  def getInstanceParameter(self, key):
    parameter_dict = getattr(self, '_parameter_dict', None) or {}
    if key in parameter_dict:
      return parameter_dict[key]
    else:
      raise NotFoundError("%s not found" % key)

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
    xml = self._connection_helper.GET(
        '/getComputerPartitionCertificate?computer_id=%s&'
        'computer_partition_id=%s' % (self._computer_id, self._partition_id))
    return xml_marshaller.loads(xml)

  def getStatus(self):
    xml = self._connection_helper.GET(
        '/getComputerPartitionStatus?computer_id=%s&'
        'computer_partition_id=%s' % (self._computer_id, self._partition_id))
    return xml_marshaller.loads(xml)


class ConnectionHelper:
  error_message_timeout = "\nThe connection timed out. Please try again later."
  error_message_connect_fail = "Couldn't connect to the server. Please " \
      "double check given master-url argument, and make sure that IPv6 is " \
      "enabled on your machine and that the server is available. The " \
      "original error was: "
  ssl_error_message_connect_fail = "\nCouldn't authenticate computer. Please "\
      "check that certificate and key exist and are valid. "

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
    xml = self.GET('/getComputerInformation?computer_id=%s' % computer_id)
    return xml_marshaller.loads(xml)

  def getFullComputerInformation(self, computer_id):
    """
    Retrieve from SlapOS Master Computer instance containing all needed
    informations (Software Releases, Computer Partitions, ...).
    """
    method = '/getFullComputerInformation?computer_id=%s' % computer_id
    if not computer_id:
      # XXX-Cedric: should raise something smarter than "NotFound".
      raise NotFoundError(method)
    try:
      xml = self.GET(method)
    except NotFoundError:
      # XXX: This is a ugly way to keep backward compatibility,
      # We should stablise slap library soon.
      xml = self.GET('/getComputerInformation?computer_id=%s' % computer_id)

    return xml_marshaller.loads(xml)

  def connect(self):
    connection_dict = {
            'host': self.host
            }
    if self.key_file and self.cert_file:
      connection_dict['key_file'] = self.key_file
      connection_dict['cert_file'] = self.cert_file
    if self.master_ca_file:
      connection_dict['ca_file'] = self.master_ca_file
    self.connection = self.connection_wrapper(**connection_dict)

  def GET(self, path):
    try:
      default_timeout = socket.getdefaulttimeout()
      socket.setdefaulttimeout(self.timeout)
      try:
        self.connect()
        self.connection.request('GET', self.path + path)
        response = self.connection.getresponse()
      # If ssl error : may come from bad configuration
      except ssl.SSLError as exc:
        if exc.message == 'The read operation timed out':
          raise socket.error(str(exc) + self.error_message_timeout)
        raise ssl.SSLError(str(exc) + self.ssl_error_message_connect_fail)
      except socket.error as exc:
        if exc.message == 'timed out':
          raise socket.error(str(exc) + self.error_message_timeout)
        raise socket.error(self.error_message_connect_fail + str(exc))

      # check self.response.status and raise exception early
      if response.status == httplib.REQUEST_TIMEOUT:
        # resource is not ready
        raise ResourceNotReady(path)
      elif response.status == httplib.NOT_FOUND:
        raise NotFoundError(path)
      elif response.status == httplib.FORBIDDEN:
        raise Unauthorized(path)
      elif response.status != httplib.OK:
        message = parsed_error_message(response.status,
                                       response.read(),
                                       path)
        raise ServerError(message)
    finally:
      socket.setdefaulttimeout(default_timeout)

    return response.read()

  def POST(self, path, parameter_dict,
           content_type='application/x-www-form-urlencoded'):
    try:
      default_timeout = socket.getdefaulttimeout()
      socket.setdefaulttimeout(self.timeout)
      try:
        self.connect()
        header_dict = {'Content-type': content_type}
        self.connection.request("POST", self.path + path,
            urllib.urlencode(parameter_dict), header_dict)
      # If ssl error : must come from bad configuration
      except ssl.SSLError as exc:
        raise ssl.SSLError(self.ssl_error_message_connect_fail + str(exc))
      except socket.error as exc:
        raise socket.error(self.error_message_connect_fail + str(exc))

      response = self.connection.getresponse()
      # check self.response.status and raise exception early
      if response.status == httplib.REQUEST_TIMEOUT:
        # resource is not ready
        raise ResourceNotReady("%s - %s" % (path, parameter_dict))
      elif response.status == httplib.NOT_FOUND:
        raise NotFoundError("%s - %s" % (path, parameter_dict))
      elif response.status == httplib.FORBIDDEN:
        raise Unauthorized("%s - %s" % (path, parameter_dict))
      elif response.status != httplib.OK:
        message = parsed_error_message(response.status,
                                       response.read(),
                                       path)
        raise ServerError(message)
    finally:
      socket.setdefaulttimeout(default_timeout)

    return response.read()


class slap:
  zope.interface.implements(interface.slap)

  def initializeConnection(self, slapgrid_uri, key_file=None, cert_file=None,
                           master_ca_file=None, timeout=60):
    scheme, netloc, path, query, fragment = urlparse.urlsplit(slapgrid_uri)
    if not (query == '' and fragment == ''):
      raise AttributeError('Passed URL %r issue: not parseable' % slapgrid_uri)

    if scheme == 'http':
      connection_wrapper = httplib.HTTPConnection
    elif scheme == 'https':
      if master_ca_file is not None:
        connection_wrapper = HTTPSConnectionCA
      else:
        connection_wrapper = httplib.HTTPSConnection
    else:
      raise AttributeError('Passed URL %r issue: there is no support '
                           'for %r protocol' % (slapgrid_uri, scheme))
    self._connection_helper = ConnectionHelper(connection_wrapper,
          netloc, path, key_file, cert_file, master_ca_file, timeout)

  # XXX-Cedric: this method is never used and thus should be removed.
  def registerSoftwareRelease(self, software_release):
    """
    Registers connected representation of software release and
    returns SoftwareRelease class object
    """
    return SoftwareRelease(software_release=software_release,
      connection_helper=self._connection_helper
    )

  def registerComputer(self, computer_guid):
    """
    Registers connected representation of computer and
    returns Computer class object
    """
    return Computer(computer_guid, connection_helper=self._connection_helper)

  def registerComputerPartition(self, computer_guid, partition_id):
    """
    Registers connected representation of computer partition and
    returns Computer Partition class object
    """
    if not computer_guid or not partition_id:
      # XXX-Cedric: should raise something smarter than NotFound
      raise NotFoundError

    xml = self._connection_helper.GET('/registerComputerPartition?' \
        'computer_reference=%s&computer_partition_reference=%s' % (
          computer_guid, partition_id))
    result = xml_marshaller.loads(xml)
    # XXX: dirty hack to make computer partition usable. xml_marshaller is too
    # low-level for our needs here.
    result._connection_helper = self._connection_helper
    return result

  def registerOpenOrder(self):
    return OpenOrder(connection_helper=self._connection_helper)

  def registerSupply(self):
    return Supply(connection_helper=self._connection_helper)
