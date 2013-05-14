# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2011 Nexedi SA and Contributors. All Rights Reserved.
#                    Łukasz Nowak <luke@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
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
# as published by the Free Software Foundation; either version 2
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

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from AccessControl.Permissions import access_contents_information
from AccessControl import getSecurityManager
from Products.ERP5Type.UnrestrictedMethod import UnrestrictedMethod
from OFS.Traversable import NotFound
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from Products.ERP5Type.Globals import InitializeClass
from Products.ERP5Type.Tool.BaseTool import BaseTool
from Products.ERP5Type import Permissions
from Products.ERP5Type.Cache import DEFAULT_CACHE_SCOPE
from Products.ERP5Type.Cache import CachingMethod
from lxml import etree
import time
from Products.ERP5Type.tests.utils import DummyMailHostMixin
try:
  from slapos.slap.slap import Computer
  from slapos.slap.slap import ComputerPartition as SlapComputerPartition
  from slapos.slap.slap import SoftwareInstance
  from slapos.slap.slap import SoftwareRelease
except ImportError:
  # Do no prevent instance from starting
  # if libs are not installed
  class Computer:
    def __init__(self):
      raise ImportError
  class SlapComputerPartition:
    def __init__(self):
      raise ImportError
  class SoftwareInstance:
    def __init__(self):
      raise ImportError
  class SoftwareRelease:
    def __init__(self):
      raise ImportError

from zLOG import LOG, INFO
import xml_marshaller
import StringIO
import pkg_resources
from Products.Vifib.Conduit import VifibConduit
import json
from DateTime import DateTime
from App.Common import rfc1123_date
class SoftwareInstanceNotReady(Exception):
  pass

def convertToREST(function):
  """
  Wrap the method to create a log entry for each invocation to the zope logger
  """
  def wrapper(self, *args, **kwd):
    """
    Log the call, and the result of the call
    """
    try:
      retval = function(self, *args, **kwd)
    except (ValueError, AttributeError), log:
      LOG('SlapTool', INFO, 'Converting ValueError to NotFound, real error:',
          error=True)
      raise NotFound(log)
    except SoftwareInstanceNotReady, log:
      self.REQUEST.response.setStatus(408)
      self.REQUEST.response.setHeader('Cache-Control', 'private')
      return self.REQUEST.response
    except ValidationFailed:
      LOG('SlapTool', INFO, 'Converting ValidationFailed to ValidationFailed,'\
        ' real error:',
          error=True)
      raise ValidationFailed
    except Unauthorized:
      LOG('SlapTool', INFO, 'Converting Unauthorized to Unauthorized,'\
        ' real error:',
          error=True)
      raise Unauthorized

    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    return '%s' % retval
  wrapper.__doc__ = function.__doc__
  return wrapper

def _assertACI(document):
  sm = getSecurityManager()
  if sm.checkPermission(access_contents_information,
      document):
    return document
  raise Unauthorized('User %r has no access to %r' % (sm.getUser(), document))


_MARKER = []

class SlapTool(BaseTool):
  """SlapTool"""

  # TODO:
  #   * catch and convert exceptions to HTTP codes (be restful)

  id = 'portal_slap'
  meta_type = 'ERP5 Slap Tool'
  portal_type = 'Slap Tool'
  security = ClassSecurityInfo()
  allowed_types = ()

  security.declarePrivate('manage_afterAdd')
  def manage_afterAdd(self, item, container) :
    """Init permissions right after creation.

    Permissions in slap tool are simple:
     o Each member can access the tool.
     o Only manager can view and create.
     o Anonymous can not access
    """
    item.manage_permission(Permissions.AddPortalContent,
          ['Manager'])
    item.manage_permission(Permissions.AccessContentsInformation,
          ['Member', 'Manager'])
    item.manage_permission(Permissions.View,
          ['Manager',])
    BaseTool.inheritedAttribute('manage_afterAdd')(self, item, container)

  ####################################################
  # Public GET methods
  ####################################################

  def _isTestRun(self):
    if issubclass(self.getPortalObject().MailHost.__class__, DummyMailHostMixin) \
        or self.REQUEST.get('test_list'):
      return True
    return False

  def _getCachePlugin(self):
    return self.getPortalObject().portal_caches\
      .getRamCacheRoot().get('computer_information_cache_factory')\
      .getCachePluginList()[0]

  def _getCacheComputerInformation(self, computer_id, user):
    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    slap_computer = Computer(computer_id.decode("UTF-8"))
    parent_uid = self._getComputerUidByReference(computer_id)

    slap_computer._computer_partition_list = []
    slap_computer._software_release_list = \
       self._getSoftwareReleaseValueListForComputer(computer_id)
    for computer_partition in self.getPortalObject().portal_catalog.unrestrictedSearchResults(
                    parent_uid=parent_uid,
                    validation_state="validated",
                    portal_type="Computer Partition"):
      slap_computer._computer_partition_list.append(
          self._getSlapPartitionByPackingList(_assertACI(computer_partition.getObject())))
    return xml_marshaller.xml_marshaller.dumps(slap_computer)

  def _fillComputerInformationCache(self, computer_id, user):
    key = '%s_%s' % (computer_id, user)
    try:
      self._getCachePlugin().set(key, DEFAULT_CACHE_SCOPE,
        dict (
          time=time.time(),
          data=self._getCacheComputerInformation(computer_id, user),
        ),
        cache_duration=self.getPortalObject().portal_caches\
            .getRamCacheRoot().get('computer_information_cache_factory'\
              ).cache_duration
        )
    except (Unauthorized, IndexError):
      # XXX: Unauthorized hack. Race condition of not ready setup delivery which provides
      # security information shall not make this method fail, as it will be
      # called later anyway
      # Note: IndexError ignored, as it happend in case if full reindex is
      # called on site
      pass

  def _storeLastData(self, key, value):
    cache_plugin = self.getPortalObject().portal_caches\
      .getRamCacheRoot().get('last_stored_data_cache_factory')\
      .getCachePluginList()[0]
    cache_plugin.set(key, DEFAULT_CACHE_SCOPE, value,
      cache_duration=self.getPortalObject().portal_caches\
      .getRamCacheRoot().get('last_stored_data_cache_factory').cache_duration)

  def _getLastData(self, key):
    cache_plugin = self.getPortalObject().portal_caches\
      .getRamCacheRoot().get('last_stored_data_cache_factory')\
      .getCachePluginList()[0]
    try:
      entry = cache_plugin.get(key, DEFAULT_CACHE_SCOPE)
    except KeyError:
      entry = None
    else:
      entry = entry.getValue()
    return entry

  def _activateFillComputerInformationCache(self, computer_id, user):
    tag = 'computer_information_cache_fill_%s_%s' % (computer_id, user)
    if self.getPortalObject().portal_activities.countMessageWithTag(tag) == 0:
      self.activate(activity='SQLQueue', tag=tag)._fillComputerInformationCache(
        computer_id, user)

  def _getComputerInformation(self, computer_id, user):
    user_document = _assertACI(self.getPortalObject().portal_catalog.unrestrictedGetResultValue(
      reference=user, portal_type=['Person', 'Computer', 'Software Instance']))
    user_type = user_document.getPortalType()
    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    slap_computer = Computer(computer_id.decode("UTF-8"))
    parent_uid = self._getComputerUidByReference(computer_id)

    slap_computer._computer_partition_list = []
    if user_type in ('Computer', 'Person'):
      if not self._isTestRun():
        cache_plugin = self._getCachePlugin()
        try:
          key = '%s_%s' % (computer_id, user)
          entry = cache_plugin.get(key, DEFAULT_CACHE_SCOPE)
        except KeyError:
          entry = None
        if entry is not None and type(entry.getValue()) == type({}):
          result = entry.getValue()['data']
          self._activateFillComputerInformationCache(computer_id, user)
          return result
        else:
          self._activateFillComputerInformationCache(computer_id, user)
          self.REQUEST.response.setStatus(503)
          return self.REQUEST.response
      else:
        return self._getCacheComputerInformation(computer_id, user)
#      return self._getCacheComputerInformation(computer_id, user)
    else:
      slap_computer._software_release_list = []
    if user_type == 'Software Instance':
      computer = self.getPortalObject().portal_catalog.unrestrictedSearchResults(
        portal_type='Computer', reference=computer_id,
        validation_state="validated")[0].getObject()
      computer_partition_list = computer.contentValues(
        portal_type="Computer Partition",
        checked_permission="View")
    else:
      computer_partition_list = self.getPortalObject().portal_catalog.unrestrictedSearchResults(
                    parent_uid=parent_uid,
                    validation_state="validated",
                    portal_type="Computer Partition")
    for computer_partition in computer_partition_list:
      slap_computer._computer_partition_list.append(
          self._getSlapPartitionByPackingList(_assertACI(computer_partition.getObject())))
    return xml_marshaller.xml_marshaller.dumps(slap_computer)

  security.declareProtected(Permissions.AccessContentsInformation,
    'getFullComputerInformation')
  def getFullComputerInformation(self, computer_id):
    """Returns marshalled XML of all needed information for computer

    Includes Software Releases, which may contain Software Instances.

    Reuses slap library for easy marshalling.
    """
    user = self.getPortalObject().portal_membership.getAuthenticatedMember().getUserName()
    if str(user) == computer_id:
      self._logAccess(user, user, '#access %s' % computer_id)
    result = self._getComputerInformation(computer_id, user)

    if self.REQUEST.response.getStatus() == 200:
      # Keep in cache server for 7 days
      self.REQUEST.response.setHeader('Cache-Control',
                                      'public, max-age=1, stale-if-error=604800')
      self.REQUEST.response.setHeader('Vary',
                                      'REMOTE_USER')
      self.REQUEST.response.setHeader('Last-Modified', rfc1123_date(DateTime()))
      self.REQUEST.response.setBody(result)
      return self.REQUEST.response
    else:
      return result

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerPartitionCertificate')
  def getComputerPartitionCertificate(self, computer_id, computer_partition_id):
    """Method to fetch certificate"""
    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    software_instance = self._getSoftwareInstanceForComputerPartition(
      computer_id, computer_partition_id)
    certificate_dict = dict(
      key=software_instance.getSslKey(),
      certificate=software_instance.getSslCertificate()
    )
    result = xml_marshaller.xml_marshaller.dumps(certificate_dict)
    # Cache with revalidation
    self.REQUEST.response.setStatus(200)
    self.REQUEST.response.setHeader('Cache-Control',
                                    'public, max-age=0, must-revalidate')
    self.REQUEST.response.setHeader('Vary',
                                    'REMOTE_USER')
    self.REQUEST.response.setHeader('Last-Modified',
                                    rfc1123_date(software_instance.getModificationDate()))
    self.REQUEST.response.setBody(result)
    return self.REQUEST.response

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerInformation')
  getComputerInformation = getFullComputerInformation

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerPartitionStatus')
  def getComputerPartitionStatus(self, computer_id, computer_partition_id):
    """
    Get the connection status of the partition
    """
    try:
      instance = self._getSoftwareInstanceForComputerPartition(
          computer_id,
          computer_partition_id)
    except NotFound:
      return self._getAccessStatus(None)
    else:
      return self._getAccessStatus(instance.getReference())

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerStatus')
  def getComputerStatus(self, computer_id):
    """
    Get the connection status of the partition
    """
    computer = self.getPortalObject().portal_catalog.unrestrictedSearchResults(
      portal_type='Computer', reference=computer_id,
      validation_state="validated")[0].getObject()
    # Be sure to prevent accessing information to disallowed users
    computer = _assertACI(computer)
    return self._getAccessStatus(computer_id)

  ####################################################
  # Public POST methods
  ####################################################

  security.declareProtected(Permissions.AccessContentsInformation,
    'setComputerPartitionConnectionXml')
  def setComputerPartitionConnectionXml(self, computer_id,
                                        computer_partition_id,
                                        connection_xml, slave_reference=None):
    """
    Set instance parameter informations on the slagrid server
    """
    # When None is passed in POST, it is converted to string
    if slave_reference is not None and slave_reference.lower() == "none":
      slave_reference = None
    return self._setComputerPartitionConnectionXml(computer_id,
                                                   computer_partition_id,
                                                   connection_xml,
                                                   slave_reference)

  security.declareProtected(Permissions.AccessContentsInformation,
    'supplySupply')
  def supplySupply(self, url, computer_id, state='available'):
    """
    Request Software Release installation
    """
    return self._supplySupply(url, computer_id, state)

  @convertToREST
  def _requestComputer(self, computer_title):
    portal = self.getPortalObject()
    person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
    person.requestComputer(computer_title=computer_title)
    computer = Computer(self.REQUEST.get('computer_reference').decode("UTF-8"))
    return xml_marshaller.xml_marshaller.dumps(computer)

  security.declareProtected(Permissions.AccessContentsInformation,
    'requestComputer')
  def requestComputer(self, computer_title):
    """
    Request Computer
    """
    return self._requestComputer(computer_title)

  security.declareProtected(Permissions.AccessContentsInformation,
    'buildingSoftwareRelease')
  def buildingSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is being build
    """
    return self._buildingSoftwareRelease(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'availableSoftwareRelease')
  def availableSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is available
    """
    return self._availableSoftwareRelease(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'destroyedSoftwareRelease')
  def destroyedSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is available
    """
    return self._destroyedSoftwareRelease(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareReleaseError')
  def softwareReleaseError(self, url, computer_id, error_log):
    """
    Add an error for a software Release workflow
    """
    return self._softwareReleaseError(url, computer_id, error_log)

  security.declareProtected(Permissions.AccessContentsInformation,
    'buildingComputerPartition')
  def buildingComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is being build
    """
    return self._buildingComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'availableComputerPartition')
  def availableComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is available
    """
    return self._availableComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareInstanceError')
  def softwareInstanceError(self, computer_id,
                            computer_partition_id, error_log):
    """
    Add an error for the software Instance Workflow
    """
    return self._softwareInstanceError(computer_id, computer_partition_id,
                                       error_log)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareInstanceRename')
  def softwareInstanceRename(self, new_name, computer_id,
                             computer_partition_id, slave_reference=None):
    """
    Change the title of a Software Instance using Workflow.
    """
    return self._softwareInstanceRename(new_name, computer_id,
                                        computer_partition_id,
                                        slave_reference)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareInstanceBang')
  def softwareInstanceBang(self, computer_id,
                            computer_partition_id, message):
    """
    Fire up bang on this Software Instance
    """
    return self._softwareInstanceBang(computer_id, computer_partition_id,
                                       message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'startedComputerPartition')
  def startedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is started
    """
    return self._startedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'stoppedComputerPartition')
  def stoppedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is stopped
    """
    return self._stoppedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'destroyedComputerPartition')
  def destroyedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is destroyed
    """
    return self._destroyedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'requestComputerPartition')
  def requestComputerPartition(self, computer_id=None,
      computer_partition_id=None, software_release=None, software_type=None,
      partition_reference=None, partition_parameter_xml=None,
      filter_xml=None, state=None, shared_xml=_MARKER):
    """
    Asynchronously requests creation of computer partition for assigned
    parameters

    Returns XML representation of partition with HTTP code 200 OK

    In case if this request is still being processed data contain
    "Computer Partition is being processed" and HTTP code is 408 Request Timeout

    In any other case returns not important data and HTTP code is 403 Forbidden
    """
    return self._requestComputerPartition(computer_id, computer_partition_id,
        software_release, software_type, partition_reference,
        shared_xml, partition_parameter_xml, filter_xml, state)

  security.declareProtected(Permissions.AccessContentsInformation,
    'useComputer')
  def useComputer(self, computer_id, use_string):
    """Entry point to reporting usage of a computer."""
    #We retrieve XSD model
    try:
      computer_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/computer_consumption.xsd')
    except IOError:
      computer_consumption_model = \
        pkg_resources.resource_string(
          __name__,
          '../../../../slapos/slap/doc/computer_consumption.xsd')

    if self._validateXML(use_string, computer_consumption_model):
      vifib_conduit_instance = VifibConduit.VifibConduit()

      #We create the SPL
      vifib_conduit_instance.addNode(
        object=self, 
        xml=use_string, 
        computer_id=computer_id)
    else:
      raise NotImplementedError("XML file sent by the node is not valid !")

    return 'Content properly posted.'

  @convertToREST
  def _computerBang(self, computer_id, message):
    """
    Fire up bung on Computer
    """
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, computer_id, '#error bang')
    return self._getComputerDocument(computer_id).reportComputerBang(
                                     comment=message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'computerBang')
  def computerBang(self, computer_id, message):
    """
    Fire up bang on this Software Instance
    """
    return self._computerBang(computer_id, message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'loadComputerConfigurationFromXML')
  def loadComputerConfigurationFromXML(self, xml):
    "Load the given xml as configuration for the computer object"
    computer_dict = xml_marshaller.xml_marshaller.loads(xml)
    computer = self._getComputerDocument(computer_dict['reference'])
    computer.Computer_updateFromDict(computer_dict)
    return 'Content properly posted.'

  security.declareProtected(Permissions.AccessContentsInformation,
    'useComputerPartition')
  def useComputerPartition(self, computer_id, computer_partition_id,
    use_string):
    """Warning : deprecated method."""
    computer_document = self._getComputerDocument(computer_id)
    computer_partition_document = self._getComputerPartitionDocument(
      computer_document.getReference(), computer_partition_id)
    # easy way to start to store usage messages sent by client in related Web
    # Page text_content...
    self._reportUsage(computer_partition_document, use_string)
    return """Content properly posted.
              WARNING : this method is deprecated. Please use useComputer."""

  @convertToREST
  def _generateComputerCertificate(self, computer_id):
    self._getComputerDocument(computer_id).generateCertificate()
    result = {
     'certificate': self.REQUEST.get('computer_certificate').decode("UTF-8"),
     'key': self.REQUEST.get('computer_key').decode("UTF-8")
     }
    return xml_marshaller.xml_marshaller.dumps(result)

  security.declareProtected(Permissions.AccessContentsInformation,
    'generateComputerCertificate')
  def generateComputerCertificate(self, computer_id):
    """Fetches new computer certificate"""
    return self._generateComputerCertificate(computer_id)

  @convertToREST
  def _revokeComputerCertificate(self, computer_id):
    self._getComputerDocument(computer_id).revokeCertificate()

  security.declareProtected(Permissions.AccessContentsInformation,
    'revokeComputerCertificate')
  def revokeComputerCertificate(self, computer_id):
    """Revokes existing computer certificate"""
    return self._revokeComputerCertificate(computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'registerComputerPartition')
  def registerComputerPartition(self, computer_reference,
                                computer_partition_reference):
    """
    Registers connected representation of computer partition and
    returns Computer Partition class object
    """
    # Try to get the computer partition to raise an exception if it doesn't
    # exist
    portal = self.getPortalObject()
    computer_partition_document = self._getComputerPartitionDocument(
          computer_reference, computer_partition_reference)
    slap_partition = SlapComputerPartition(computer_reference.decode("UTF-8"),
        computer_partition_reference.decode("UTF-8"))
    slap_partition._software_release_document = None
    slap_partition._requested_state = 'destroyed'
    slap_partition._need_modification = 0
    software_instance = None

    if computer_partition_document.getSlapState() == 'busy':
      software_instance_list = portal.portal_catalog.unrestrictedSearchResults(
          portal_type="Software Instance",
          default_aggregate_uid=computer_partition_document.getUid(),
          validation_state="validated",
          limit=2,
          )
      software_instance_count = len(software_instance_list)
      if software_instance_count == 1:
        software_instance = _assertACI(software_instance_list[0].getObject())
      elif software_instance_count > 1:
        # XXX do not prevent the system to work if one partition is broken
        raise NotImplementedError, "Too many instances %s linked to %s" % \
          ([x.path for x in software_instance_list],
           computer_partition_document.getRelativeUrl())

    if software_instance is not None:
      # trick client side, that data has been synchronised already for given
      # document
      slap_partition._synced = True
      state = software_instance.getSlapState()
      if state == "stop_requested":
        slap_partition._requested_state = 'stopped'
      if state == "start_requested":
        slap_partition._requested_state = 'started'

      slap_partition._software_release_document = SoftwareRelease(
            software_release=software_instance.getUrlString().decode("UTF-8"),
            computer_guid=computer_reference.decode("UTF-8"))
      slap_partition._software_release_document._software_release = \
        slap_partition._software_release_document._software_release.decode("UTF-8")

      slap_partition._need_modification = 1

      parameter_dict = self._getSoftwareInstanceAsParameterDict(
                                                       software_instance)
      # software instance has to define an xml parameter
      slap_partition._parameter_dict = self._instanceXmlToDict(
        parameter_dict.pop('xml'))
      slap_partition._connection_dict = self._instanceXmlToDict(
        parameter_dict.pop('connection_xml'))
      slap_partition._instance_guid = parameter_dict.pop('instance_guid')
      for slave_instance_dict in parameter_dict.get("slave_instance_list", []):
        if slave_instance_dict.has_key("connection_xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("connection_xml")))
        if slave_instance_dict.has_key("xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("xml")))
      slap_partition._parameter_dict.update(parameter_dict)
    result = xml_marshaller.xml_marshaller.dumps(slap_partition)

    # Keep in cache server for 7 days
    self.REQUEST.response.setStatus(200)
    self.REQUEST.response.setHeader('Cache-Control',
                                    'public, max-age=1, stale-if-error=604800')
    self.REQUEST.response.setHeader('Vary',
                                    'REMOTE_USER')
    self.REQUEST.response.setHeader('Last-Modified', rfc1123_date(DateTime()))
    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    self.REQUEST.response.setBody(result)
    return self.REQUEST.response

  ####################################################
  # Internal methods
  ####################################################

  def _getMemcachedDict(self):
    return self.getPortalObject().portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')

  def _logAccess(self, user_reference, context_reference, text):
    memcached_dict = self._getMemcachedDict()
    value = json.dumps({
      'user': '%s' % user_reference,
      'created_at': '%s' % rfc1123_date(DateTime()),
      'text': '%s' % text,
    })
    memcached_dict[context_reference] = value

  def _validateXML(self, to_be_validated, xsd_model):
    """Will validate the xml file"""
    #We parse the XSD model
    xsd_model = StringIO.StringIO(xsd_model)
    xmlschema_doc = etree.parse(xsd_model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    string_to_validate = StringIO.StringIO(to_be_validated)

    try:
      document = etree.parse(string_to_validate)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
      LOG('SlapTool::_validateXML', INFO, 
        'Failed to parse this XML reports : %s\n%s' % \
          (to_be_validated, e))
      return False

    if xmlschema.validate(document):
      return True

    return False

  def _instanceXmlToDict(self, xml):
    result_dict = {}
    try:
      if xml is not None and xml != '':
        tree = etree.fromstring(xml)
        for element in tree.findall('parameter'):
          key = element.get('id')
          value = result_dict.get(key, None)
          if value is not None:
            value = value + ' ' + element.text
          else:
            value = element.text
          result_dict[key] = value
    except (etree.XMLSchemaError, etree.XMLSchemaParseError,
      etree.XMLSchemaValidateError, etree.XMLSyntaxError):
      LOG('SlapTool', INFO, 'Issue during parsing xml:', error=True)
    return result_dict

  def _getSlapPartitionByPackingList(self, computer_partition_document):
    computer = computer_partition_document
    portal = self.getPortalObject()
    while computer.getPortalType() != 'Computer':
      computer = computer.getParentValue()
    computer_id = computer.getReference().decode("UTF-8")
    slap_partition = SlapComputerPartition(computer_id,
      computer_partition_document.getReference().decode("UTF-8"))

    slap_partition._software_release_document = None
    slap_partition._requested_state = 'destroyed'
    slap_partition._need_modification = 0

    software_instance = None

    if computer_partition_document.getSlapState() == 'busy':
      software_instance_list = portal.portal_catalog.unrestrictedSearchResults(
          portal_type="Software Instance",
          default_aggregate_uid=computer_partition_document.getUid(),
          validation_state="validated",
          limit=2,
          )
      software_instance_count = len(software_instance_list)
      if software_instance_count == 1:
        software_instance = _assertACI(software_instance_list[0].getObject())
      elif software_instance_count > 1:
        # XXX do not prevent the system to work if one partition is broken
        raise NotImplementedError, "Too many instances %s linked to %s" % \
          ([x.path for x in software_instance_list],
           computer_partition_document.getRelativeUrl())

    if software_instance is not None:
      state = software_instance.getSlapState()
      if state == "stop_requested":
        slap_partition._requested_state = 'stopped'
      if state == "start_requested":
        slap_partition._requested_state = 'started'

      slap_partition._software_release_document = SoftwareRelease(
            software_release=software_instance.getUrlString().decode("UTF-8"),
            computer_guid=computer_id)
      slap_partition._software_release_document._software_release = \
        slap_partition._software_release_document._software_release.decode("UTF-8")

      slap_partition._need_modification = 1

      parameter_dict = self._getSoftwareInstanceAsParameterDict(
                                                       software_instance)
      # software instance has to define an xml parameter
      slap_partition._parameter_dict = self._instanceXmlToDict(
        parameter_dict.pop('xml'))
      slap_partition._connection_dict = self._instanceXmlToDict(
        parameter_dict.pop('connection_xml'))
      slap_partition._instance_guid = parameter_dict.pop('instance_guid')
      for slave_instance_dict in parameter_dict.get("slave_instance_list", []):
        if slave_instance_dict.has_key("connection_xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("connection_xml")))
        if slave_instance_dict.has_key("xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("xml")))
      slap_partition._parameter_dict.update(parameter_dict)

    return slap_partition

  @convertToREST
  def _supplySupply(self, url, computer_id, state):
    """
    Request Software Release installation
    """
    computer_document = self._getComputerDocument(computer_id)
    computer_document.requestSoftwareRelease(software_release_url=url, state=state)

  @convertToREST
  def _buildingSoftwareRelease(self, url, computer_id):
    """
    Log the computer status
    """
    user = self.getPortalObject().portal_membership.\
        getAuthenticatedMember().getUserName()
    self._logAccess(user, user, 'building software release %s' % url)

  @convertToREST
  def _availableSoftwareRelease(self, url, computer_id):
    """
    Log the computer status
    """
    user = self.getPortalObject().portal_membership.\
        getAuthenticatedMember().getUserName()
    self._logAccess(user, user, '#access software release %s available' % \
        url)

  @convertToREST
  def _destroyedSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is destroyed
    """
    computer_document = self._getComputerDocument(computer_id)
    software_installation = self._getSoftwareInstallationForComputer(url,
      computer_document)
    if software_installation.getSlapState() != 'destroy_requested':
      raise NotFound
    if self.getPortalObject().portal_workflow.isTransitionPossible(software_installation,
        'invalidate'):
      software_installation.invalidate(
        comment="Software Release destroyed report.")

  @convertToREST
  def _buildingComputerPartition(self, computer_id, computer_partition_id):
    """
    Log the computer status
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, instance.getReference(), 
                    'building the instance')

  @convertToREST
  def _availableComputerPartition(self, computer_id, computer_partition_id):
    """
    Log the computer status
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, instance.getReference(), 
                    '#access instance available')

  @convertToREST
  def _softwareInstanceError(self, computer_id,
                            computer_partition_id, error_log):
    """
    Add an error for the software Instance Workflow
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, instance.getReference(), 
                    '#error while instanciating')
    #return instance.reportComputerPartitionError()

  @convertToREST
  def _softwareInstanceRename(self, new_name, computer_id,
                              computer_partition_id, slave_reference):
    software_instance = self._getSoftwareInstanceForComputerPartition(
      computer_id, computer_partition_id,
      slave_reference)
    hosting = software_instance.getSpecialise()
    for name in [software_instance.getTitle(), new_name]:
      # reset request cache
      key = '_'.join([hosting, name])
      self._storeLastData(key, {})
    return software_instance.rename(new_name=new_name,
      comment="Rename %s into %s" % (software_instance.title, new_name))

  @convertToREST
  def _softwareInstanceBang(self, computer_id,
                            computer_partition_id, message):
    """
    Fire up bang on Software Instance
    Add an error for the software Instance Workflow
    """
    software_instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.\
        getAuthenticatedMember().getUserName()
    self._logAccess(user, software_instance.getReference(),
                    '#error bang called')
    return software_instance.bang(bang_tree=True, comment=message)

  def _getAccessStatus(self, context_reference):
    memcached_dict = self._getMemcachedDict()
    try:
      if context_reference is None:
        raise KeyError
      else:
        d = memcached_dict[context_reference]
    except KeyError:
      if context_reference is None:
        d = {
          "user": "SlapOS Master",
          'created_at': '%s' % rfc1123_date(DateTime()),
          "text": "#error no data found"
        }
      else:
        d = {
          "user": "SlapOS Master",
          'created_at': '%s' % rfc1123_date(DateTime()),
          "text": "#error no data found for %s" % context_reference
        }
      # Prepare for xml marshalling
      d["user"] = d["user"].decode("UTF-8")
      d["text"] = d["text"].decode("UTF-8")
    else:
      d = json.loads(d)

    # Keep in cache server for 7 days
    self.REQUEST.response.setStatus(200)
    self.REQUEST.response.setHeader('Cache-Control',
                                    'public, max-age=60, stale-if-error=604800')
    self.REQUEST.response.setHeader('Vary',
                                    'REMOTE_USER')
    self.REQUEST.response.setHeader('Last-Modified', rfc1123_date(DateTime()))
    self.REQUEST.response.setHeader('Content-Type', 'text/xml; charset=utf-8')
    self.REQUEST.response.setBody(xml_marshaller.xml_marshaller.dumps(d))
    return self.REQUEST.response

  @convertToREST
  def _startedComputerPartition(self, computer_id, computer_partition_id):
    """
    Log the computer status
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, instance.getReference(),
                    '#access Instance correctly started')

  @convertToREST
  def _stoppedComputerPartition(self, computer_id, computer_partition_id):
    """
    Log the computer status
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(user, instance.getReference(),
                    '#access Instance correctly stopped')

  @convertToREST
  def _destroyedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is destroyed
    """
    instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    if instance.getSlapState() == 'destroy_requested':
      # remove certificate from SI
      if instance.getSslKey() is not None or instance.getSslCertificate() is not None:
        instance.edit(
          ssl_key=None,
          ssl_certificate=None,
        )
      if instance.getValidationState() == 'validated':
        instance.invalidate()

      # XXX Integrate with REST API
      # Code duplication will be needed until SlapTool is removed
      # revoke certificate
      portal = self.getPortalObject()
      try:
        portal.portal_certificate_authority\
          .revokeCertificate(instance.getDestinationReference())
      except ValueError:
        # Ignore already revoked certificates, as OpenSSL backend is
        # non transactional, so it is ok to allow multiple tries to destruction
        # even if certificate was already revoked
        pass


  @convertToREST
  def _setComputerPartitionConnectionXml(self, computer_id,
                                         computer_partition_id,
                                         connection_xml,
                                         slave_reference=None):
    """
    Sets Computer Partition connection Xml
    """
    software_instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id,
        slave_reference)
    partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              connection_xml)
    instance = etree.Element('instance')
    for parameter_id, parameter_value in partition_parameter_kw.iteritems():
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    connection_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')
    reference = software_instance.getReference()
    if self._getLastData(reference) != connection_xml:
      software_instance.updateConnection(
        connection_xml=connection_xml,
      )
      self._storeLastData(reference, connection_xml)

  @convertToREST
  def _requestComputerPartition(self, computer_id, computer_partition_id,
        software_release, software_type, partition_reference,
        shared_xml, partition_parameter_xml, filter_xml, state):
    """
    Asynchronously requests creation of computer partition for assigned
    parameters

    Returns XML representation of partition with HTTP code 200 OK

    In case if this request is still being processed data contain
    "Computer Partition is being processed" and HTTP code is 408 Request
    Timeout

    In any other case returns not important data and HTTP code is 403 Forbidden
    """
    if state:
      state = xml_marshaller.xml_marshaller.loads(state)
    if state is None:
      state = 'started'
    if shared_xml is not _MARKER:
      shared = xml_marshaller.xml_marshaller.loads(shared_xml)
    else:
      shared = False
    if partition_parameter_xml:
      partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              partition_parameter_xml)
    else:
      partition_parameter_kw = dict()
    if filter_xml:
      filter_kw = xml_marshaller.xml_marshaller.loads(filter_xml)
    else:
      filter_kw = dict()

    instance = etree.Element('instance')
    for parameter_id, parameter_value in partition_parameter_kw.iteritems():
      # cast everything to string
      parameter_value = str(parameter_value)
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    instance_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')

    instance = etree.Element('instance')
    for parameter_id, parameter_value in filter_kw.iteritems():
      # cast everything to string
      parameter_value = str(parameter_value)
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    sla_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')

    portal = self.getPortalObject()
    if computer_id and computer_partition_id:
      # requested by Software Instance, there is already top part of tree
      software_instance_document = self.\
        _getSoftwareInstanceForComputerPartition(computer_id,
        computer_partition_id)
      kw = dict(software_release=software_release,
              software_type=software_type,
              software_title=partition_reference,
              instance_xml=instance_xml,
              shared=shared,
              sla_xml=sla_xml,
              state=state)
      key = '_'.join([software_instance_document.getSpecialise(), partition_reference])
      value = dict(
        hash='_'.join([software_instance_document.getRelativeUrl(), str(kw)]),
        )
      last_data = self._getLastData(key)
      requested_software_instance = None
      if last_data is not None and type(last_data) == type({}):
        requested_software_instance = portal.restrictedTraverse(
          last_data.get('request_instance'), None)
      if last_data is None or type(last_data) != type(value) or \
          last_data.get('hash') != value['hash'] or \
          requested_software_instance is None:
        software_instance_document.requestInstance(**kw)
        requested_software_instance = self.REQUEST.get('request_instance')
        if requested_software_instance is not None:
          value['request_instance'] = requested_software_instance\
            .getRelativeUrl()
          self._storeLastData(key, value)
    else:
      # requested as root, so done by human
      person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
      kw = dict(software_release=software_release,
              software_type=software_type,
              software_title=partition_reference,
              shared=shared,
              instance_xml=instance_xml,
              sla_xml=sla_xml,
              state=state)
      key = '_'.join([person.getRelativeUrl(), partition_reference])
      value = dict(
        hash=str(kw)
      )
      last_data = self._getLastData(key)
      if last_data is not None and type(last_data) == type({}):
        requested_software_instance = portal.restrictedTraverse(
          last_data.get('request_instance'), None)
      if last_data is None or type(last_data) != type(value) or \
        last_data.get('hash') != value['hash'] or \
        requested_software_instance is None:
        person.requestSoftwareInstance(**kw)
        requested_software_instance = self.REQUEST.get('request_instance')
        if requested_software_instance is not None:
          value['request_instance'] = requested_software_instance\
            .getRelativeUrl()
          self._storeLastData(key, value)

    if requested_software_instance is None:
      raise SoftwareInstanceNotReady
    else:
      if not requested_software_instance.getAggregate(portal_type="Computer Partition"):
        raise SoftwareInstanceNotReady
      else:
        parameter_dict = self._getSoftwareInstanceAsParameterDict(requested_software_instance)

        # software instance has to define an xml parameter
        xml = self._instanceXmlToDict(
          parameter_dict.pop('xml'))
        connection_xml = self._instanceXmlToDict(
          parameter_dict.pop('connection_xml'))
        instance_guid = parameter_dict.pop('instance_guid')

        software_instance = SoftwareInstance(**parameter_dict)
        software_instance._parameter_dict = xml
        software_instance._connection_dict = connection_xml
        software_instance._requested_state = state
        software_instance._instance_guid = instance_guid
        return xml_marshaller.xml_marshaller.dumps(software_instance)

  ####################################################
  # Internals methods
  ####################################################

  def _getDocument(self, **kwargs):
    # No need to get all results if an error is raised when at least 2 objects
    # are found
    l = self.getPortalObject().portal_catalog.unrestrictedSearchResults(limit=2, **kwargs)
    if len(l) != 1:
      raise NotFound, "No document found with parameters: %s" % kwargs
    else:
      return _assertACI(l[0].getObject())

  def _getNonCachedComputerDocument(self, computer_reference):
    return self._getDocument(
        portal_type='Computer',
        # XXX Hardcoded validation state
        validation_state="validated",
        reference=computer_reference).getRelativeUrl()

  def _getComputerDocument(self, computer_reference):
    """
    Get the validated computer with this reference.
    """
    result = CachingMethod(self._getNonCachedComputerDocument,
        id='_getComputerDocument',
        cache_factory='slap_cache_factory')(computer_reference)
    return self.getPortalObject().restrictedTraverse(result)

  @UnrestrictedMethod
  def _getComputerUidByReference(self, computer_reference):
    return self.getPortalObject().portal_catalog.unrestrictedSearchResults(
      portal_type='Computer', reference=computer_reference,
      validation_state="validated")[0].UID

  def _getComputerPartitionDocument(self, computer_reference,
                                    computer_partition_reference):
    """
    Get the computer partition defined in an available computer
    """
    # Related key might be nice
    return self._getDocument(portal_type='Computer Partition',
                             reference=computer_partition_reference,
                             parent_uid=self._getComputerUidByReference(
                                computer_reference))

  def _getUsageReportServiceDocument(self):
    service_document = self.Base_getUsageReportServiceDocument()
    if service_document is not None:
      return service_document
    raise Unauthorized

  def _getSoftwareInstallationForComputer(self, url, computer_document):
    software_installation_list = self.getPortalObject().portal_catalog.unrestrictedSearchResults(
      portal_type='Software Installation',
      default_aggregate_uid=computer_document.getUid(),
      validation_state='validated',
      limit=2,
      url_string={'query': url, 'key': 'ExactMatch'},
    )

    l = len(software_installation_list)
    if l == 1:
      return _assertACI(software_installation_list[0].getObject())
    elif l == 0:
      raise NotFound('No software release %r found on computer %r' % (url,
        computer_document.getReference()))
    else:
      raise ValueError('Wrong list of software releases on %r: %s' % (
        computer_document.getReference(), ', '.join([q.getRelativeUrl() for q \
          in software_installation_list])
      ))

  def _getSoftwareInstanceForComputerPartition(self, computer_id,
      computer_partition_id, slave_reference=None):
    computer_partition_document = self._getComputerPartitionDocument(
      computer_id, computer_partition_id)
    if computer_partition_document.getSlapState() != 'busy':
      LOG('SlapTool::_getSoftwareInstanceForComputerPartition', INFO,
          'Computer partition %s shall be busy, is free' %
          computer_partition_document.getRelativeUrl())
      raise NotFound, "No software instance found for: %s - %s" % (computer_id,
          computer_partition_id)
    else:
      query_kw = {
        'validation_state': 'validated',
        'portal_type': 'Slave Instance',
        'default_aggregate_uid': computer_partition_document.getUid(),
      }
      if slave_reference is None:
        query_kw['portal_type'] = "Software Instance"
      else:
        query_kw['reference'] = slave_reference

      software_instance = _assertACI(self.getPortalObject().portal_catalog.unrestrictedGetResultValue(**query_kw))
      if software_instance is None:
        raise NotFound, "No software instance found for: %s - %s" % (
          computer_id, computer_partition_id)
      else:
        return software_instance

  @UnrestrictedMethod
  def _getSoftwareInstanceAsParameterDict(self, software_instance):
    portal = software_instance.getPortalObject()
    computer_partition = software_instance.getAggregateValue(portal_type="Computer Partition")
    timestamp = int(computer_partition.getModificationDate())

    newtimestamp = int(software_instance.getBangTimestamp(int(software_instance.getModificationDate())))
    if (newtimestamp > timestamp):
      timestamp = newtimestamp

    ip_list = []
    for internet_protocol_address in computer_partition.contentValues(portal_type='Internet Protocol Address'):
      ip_list.append((
        internet_protocol_address.getNetworkInterface('').decode("UTF-8"),
        internet_protocol_address.getIpAddress().decode("UTF-8")))

    slave_instance_list = []
    if (software_instance.getPortalType() == "Software Instance"):
      append = slave_instance_list.append
      slave_instance_sql_list = portal.portal_catalog.unrestrictedSearchResults(
        default_aggregate_uid=computer_partition.getUid(),
        portal_type='Slave Instance',
        validation_state="validated",
      )
      for slave_instance in slave_instance_sql_list:
        slave_instance = _assertACI(slave_instance.getObject())
        # XXX Use catalog to filter more efficiently
        if slave_instance.getSlapState() == "start_requested":
          append({
            'slave_title': slave_instance.getTitle().decode("UTF-8"),
            'slap_software_type': \
                slave_instance.getSourceReference().decode("UTF-8"),
            'slave_reference': slave_instance.getReference(),
            'xml': slave_instance.getTextContent(),
            'connection_xml': slave_instance.getConnectionXml(),
          })
          newtimestamp = int(slave_instance.getBangTimestamp(int(software_instance.getModificationDate())))                  
          if (newtimestamp > timestamp):                                            
            timestamp = newtimestamp
    return {
      'instance_guid': software_instance.getReference().decode("UTF-8"),
      'xml': software_instance.getTextContent(),
      'connection_xml': software_instance.getConnectionXml(),
      'slap_computer_id': \
        computer_partition.getParentValue().getReference().decode("UTF-8"),
      'slap_computer_partition_id': \
        computer_partition.getReference().decode("UTF-8"),
      'slap_software_type': \
        software_instance.getSourceReference().decode("UTF-8"),
      'slap_software_release_url': \
        software_instance.getUrlString().decode("UTF-8"),
      'slave_instance_list': slave_instance_list,
      'ip_list': ip_list,
      'timestamp': "%i" % timestamp,
    }

  @UnrestrictedMethod
  def _getSoftwareReleaseValueListForComputer(self, computer_reference):
    """Returns list of Software Releases documentsfor computer"""
    computer_document = self._getComputerDocument(computer_reference)
    portal = self.getPortalObject()
    software_release_list = []
    for software_installation in portal.portal_catalog.unrestrictedSearchResults(
      portal_type='Software Installation',
      default_aggregate_uid=computer_document.getUid(),
      validation_state='validated',
      ):
      software_installation = _assertACI(software_installation.getObject())
      software_release_response = SoftwareRelease(
          software_release=software_installation.getUrlString().decode('UTF-8'),
          computer_guid=computer_reference.decode('UTF-8'))
      software_release_response._software_release = \
        software_release_response._software_release.decode("UTF-8")
      if software_installation.getSlapState() == 'destroy_requested':
        software_release_response._requested_state = 'destroyed'
      else:
        software_release_response._requested_state = 'available'
      software_release_list.append(software_release_response)
    return software_release_list

  def _reportComputerUsage(self, computer, usage):
    """Stores usage report of a computer."""
    usage_report_portal_type = 'Usage Report'
    usage_report_module = \
      self.getPortalObject().getDefaultModule(usage_report_portal_type)
    sale_packing_list_portal_type = 'Sale Packing List'
    sale_packing_list_module = \
      self.getPortalObject().getDefaultModule(sale_packing_list_portal_type)
    sale_packing_list_line_portal_type = 'Sale Packing List Line'

    software_release_portal_type = 'Software Release'
    hosting_subscription_portal_type = 'Hosting Subscription'
    software_instance_portal_type = 'Software Instance'

    # We get the whole computer usage in one time
    # We unmarshall it, then we create a single packing list,
    # each line is a computer partition
    unmarshalled_usage = xml_marshaller.xml_marshaller.loads(usage)

    # Creates the Packing List
    usage_report_sale_packing_list_document = \
      sale_packing_list_module.newContent(
        portal_type = sale_packing_list_portal_type,
      )
    usage_report_sale_packing_list_document.confirm()
    usage_report_sale_packing_list_document.start()

    # Adds a new SPL line for each Computer Partition
    for computer_partition_usage in unmarshalled_usage\
        .computer_partition_usage_list:
      #Get good packing list line for a computer_partition
      computer_partition_document = self.\
                _getComputerPartitionDocument(
                  computer.getReference(),
                  computer_partition_usage.getId()
                )
      instance_setup_sale_packing_line = \
          self._getDocument(
                    portal_type='Sale Packing List Line',
                    simulation_state='stopped',
                    aggregate_relative_url=computer_partition_document\
                      .getRelativeUrl(),
                    resource_relative_url=self.portal_preferences\
                      .getPreferredInstanceSetupResource()
          )

      # Fetching documents
      software_release_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=software_release_portal_type
              )[0]
          )
      hosting_subscription_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=hosting_subscription_portal_type
              )[0]
          )
      software_instance_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=software_instance_portal_type
              )[0]
          )
      # Creates the usage document
      usage_report_document = usage_report_module.newContent(
        portal_type = usage_report_portal_type,
        text_content = computer_partition_usage.usage,
        causality_value = computer_partition_document
      )
      usage_report_document.validate()
      # Creates the line
      usage_report_sale_packing_list_document.newContent(
        portal_type = sale_packing_list_line_portal_type,
        # We assume that "Usage Report" is an existing service document
        resource_value = self._getUsageReportServiceDocument(),
        aggregate_value_list = [usage_report_document, \
          computer_partition_document, software_release_document, \
          hosting_subscription_document, software_instance_document
        ]
      )

  def _reportUsage(self, computer_partition, usage):
    """Warning : deprecated method."""
    portal_type = 'Usage Report'
    module = self.getPortalObject().getDefaultModule(portal_type)
    usage_report = module.newContent(
      portal_type=portal_type,
      text_content=usage,
      causality_value=computer_partition
    )
    usage_report.validate()

  @convertToREST
  def _softwareReleaseError(self, url, computer_id, error_log):
    """
    Log the computer status
    """
    user = self.getPortalObject().portal_membership.getAuthenticatedMember()\
                                                   .getUserName()
    self._logAccess(
        user, computer_id, '#error while installing %s' % url)

InitializeClass(SlapTool)
