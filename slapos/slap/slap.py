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
           "SoftwareInstance", "SoftwareProductCollection",
           "Supply", "OpenOrder", "NotFoundError",
           "ResourceNotReady", "ServerError", "ConnectionError"]

import os
import json
import logging
import re
import urlparse
import hashlib
from util import xml2dict

import netaddr
from xml.sax import saxutils
import zope.interface
from interface import slap as interface
from xml_marshaller import xml_marshaller

from uritemplate import expand

import requests
# silence messages like 'Unverified HTTPS request is being made'
requests.packages.urllib3.disable_warnings()
# silence messages like 'Starting connection' that are logged with INFO
urllib3_logger = logging.getLogger('requests.packages.urllib3')
urllib3_logger.setLevel(logging.WARNING)


# XXX fallback_logger to be deprecated together with the old CLI entry points.
fallback_logger = logging.getLogger(__name__)
fallback_handler = logging.StreamHandler()
fallback_logger.setLevel(logging.INFO)
fallback_logger.addHandler(fallback_handler)


DEFAULT_SOFTWARE_TYPE = 'RootSoftwareInstance'
COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME = '.slapos-request-transaction-%s'

class SlapDocument:
  def __init__(self, connection_helper=None, hateoas_navigator=None):
    if connection_helper is not None:
      # Do not require connection_helper to be provided, but when it's not,
      # cause failures when accessing _connection_helper property.
      self._connection_helper = connection_helper
      self._hateoas_navigator = hateoas_navigator


class SlapRequester(SlapDocument):
  """
  Abstract class that allow to factor method for subclasses that use "request()"
  """

  def _requestComputerPartition(self, request_dict):
    try:
      xml = self._connection_helper.POST('requestComputerPartition', data=request_dict)
    except ResourceNotReady:
      return ComputerPartition(
        request_dict=request_dict,
        connection_helper=self._connection_helper,
      )
    if type(xml) is unicode:
      xml = str(xml)
      xml.encode('utf-8')
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
    SlapDocument.__init__(self, kw.pop('connection_helper', None),
                                kw.pop('hateoas_navigator', None))
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
      self._connection_helper.POST('softwareReleaseError', data={
        'url': self.getURI(),
        'computer_id': self.getComputerId(),
        'error_log': error_log})
    except Exception:
      (logger or fallback_logger).exception('')

  def available(self):
    self._connection_helper.POST('availableSoftwareRelease', data={
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def building(self):
    self._connection_helper.POST('buildingSoftwareRelease', data={
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def destroyed(self):
    self._connection_helper.POST('destroyedSoftwareRelease', data={
      'url': self.getURI(),
      'computer_id': self.getComputerId()})

  def getState(self):
    return getattr(self, '_requested_state', 'available')


class SoftwareProductCollection(object):
  zope.interface.implements(interface.ISoftwareProductCollection)

  def __init__(self, logger, slap):
    self.logger = logger
    self.slap = slap
    self.get = self.__getattr__

  def __getattr__(self, software_product):
      self.logger.info('Getting best Software Release corresponding to '
                       'this Software Product...')
      software_release_list = \
          self.slap.getSoftwareReleaseListFromSoftwareProduct(software_product)
      try:
          software_release_url = software_release_list[0] # First is best one.
          self.logger.info('Found as %s.' % software_release_url)
          return software_release_url
      except IndexError:
          raise AttributeError('No Software Release corresponding to this '
                           'Software Product has been found.')


# XXX What is this SoftwareInstance class?
class SoftwareInstance(SlapDocument):
  """
  Contains Software Instance information
  """
  zope.interface.implements(interface.ISoftwareInstance)

  def __init__(self, **kwargs):
    """
    Makes easy initialisation of class parameters
    """
    for k, v in kwargs.iteritems():
      setattr(self, k, v)


"""Exposed exceptions"""
class ResourceNotReady(Exception):
  zope.interface.implements(interface.IResourceNotReady)

class ServerError(Exception):
  zope.interface.implements(interface.IServerError)

class NotFoundError(Exception):
  zope.interface.implements(interface.INotFoundError)

class AuthenticationError(Exception):
  pass


class ConnectionError(Exception):
  zope.interface.implements(interface.IConnectionError)


class Supply(SlapDocument):
  zope.interface.implements(interface.ISupply)

  def supply(self, software_release, computer_guid=None, state='available'):
    try:
      self._connection_helper.POST('supplySupply', data={
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

  def getInformation(self, partition_reference):
    if not getattr(self, '_hateoas_navigator', None):
      raise Exception('SlapOS Master Hateoas API required for this operation is not availble.')
    raw_information = self._hateoas_navigator.getHostingSubscriptionRootSoftwareInstanceInformation(partition_reference)
    software_instance = SoftwareInstance()
    # XXX redefine SoftwareInstance to be more consistent
    for key, value in raw_information.iteritems():
      if key in ['_links']:
        continue
      setattr(software_instance, '_%s' % key, value)
    setattr(software_instance, '_software_release_url', raw_information['_links']['software_release'])
    return software_instance

  def requestComputer(self, computer_reference):
    """
    Requests a computer.
    """
    xml = self._connection_helper.POST('requestComputer', data={'computer_title': computer_reference})
    computer = xml_marshaller.loads(xml)
    computer._connection_helper = self._connection_helper
    computer._hateoas_navigator = self._hateoas_navigator
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

  def __init__(self, computer_id, connection_helper=None, hateoas_navigator=None):
    SlapDocument.__init__(self, connection_helper, hateoas_navigator)
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
      software_relase._hateoas_navigator = self._hateoas_navigator
    return self._software_release_list

  @_syncComputerInformation
  def getComputerPartitionList(self):
    for computer_partition in self._computer_partition_list:
      computer_partition._connection_helper = self._connection_helper
      computer_partition._hateoas_navigator = self._hateoas_navigator
    return [x for x in self._computer_partition_list]

  def reportUsage(self, computer_usage):
    if computer_usage == "":
      return
    self._connection_helper.POST('useComputer', data={
      'computer_id': self._computer_id,
      'use_string': computer_usage})

  def updateConfiguration(self, xml):
    return self._connection_helper.POST('loadComputerConfigurationFromXML', data={'xml': xml})

  def bang(self, message):
    self._connection_helper.POST('computerBang', data={
      'computer_id': self._computer_id,
      'message': message})

  def getStatus(self):
    xml = self._connection_helper.GET('getComputerStatus', params={'computer_id': self._computer_id})
    return xml_marshaller.loads(xml)

  def revokeCertificate(self):
    self._connection_helper.POST('revokeComputerCertificate', data={
      'computer_id': self._computer_id})

  def generateCertificate(self):
    xml = self._connection_helper.POST('generateComputerCertificate', data={
      'computer_id': self._computer_id})
    return xml_marshaller.loads(xml)


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
               request_dict=None, connection_helper=None,
               hateoas_navigator=None):
    SlapDocument.__init__(self, connection_helper, hateoas_navigator)
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

    # Just create an empty file (for nothing requested yet)
    self._updateTransactionFile(partition_reference=None)

  def __getinitargs__(self):
    return (self._computer_id, self._partition_id, )

  def _updateTransactionFile(self, partition_reference=None):
    """
    Store reference to all Instances requested by this Computer Parition
    """
    # Environ variable set by Slapgrid while processing this partition
    instance_root = os.environ.get('SLAPGRID_INSTANCE_ROOT', '')
    if not instance_root or not self._partition_id:
      return

    transaction_file_name = COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME % self._partition_id
    transaction_file_path = os.path.join(instance_root, self._partition_id,
                                        transaction_file_name)

    try:
      if partition_reference is None:
        if os.access(os.path.join(instance_root, self._partition_id), os.W_OK):
          if os.path.exists(transaction_file_path):
            return
          transac_file = open(transaction_file_path, 'w')
          transac_file.close()
      else:
        with open(transaction_file_path, 'a') as transac_file:
          transac_file.write('%s\n' % partition_reference)
    except OSError:
      return

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
    self._updateTransactionFile(partition_reference)
    return self._requestComputerPartition(request_dict)

  def destroyed(self):
    self._connection_helper.POST('destroyedComputerPartition', data={
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def started(self):
    self._connection_helper.POST('startedComputerPartition', data={
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def stopped(self):
    self._connection_helper.POST('stoppedComputerPartition', data={
      'computer_id': self._computer_id,
      'computer_partition_id': self.getId(),
      })

  def error(self, error_log, logger=None):
    try:
      self._connection_helper.POST('softwareInstanceError', data={
        'computer_id': self._computer_id,
        'computer_partition_id': self.getId(),
        'error_log': error_log})
    except Exception:
      (logger or fallback_logger).exception('')

  def bang(self, message):
    self._connection_helper.POST('softwareInstanceBang', data={
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
    self._connection_helper.POST('softwareInstanceRename', data=post_dict)

  def getInformation(self, partition_reference):
    """
    Return all needed informations about an existing Computer Partition
    in the Instance tree of the current Computer Partition.
    """
    if not getattr(self, '_hateoas_navigator', None):
      raise Exception('SlapOS Master Hateoas API required for this operation is not availble.')

    raw_information = self._hateoas_navigator.getRelatedInstanceInformation(partition_reference)
    software_instance = SoftwareInstance()
    # XXX redefine SoftwareInstance to be more consistent
    for key, value in raw_information.iteritems():
      if key in ['_links']:
        continue
      setattr(software_instance, '_%s' % key, value)
    setattr(software_instance, '_software_release_url', raw_information['_links']['software_release'])
    return software_instance


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

  def getAccessStatus(self):
    """Get latest computer partition Access message state"""
    return getattr(self, '_access_status', None)

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
    connection_dict = getattr(self, '_connection_dict', None)
    if connection_dict is None:
      # XXX Backward compatibility for older slapproxy (<= 1.0.0)
      connection_dict = xml2dict(getattr(self, 'connection_xml', ''))

    return connection_dict or {}

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
    if self.getConnectionParameterDict() == connection_dict:
      return

    if slave_reference is not None:
      # check the connection parameters from the slave

      # Should we check existence?
      slave_parameter_list = self.getInstanceParameter("slave_instance_list")
      slave_connection_dict = {}
      connection_parameter_hash = None
      for slave_parameter_dict in slave_parameter_list:
        if slave_parameter_dict.get("slave_reference") == slave_reference:
          connection_parameter_hash = slave_parameter_dict.get("connection-parameter-hash", None)
          break

      # Skip as nothing changed for the slave
      if connection_parameter_hash is not None and \
        connection_parameter_hash == hashlib.sha256(str(connection_dict)).hexdigest():
        return

    self._connection_helper.POST('setComputerPartitionConnectionXml', data={
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
    connection_dict = self.getConnectionParameterDict()
    if key in connection_dict:
      return connection_dict[key]
    else:
      raise NotFoundError("%s not found" % key)

  def setUsage(self, usage_log):
    # XXX: this implementation has not been reviewed
    self.usage = usage_log

  def getCertificate(self):
    xml = self._connection_helper.GET('getComputerPartitionCertificate',
            params={
                'computer_id': self._computer_id,
                'computer_partition_id': self._partition_id,
                }
            )
    return xml_marshaller.loads(xml)

  def getStatus(self):
    xml = self._connection_helper.GET('getComputerPartitionStatus',
            params={
                'computer_id': self._computer_id,
                'computer_partition_id': self._partition_id,
                }
            )
    return xml_marshaller.loads(xml)
  
  def getFullHostingIpAddressList(self):
    xml = self._connection_helper.GET('getHostingSubscriptionIpList',
            params={
                'computer_id': self._computer_id,
                'computer_partition_id': self._partition_id,
                }
            )
    return xml_marshaller.loads(xml)

  def setComputerPartitionRelatedInstanceList(self, instance_reference_list):
    self._connection_helper.POST('updateComputerPartitionRelatedInstanceList',
        data={
          'computer_id': self._computer_id,
          'computer_partition_id': self._partition_id,
          'instance_reference_xml': xml_marshaller.dumps(instance_reference_list)
          }
        )

def _addIpv6Brackets(url):
  # if master_url contains an ipv6 without bracket, add it
  # Note that this is mostly to limit specific issues with
  # backward compatiblity, not to ensure generic detection.
  api_scheme, api_netloc, api_path, api_query, api_fragment = urlparse.urlsplit(url)
  try:
    ip = netaddr.IPAddress(api_netloc)
    port = None
  except netaddr.AddrFormatError:
    try:
      ip = netaddr.IPAddress(':'.join(api_netloc.split(':')[:-1]))
      port = api_netloc.split(':')[-1]
    except netaddr.AddrFormatError:
      ip = port = None
  if ip and ip.version == 6:
    api_netloc = '[%s]' % ip
    if port:
      api_netloc = '%s:%s' % (api_netloc, port)
    url = urlparse.urlunsplit((api_scheme, api_netloc, api_path, api_query, api_fragment))
  return url

class ConnectionHelper:
  def __init__(self, master_url, key_file=None,
               cert_file=None, master_ca_file=None, timeout=None):
    master_url = _addIpv6Brackets(master_url)
    if master_url.endswith('/'):
        self.slapgrid_uri = master_url
    else:
        # add a slash or the last path segment will be ignored by urljoin
        self.slapgrid_uri = master_url + '/'
    self.key_file = key_file
    self.cert_file = cert_file
    self.master_ca_file = master_ca_file
    self.timeout = timeout

  def getComputerInformation(self, computer_id):
    xml = self.GET('getComputerInformation', params={'computer_id': computer_id})
    return xml_marshaller.loads(xml)

  def getFullComputerInformation(self, computer_id):
    """
    Retrieve from SlapOS Master Computer instance containing all needed
    informations (Software Releases, Computer Partitions, ...).
    """
    path = 'getFullComputerInformation'
    params = {'computer_id': computer_id}
    if not computer_id:
      # XXX-Cedric: should raise something smarter than "NotFound".
      raise NotFoundError('%r %r' % (path, params))
    try:
      xml = self.GET(path, params=params)
    except NotFoundError:
      # XXX: This is a ugly way to keep backward compatibility,
      # We should stablise slap library soon.
      xml = self.GET('getComputerInformation', params=params)

    if type(xml) is unicode:
      xml = str(xml)
      xml.encode('utf-8')
    return xml_marshaller.loads(xml)

  def do_request(self, method, path, params=None, data=None, headers=None):
    url = urlparse.urljoin(self.slapgrid_uri, path)
    if headers is None:
      headers = {}
    headers.setdefault('Accept', '*/*')
    if path.startswith('/'):
      path = path[1:]
#      raise ValueError('method path should be relative: %s' % path)

    try:
      if url.startswith('https'):
        cert = (self.cert_file, self.key_file)
      else:
        cert = None

      # XXX TODO: handle host cert verify

      # Old behavior was to pass empty parameters as "None" value.
      # Behavior kept for compatibility with old slapproxies (< v1.3.3).
      # Can be removed when old slapproxies are no longer in use.
      if data:
        for k, v in data.iteritems():
          if v is None:
            data[k] = 'None'

      req = method(url=url,
                   params=params,
                   cert=cert,
                   verify=False,
                   data=data,
                   headers=headers,
                   timeout=self.timeout)
      req.raise_for_status()

    except (requests.Timeout, requests.ConnectionError) as exc:
      raise ConnectionError("Couldn't connect to the server. Please "
                            "double check given master-url argument, and make sure that IPv6 is "
                            "enabled on your machine and that the server is available. The "
                            "original error was:\n%s" % exc)
    except requests.HTTPError as exc:
      if exc.response.status_code == requests.status_codes.codes.not_found:
        msg = url
        if params:
            msg += ' - %s' % params
        raise NotFoundError(msg)
      elif exc.response.status_code == requests.status_codes.codes.request_timeout:
        # this is explicitly returned by SlapOS master, and does not really mean timeout
        raise ResourceNotReady(path)
        # XXX TODO test request timeout and resource not found
      else:
        # we don't know how or don't want to handle these (including Unauthorized)
        req.raise_for_status()
    except requests.exceptions.SSLError as exc:
      raise AuthenticationError("%s\nCouldn't authenticate computer. Please "
                                "check that certificate and key exist and are valid." % exc)

#    XXX TODO parse server messages for client configure and node register
#    elif response.status != httplib.OK:
#      message = parsed_error_message(response.status,
#                                     response.read(),
#                                     path)
#      raise ServerError(message)

    return req

  def GET(self, path, params=None, headers=None):
    req = self.do_request(requests.get,
                          path=path,
                          params=params,
                          headers=headers)
    return req.text.encode('utf-8')

  def POST(self, path, params=None, data=None,
           content_type='application/x-www-form-urlencoded'):
    req = self.do_request(requests.post,
                          path=path,
                          params=params,
                          data=data,
                          headers={'Content-type': content_type})
    return req.text.encode('utf-8')


getHateoasUrl_cache = {}
class slap:
  zope.interface.implements(interface.slap)

  def initializeConnection(self, slapgrid_uri,
                           key_file=None, cert_file=None,
                           master_ca_file=None,
                           timeout=60,
                           slapgrid_rest_uri=None):
    if master_ca_file:
      raise NotImplementedError('Master certificate not verified in this version: %s' % master_ca_file)

    self._connection_helper = ConnectionHelper(slapgrid_uri, key_file, cert_file, master_ca_file, timeout)

    if not slapgrid_rest_uri:
      getHateoasUrl_cache_key = (slapgrid_uri, key_file, cert_file, master_ca_file, timeout)
      try:
        slapgrid_rest_uri = getHateoasUrl_cache[getHateoasUrl_cache_key]
      except KeyError:
        pass
    if not slapgrid_rest_uri:
      try:
        slapgrid_rest_uri = getHateoasUrl_cache[getHateoasUrl_cache_key] = self._connection_helper.GET('getHateoasUrl')
      except:
        pass
    if slapgrid_rest_uri:
      self._hateoas_navigator = SlapHateoasNavigator(
          slapgrid_rest_uri,
          key_file, cert_file,
          master_ca_file, timeout
      )
    else:
      self._hateoas_navigator = None

  # XXX-Cedric: this method is never used and thus should be removed.
  def registerSoftwareRelease(self, software_release):
    """
    Registers connected representation of software release and
    returns SoftwareRelease class object
    """
    return SoftwareRelease(software_release=software_release,
      connection_helper=self._connection_helper,
      hateoas_navigator=self._hateoas_navigator
    )

  def registerComputer(self, computer_guid):
    """
    Registers connected representation of computer and
    returns Computer class object
    """
    return Computer(computer_guid,
      connection_helper=self._connection_helper,
      hateoas_navigator=self._hateoas_navigator
    )

  def registerComputerPartition(self, computer_guid, partition_id):
    """
    Registers connected representation of computer partition and
    returns Computer Partition class object
    """
    if not computer_guid or not partition_id:
      # XXX-Cedric: should raise something smarter than NotFound
      raise NotFoundError

    xml = self._connection_helper.GET('registerComputerPartition',
            params = {
                'computer_reference': computer_guid,
                'computer_partition_reference': partition_id,
                }
            )
    if type(xml) is unicode:
      xml = str(xml)
      xml.encode('utf-8')
    result = xml_marshaller.loads(xml)
    # XXX: dirty hack to make computer partition usable. xml_marshaller is too
    # low-level for our needs here.
    result._connection_helper = self._connection_helper
    result._hateoas_navigator = self._hateoas_navigator
    return result

  def registerOpenOrder(self):
    return OpenOrder(
      connection_helper=self._connection_helper,
      hateoas_navigator=self._hateoas_navigator
  )

  def registerSupply(self):
    return Supply(
      connection_helper=self._connection_helper,
      hateoas_navigator=self._hateoas_navigator
  )

  def getSoftwareReleaseListFromSoftwareProduct(self,
      software_product_reference=None, software_release_url=None):
    url = 'getSoftwareReleaseListFromSoftwareProduct'
    params = {}
    if software_product_reference:
      if software_release_url is not None:
        raise AttributeError('Both software_product_reference and '
                             'software_release_url parameters are specified.')
      params['software_product_reference'] = software_product_reference
    else:
      if software_release_url is None:
        raise AttributeError('None of software_product_reference and '
                             'software_release_url parameters are specified.')
      params['software_release_url'] = software_release_url

    xml = self._connection_helper.GET(url, params=params)
    if type(xml) is unicode:
      xml = str(xml)
      xml.encode('utf-8')
    result = xml_marshaller.loads(xml)
    assert(type(result) == list)
    return result

  def getOpenOrderDict(self):
    if not getattr(self, '_hateoas_navigator', None):
      raise Exception('SlapOS Master Hateoas API required for this operation is not availble.')
    return self._hateoas_navigator.getHostingSubscriptionDict()

class HateoasNavigator(object):
  """
  Navigator for HATEOAS-style APIs.
  Inspired by
  https://git.erp5.org/gitweb/jio.git/blob/HEAD:/src/jio.storage/erp5storage.js
  """
  # XXX: needs to be designed for real. For now, just a non-maintainable prototype.
  # XXX: export to a standalone library, independant from slap.
  def __init__(self, slapgrid_uri,
               key_file=None, cert_file=None,
               master_ca_file=None, timeout=60):
    self.slapos_master_hateoas_uri = slapgrid_uri
    self.key_file = key_file
    self.cert_file = cert_file
    self.master_ca_file = master_ca_file
    self.timeout = timeout

  def GET(self, uri, headers=None):
    connection_helper = ConnectionHelper(
        uri, self.key_file, self.cert_file, self.master_ca_file, self.timeout)
    return connection_helper.GET(uri, headers=headers)

  def hateoasGetLinkFromLinks(self, links, title):
    if type(links) == dict:
      if links.get('title') == title:
        return links['href']
      raise NotFoundError('Action %s not found.' % title)
    for action in links:
      if action.get('title') == title:
        return action['href']
    else:
      raise NotFoundError('Action %s not found.' % title)

  def getRelativeUrlFromUrn(self, urn):
    urn_schema = 'urn:jio:get:'
    try:
      _, url = urn.split(urn_schema)
    except ValueError:
      return
    return str(url)

  def getSiteDocument(self, url, headers=None):
    result = self.GET(url, headers)
    return json.loads(result)

  def getRootDocument(self):
    # XXX what about cache?
    cached_root_document = getattr(self, 'root_document', None)
    if cached_root_document:
      return cached_root_document
    self.root_document = self.getSiteDocument(
        self.slapos_master_hateoas_uri,
        headers={'Cache-Control': 'no-cache'}
    )
    return self.root_document

  def getDocumentAndHateoas(self, relative_url, view='view'):
    site_document = self.getRootDocument()
    return expand(
        site_document['_links']['traverse']['href'],
        dict(relative_url=relative_url, view=view)
    )

  def getMeDocument(self):
    person_relative_url = self.getRelativeUrlFromUrn(
        self.getRootDocument()['_links']['me']['href'])
    person_url = self.getDocumentAndHateoas(person_relative_url)
    return json.loads(self.GET(person_url))

class SlapHateoasNavigator(HateoasNavigator):
  def _hateoas_getHostingSubscriptionDict(self):
    action_object_slap_list = self.getMeDocument()['_links']['action_object_slap']
    for action in action_object_slap_list:
      if action.get('title') == 'getHateoasHostingSubscriptionList':
        getter_link = action['href']
        break
    else:
      raise Exception('Hosting subscription not found.')
    result = self.GET(getter_link)
    return json.loads(result)['_links']['content']

  # XXX rename me to blablaUrl(self)
  def _hateoas_getRelatedHostingSubscription(self):
    action_object_slap_list = self.getMeDocument()['_links']['action_object_slap']
    getter_link = self.hateoasGetLinkFromLinks(action_object_slap_list, 'getHateoasRelatedHostingSubscription')
    result = self.GET(getter_link)
    return json.loads(result)['_links']['action_object_jump']['href']

  def _hateoasGetInformation(self, url):
    result = self.GET(url)
    result = json.loads(result)
    object_link = self.hateoasGetLinkFromLinks(
      result['_links']['action_object_slap'],
      'getHateoasInformation'
    )
    result = self.GET(object_link)
    return json.loads(result)

  def getHateoasInstanceList(self, hosting_subscription_url):
    hosting_subscription = json.loads(self.GET(hosting_subscription_url))
    instance_list_url = self.hateoasGetLinkFromLinks(hosting_subscription['_links']['action_object_slap'], 'getHateoasInstanceList')
    instance_list = json.loads(self.GET(instance_list_url))
    return instance_list['_links']['content']

  def getHostingSubscriptionDict(self):
    hosting_subscription_link_list = self._hateoas_getHostingSubscriptionDict()
    hosting_subscription_dict = {}
    for hosting_subscription_link in hosting_subscription_link_list:
      raw_information = self.getHostingSubscriptionRootSoftwareInstanceInformation(hosting_subscription_link['title'])
      software_instance = SoftwareInstance()
      # XXX redefine SoftwareInstance to be more consistent
      for key, value in raw_information.iteritems():
        if key in ['_links']:
          continue
        setattr(software_instance, '_%s' % key, value)
      setattr(software_instance, '_software_release_url', raw_information['_links']['software_release'])
      hosting_subscription_dict[software_instance._title] = software_instance

    return hosting_subscription_dict

  def getHostingSubscriptionRootSoftwareInstanceInformation(self, reference):
    hosting_subscription_list = self._hateoas_getHostingSubscriptionDict()
    for hosting_subscription in hosting_subscription_list:
      if hosting_subscription.get('title') == reference:
        hosting_subscription_url = hosting_subscription['href']
        break
    else:
      raise NotFoundError('This document does not exist.')

    hosting_subscription = json.loads(self.GET(hosting_subscription_url))

    software_instance_url = self.hateoasGetLinkFromLinks(
        hosting_subscription['_links']['action_object_slap'],
        'getHateoasRootInstance'
    )
    response = self.GET(software_instance_url)
    response = json.loads(response)
    software_instance_url = response['_links']['content'][0]['href']
    return self._hateoasGetInformation(software_instance_url)

  def getRelatedInstanceInformation(self, reference):
    related_hosting_subscription_url = self._hateoas_getRelatedHostingSubscription()
    instance_list = self.getHateoasInstanceList(related_hosting_subscription_url)
    instance_url = self.hateoasGetLinkFromLinks(instance_list, reference)
    instance = self._hateoasGetInformation(instance_url)
    return instance
