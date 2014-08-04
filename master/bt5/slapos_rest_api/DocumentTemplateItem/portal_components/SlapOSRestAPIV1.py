# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
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

from Acquisition import Implicit
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from Products.SlapOS.SlapOSMachineAuthenticationPlugin import getUserByLogin
from Products.ERP5Type import Permissions
from ComputedAttribute import ComputedAttribute
from zLOG import LOG, ERROR
from lxml import etree
import json
import transaction
from App.Common import rfc1123_date
from DateTime import DateTime
import re

class WrongRequest(Exception):
  pass

def etreeXml(d):
  r = etree.Element('instance')
  for k, v in d.iteritems():
    v = str(v)
    etree.SubElement(r, "parameter", attrib={'id': k}).text = v
  return etree.tostring(r, pretty_print=True, xml_declaration=True,
    encoding='utf-8')

def jsonify(d):
  return json.dumps(d, indent=2)

def requireHeader(header_dict):
  def outer(fn):
    def wrapperRequireHeader(self, *args, **kwargs):
      problem_dict = {}
      for header, value in header_dict.iteritems():
        send_header = self.REQUEST.getHeader(header)
        if send_header is None or not re.match(value, send_header):
          problem_dict[header] = 'Header with value %r is required.' % value
      if not problem_dict:
        return fn(self, *args, **kwargs)
      else:
        self.REQUEST.response.setStatus(400)
        self.REQUEST.response.setBody(jsonify(problem_dict))
        return self.REQUEST.response

    wrapperRequireHeader.__doc__ = fn.__doc__
    return wrapperRequireHeader
  return outer

def supportModifiedSince(document_url_id):
  def outer(fn):
    def wrapperSupportModifiedSince(self, *args, **kwargs):
      modified_since = self.REQUEST.getHeader('If-Modified-Since')
      if modified_since is not None:
        # RFC 2616 If-Modified-Since support
        try:
          modified_since = DateTime(self.REQUEST.getHeader('If-Modified-Since'))
        except Exception:
          # client sent wrong header, shall be ignored
          pass
        else:
          if modified_since <= DateTime():
            # client send date before current time, shall continue and
            # compare with second precision, as client by default shall set
            # If-Modified-Since to last known Last-Modified value
            document = self.restrictedTraverse(getattr(self, document_url_id))
            document_date = document.getModificationDate() or \
              document.bobobase_modification_time()
            if int(document_date.timeTime()) <= int(modified_since.timeTime()):
              # document was not modified since
              self.REQUEST.response.setStatus(304)
              return self.REQUEST.response

      return fn(self, *args, **kwargs)

    wrapperSupportModifiedSince.__doc__ = fn.__doc__
    return wrapperSupportModifiedSince
  return outer

def encode_utf8(s):
  return s.encode('utf-8')

def requireParameter(json_dict, optional_key_list=None):
  if optional_key_list is None:
    optional_key_list = []
  def outer(fn):
    def wrapperRequireJson(self, *args, **kwargs):

      self.jbody = {}

      error_dict = {}
      for key, type_ in json_dict.iteritems():
        if key not in self.REQUEST:
          if key not in optional_key_list:
            error_dict[key] = 'Missing.'
        else:
          value = self.REQUEST[key]
          method = None
          if type(type_) in (tuple, list):
            type_, method = type_
          if type_ == unicode:
            value = '"%s"' % value
          try:
            value = json.loads(value)
          except Exception:
            error_dict[key] = 'Malformed value.'
          else:
            if not isinstance(value, type_):
              error_dict[key] = '%s is not %s.' % (type(value
                ).__name__, type_.__name__)
            if method is None:
              self.jbody[key] = value
            else:
              try:
                self.jbody[key] = method(value)
              except Exception:
                error_dict[key] = 'Malformed value.'

      if error_dict:
        self.REQUEST.response.setStatus(400)
        self.REQUEST.response.setBody(jsonify(error_dict))
        return self.REQUEST.response
      return fn(self, *args, **kwargs)
    wrapperRequireJson.__doc__ = fn.__doc__
    return wrapperRequireJson

  return outer

def requireJson(json_dict, optional_key_list=None):
  if optional_key_list is None:
    optional_key_list = []
  def outer(fn):
    def wrapperRequireJson(self, *args, **kwargs):
      self.REQUEST.stdin.seek(0)
      try:
        self.jbody = json.load(self.REQUEST.stdin)
      except Exception:
        self.REQUEST.response.setStatus(400)
        self.REQUEST.response.setBody(jsonify(
          {'error': 'Data is not json object.'}))
        return self.REQUEST.response
      else:
        error_dict = {}
        for key, type_ in json_dict.iteritems():
          if key not in self.jbody:
            if key not in optional_key_list:
              error_dict[key] = 'Missing.'
          elif key in self.jbody:
            method = None
            if type(type_) in (tuple, list):
              type_, method = type_
            if not isinstance(self.jbody[key], type_):
              error_dict[key] = '%s is not %s.' % (type(self.jbody[key]
                ).__name__, type_.__name__)
            if method is not None:
              try:
                self.jbody[key] = method(self.jbody[key])
              except Exception:
                error_dict[key] = 'Malformed value.'
        if error_dict:
          self.REQUEST.response.setStatus(400)
          self.REQUEST.response.setBody(jsonify(error_dict))
          return self.REQUEST.response
        return fn(self, *args, **kwargs)
    wrapperRequireJson.__doc__ = fn.__doc__
    return wrapperRequireJson
  return outer

def responseSupport(anonymous=False):
  def outer(fn):
    def wrapperResponseSupport(self, *args, **kwargs):
      self.REQUEST.response.setHeader('Content-Type', 'application/json')
      request_headers = self.REQUEST.getHeader('Access-Control-Request-Headers')
      if request_headers:
        self.REQUEST.response.setHeader('Access-Control-Allow-Headers',
          request_headers)
      self.REQUEST.response.setHeader('Access-Control-Allow-Origin', '*')
      self.REQUEST.response.setHeader('Access-Control-Allow-Methods', 'DELETE, PUT, POST, '
        'GET, OPTIONS')
      if not anonymous:
        if getSecurityManager().getUser().getId() is None:
          if self.REQUEST.get('USER_CREATION_IN_PROGRESS') is not None:
            # inform that user is not ready yet
            self.REQUEST.response.setStatus(202)
            self.REQUEST.response.setBody(jsonify(
              {'status':'User under creation.'}))
          else:
            # force login
            self.REQUEST.response.setStatus(401)
            self.REQUEST.response.setHeader('WWW-Authenticate', 'Bearer realm="%s"'%
              self.getAPIRoot())
            self.REQUEST.response.setHeader('Location', self.getPortalObject()\
              .portal_preferences.getPreferredRestApiTokenServerUrl())
          return self.REQUEST.response
        else:
          user_name = self.getPortalObject().portal_membership\
            .getAuthenticatedMember()
          user_document = getUserByLogin(self.getPortalObject(),
            str(user_name))
          if len(user_document) != 1:
            transaction.abort()
            LOG('SlapOSRestApiV1', ERROR,
              'Currenty logged in user %r wrong document list %r.'%
                (user_name, user_document))
            self.REQUEST.response.setStatus(500)
            self.REQUEST.response.setBody(jsonify({'error':
              'There is system issue, please try again later.'}))
            return self.REQUEST.response
          self.user_url = user_document[0].getRelativeUrl()
      return fn(self, *args, **kwargs)
    wrapperResponseSupport.__doc__ = fn.__doc__
    return wrapperResponseSupport
  return outer

def extractDocument(portal_type):
  if not isinstance(portal_type, (list, tuple)):
    portal_type = [portal_type]
  def outer(fn):
    def wrapperExtractDocument(self, *args, **kwargs):
      if not self.REQUEST['traverse_subpath']:
        self.REQUEST.response.setStatus(404)
        return self.REQUEST.response
      path = self.REQUEST['traverse_subpath'][:2]
      try:
        document = self.getPortalObject().restrictedTraverse(path)
        if getattr(document, 'getPortalType', None) is None or \
          document.getPortalType() not in portal_type:
          raise WrongRequest('%r is neiter of %s' % (path, ', '.join(
            portal_type)))
        self.document_url = document.getRelativeUrl()
      except WrongRequest:
        LOG('SlapOSRestApiV1', ERROR,
          'Problem while trying to find document:', error=True)
        self.REQUEST.response.setStatus(404)
      except (Unauthorized, KeyError):
        self.REQUEST.response.setStatus(404)
      except Exception:
        LOG('SlapOSRestApiV1', ERROR,
          'Problem while trying to find instance:', error=True)
        self.REQUEST.response.setStatus(500)
        self.REQUEST.response.setBody(jsonify({'error':
          'There is system issue, please try again later.'}))
      else:
        self.REQUEST['traverse_subpath'] = self.REQUEST['traverse_subpath'][2:]
        return fn(self, *args, **kwargs)
      return self.REQUEST.response
    wrapperExtractDocument.__doc__ = fn.__doc__
    return wrapperExtractDocument
  return outer

class GenericPublisher(Implicit):
  @responseSupport(True)
  def OPTIONS(self, *args, **kwargs):
    """HTTP OPTIONS implementation"""
    self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

  def __before_publishing_traverse__(self, self2, request):
    path = request['TraversalRequestNameStack']
    subpath = path[:]
    path[:] = []
    subpath.reverse()
    request.set('traverse_subpath', subpath)

class InstancePublisher(GenericPublisher):
  """Instance publisher"""

  @responseSupport()
  @requireHeader({'Content-Type': '^application/json.*'})
  @requireJson(dict(
    title=(unicode, encode_utf8),
    connection=dict
  ), ['title', 'connection'])
  @extractDocument(['Software Instance', 'Slave Instance'])
  def PUT(self):
    """Instance PUT support"""
    d = {}
    try:
      self.REQUEST.response.setStatus(204)
      software_instance = self.restrictedTraverse(self.document_url)
      if 'title' in self.jbody and \
          software_instance.getTitle() != self.jbody['title']:
        software_instance.setTitle(self.jbody['title'])
        d['title'] = 'Modified.'
        self.REQUEST.response.setStatus(200)
      if 'connection' in self.jbody:
        xml = etreeXml(self.jbody['connection'])
        if xml != software_instance.getConnectionXml():
          software_instance.setConnectionXml(xml)
          d['connection'] = 'Modified.'
          self.REQUEST.response.setStatus(200)
    except Exception:
      transaction.abort()
      LOG('SlapOSRestApiV1', ERROR,
        'Problem while modifying:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      if d:
        self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  @requireHeader({'Content-Type': '^application/json.*'})
  @requireJson(dict(log=unicode))
  @extractDocument(['Software Instance', 'Slave Instance'])
  def __bang(self):
    try:
      self.restrictedTraverse(self.document_url
        ).bang(bang_tree=True, comment=self.jbody['log'])
    except Exception:
      LOG('SlapOSRestApiV1', ERROR,
        'Problem while trying to generate instance dict:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

  @requireHeader({'Content-Type': '^application/json.*'})
  @requireJson(dict(
    slave=bool,
    software_release=(unicode, encode_utf8),
    title=(unicode, encode_utf8),
    software_type=(unicode, encode_utf8),
    parameter=(dict, etreeXml),
    sla=(dict, etreeXml),
    status=(unicode, encode_utf8),
  ))
  def __request(self):
    request_dict = {}
    for k_j, k_i in (
        ('software_release', 'software_release'),
        ('title', 'software_title'),
        ('software_type', 'software_type'),
        ('parameter', 'instance_xml'),
        ('sla', 'sla_xml'),
        ('slave', 'shared'),
        ('status', 'state')
      ):
      request_dict[k_i] = self.jbody[k_j]

    if request_dict['state'] not in ['started', 'stopped', 'destroyed']:
      self.REQUEST.response.setStatus(400)
      self.REQUEST.response.setBody(jsonify(
        {'status': 'Status shall be one of: started, stopped, destroyed.'}))
      return self.REQUEST.response
    try:
      self.restrictedTraverse(self.user_url
        ).requestSoftwareInstance(**request_dict)
    except Exception:
      transaction.abort()
      LOG('SlapOSRestApiV1', ERROR,
        'Problem with person.requestSoftwareInstance:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
      return self.REQUEST.response

    self.REQUEST.response.setStatus(202)
    self.REQUEST.response.setBody(jsonify({'status':'processing'}))
    return self.REQUEST.response

  @requireParameter(dict(
    slave=bool,
    software_release=(unicode, encode_utf8),
    software_type=(unicode, encode_utf8),
    sla=dict,
  ))
  def __allocable(self):
    try:
      user = self.restrictedTraverse(self.user_url)
      user_portal_type = user.getPortalType()
      if user_portal_type == 'Person':
        pass
      elif user_portal_type == 'Software Instance':
        hosting_subscription = user.getSpecialiseValue(
          portal_type="Hosting Subscription")
        user = hosting_subscription.getDestinationSectionValue(
          portal_type="Person")
      else:
        raise NotImplementedError, "Can not get Person document"
      result = user.Person_restrictMethodAsShadowUser(
        shadow_document=user,
        callable_object=user.Person_findPartition,
        argument_list=[
          self.jbody['software_release'],
          self.jbody['software_type'],
          ('Software Instance', 'Slave Instance')[int(self.jbody['slave'])],
          self.jbody['sla']],
        argument_dict={
          'test_mode': True})
    except Exception:
      transaction.abort()
      LOG('SlapOSRestApiV1', ERROR,
        'Problem with person.allocable:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
      return self.REQUEST.response

    self.REQUEST.response.setStatus(200)
    self.REQUEST.response.setHeader('Cache-Control', 
                                    'no-cache, no-store')
    self.REQUEST.response.setBody(jsonify({'result': result}))
    return self.REQUEST.response

  @extractDocument(['Software Instance', 'Slave Instance'])
  @supportModifiedSince('document_url')
  def __instance_info(self):
    certificate = False
    software_instance = self.restrictedTraverse(self.document_url)
    if self.REQUEST['traverse_subpath'] and self.REQUEST[
        'traverse_subpath'][-1] == 'certificate':
      certificate = True
    try:
      if certificate:
        d = {
          "ssl_key": software_instance.getSslKey(),
          "ssl_certificate": software_instance.getSslCertificate()
        }
      else:
        d = {
          "title": software_instance.getTitle(),
          "status": software_instance.getSlapState(),
          "software_release": software_instance.getUrlString(),
          "software_type": software_instance.getSourceReference(),
          "slave": software_instance.getPortalType() == 'Slave Instance',
          "connection": software_instance.getConnectionXmlAsDict(),
          "parameter": software_instance.getInstanceXmlAsDict(),
          "sla": software_instance.getSlaXmlAsDict(),
          "children_list": [self.getAPIRoot() + '/' + q.getRelativeUrl() \
            for q in software_instance.getPredecessorValueList()],
          "partition": { # not ready yet
            "public_ip": [],
            "private_ip": [],
            "tap_interface": "",
          }
        }
    except Exception:
      LOG('SlapOSRestApiV1', ERROR,
        'Problem while trying to generate instance dict:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      self.REQUEST.response.setStatus(200)
      # Note: Last-Modified will result in resending certificate many times,
      # because each modification of instance will result in new Last-Modified
      # TODO: Separate certificate from instance and use correct
      # Last-Modified header of subobject containing certificate
      self.REQUEST.response.setHeader('Last-Modified',
        rfc1123_date(software_instance.getModificationDate()))
      # Say that content is publicly cacheable. It is only required in order to
      # *force* storing content on clients' disk in case of using HTTPS
      self.REQUEST.response.setHeader('Cache-Control', 'must-revalidate')
      self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  def __instance_list(self):
    kw = dict(
      portal_type=('Software Instance', 'Slave Instance'),
    )
    d = {"list": []}
    a = d['list'].append
    for si in self.getPortalObject().portal_catalog(**kw):
      a('/'.join([self.getAPIRoot(), 'instance', si.getRelativeUrl()]))
    try:
      d['list'][0]
    except IndexError:
      # no results, so nothing to return
      self.REQUEST.response.setStatus(204)
    else:
      self.REQUEST.response.setStatus(200)
      self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  @responseSupport()
  def __call__(self):
    """Instance GET/POST support"""
    if self.REQUEST['REQUEST_METHOD'] == 'POST':
      if self.REQUEST['traverse_subpath'] and \
        self.REQUEST['traverse_subpath'][-1] == 'bang':
        self.__bang()
      else:
        self.__request()
    elif self.REQUEST['REQUEST_METHOD'] == 'GET':
      if self.REQUEST['traverse_subpath']:
        if self.REQUEST['traverse_subpath'][-1] == 'request':
          self.__allocable()
        else:
          self.__instance_info()
      else:
        self.__instance_list()


class ComputerPublisher(GenericPublisher):
  @responseSupport()
  @requireHeader({'Content-Type': '^application/json.*'})
  @extractDocument('Computer')
  @requireJson(dict(
    partition=list,
    software=list
  ), ['partition', 'software'])
  def PUT(self):
    """Computer PUT support"""
    computer = self.restrictedTraverse(self.document_url)
    error_dict = {}
    def getErrorDict(list_, key_list, prefix):
      no = 0
      for dict_ in list_:
        error_list = []
        if not isinstance(dict_, dict):
          error_list.append('Not a dict.')
        else:
          for k in key_list:
            if k not in dict_:
              error_list.append('Missing key "%s".' % k)
            elif not isinstance(dict_[k], unicode):
              error_list.append('Key "%s" is not unicode.' % k)
            elif k == 'status' and dict_[k] not in ['installed',
              'uninstalled', 'error']:
              error_list.append('Status "%s" is incorrect.' % dict_[k])
        if len(error_list) > 0:
          error_dict['%s_%s' % (prefix, no)] = error_list
        no += 1
      return error_dict

    error_dict = {}
    transmitted = False
    if 'partition' in self.jbody:
      error_dict.update(getErrorDict(self.jbody['partition'],
        ('title', 'public_ip', 'private_ip', 'tap_interface'), 'partition'))
      transmitted = True
    if 'software' in self.jbody:
      error_dict.update(getErrorDict(self.jbody['software'],
        ('software_release', 'status', 'log'), 'software'))
      transmitted = True
      # XXX: Support status as enum.
    if error_dict:
      self.REQUEST.response.setStatus(400)
      self.REQUEST.response.setBody(jsonify(error_dict))
      return self.REQUEST.response

    if transmitted:
      try:
        computer.Computer_updateFromJson(self.jbody)
      except Exception:
        transaction.abort()
        LOG('SlapOSRestApiV1', ERROR,
          'Problem while trying to update computer:', error=True)
        self.REQUEST.response.setStatus(500)
        self.REQUEST.response.setBody(jsonify({'error':
          'There is system issue, please try again later.'}))
        return self.REQUEST.response
    self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

class StatusPublisher(GenericPublisher):

  @responseSupport()
  def __call__(self):
    """Log GET support"""
    if self.REQUEST['REQUEST_METHOD'] == 'POST':
      self.REQUEST.response.setStatus(404)
      return self.REQUEST.response
    elif self.REQUEST['REQUEST_METHOD'] == 'GET':
      if self.REQUEST['traverse_subpath']:
        self.__status_info()
      else:
        self.__status_list()

  def __status_list(self):
    portal = self.getPortalObject()
    open_friend = portal.restrictedTraverse(
      "portal_categories/allocation_scope/open/friend", None).getUid()
    open_personal = portal.restrictedTraverse(
      "portal_categories/allocation_scope/open/personal", None).getUid()
    open_public = portal.restrictedTraverse(
      "portal_categories/allocation_scope/open/public", None).getUid()

    kw = dict(
      validation_state="validated",
      portal_type=['Computer', 'Software Installation', 'Software Instance']
      )
    d = {"list": []}
    a = d['list'].append
    for si in self.getPortalObject().portal_catalog(**kw):
      if (si.getPortalType() == "Software Instance" or \
           si.getPortalType() == "Software Installation") and \
           si.getSlapState() not in ['start_requested','stop_requested']:
        continue
      if si.getPortalType() == "Computer" and \
           si.getAllocationScopeUid() not in [open_friend, open_personal, open_public]:
        continue
      
      a('/'.join([self.getAPIRoot(), 'status', si.getRelativeUrl()]))
    try:
      d['list'][0]
    except IndexError:
      # no results, so nothing to return
      self.REQUEST.response.setStatus(204)
    else:
      self.REQUEST.response.setStatus(200)
      self.REQUEST.response.setHeader('Cache-Control', 
                                      'max-age=300, private')
      self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  # XXX Use a decated document to keep the history
  @extractDocument(['Computer', 'Software Installation',  'Software Instance'])
#   @supportModifiedSince('document_url')
  def __status_info(self):
    certificate = False
    document = self.restrictedTraverse(self.document_url)
    try:
      memcached_dict = self.getPortalObject().portal_memcached.getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
      try:
        d = memcached_dict[document.getReference()]
      except KeyError:
        d = {
          "user": "SlapOS Master",
          'created_at': '%s' % rfc1123_date(DateTime()),
          "text": "#error no data found for %s" % document.getReference()
        }
      else:
        d = json.loads(d)
    except Exception:
      LOG('SlapOSRestApiV1', ERROR,
        'Problem while trying to generate status information:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      d['@document'] = self.document_url
      self.REQUEST.response.setStatus(200)
      self.REQUEST.response.setHeader('Cache-Control', 
                                      'max-age=300, private')
      self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

class SlapOSRestAPIV1(Implicit):
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)
  security.declarePublic('instance')

  security.declarePublic('getAPIRoot')
  def getAPIRoot(self):
    """Returns the root of API"""
    return self.absolute_url() + '/v1'

  @ComputedAttribute
  def instance(self):
    """Instance publisher"""
    return InstancePublisher().__of__(self)

  security.declarePublic('computer')
  @ComputedAttribute
  def computer(self):
    """Computer publisher"""
    return ComputerPublisher().__of__(self)

  security.declarePublic('log')
  @ComputedAttribute
  def status(self):
    """Status publisher"""
    return StatusPublisher().__of__(self)

  @responseSupport(True)
  def OPTIONS(self, *args, **kwargs):
    """HTTP OPTIONS implementation"""
    self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

  security.declarePublic('__call__')
  @responseSupport(True)
  def __call__(self):
    """Possible API discovery"""
    self.REQUEST.response.setStatus(400)
    return self.REQUEST.response
