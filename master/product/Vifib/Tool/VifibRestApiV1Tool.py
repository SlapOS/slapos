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
from Products.ERP5Type.Tool.BaseTool import BaseTool
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from Products.ERP5Type.Globals import InitializeClass
from Products.ERP5Type import Permissions
from ComputedAttribute import ComputedAttribute
from zLOG import LOG, ERROR
from lxml import etree
import json
import transaction
from App.Common import rfc1123_date
from DateTime import DateTime

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
        if self.REQUEST.getHeader(header) != value:
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

def supportModifiedSince(document_url_id=None, modified_property_id=None):
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
            document = None
            if document_url_id is None and modified_property_id is None:
              document = self
            elif document_url_id is not None:
              document = self.restrictedTraverse(getattr(self, document_url_id))
            else:
              document_date = getattr(self, modified_property_id)
            if document is not None:
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
          # force login
          self.REQUEST.response.setStatus(401)
          self.REQUEST.response.setHeader('WWW-Authenticate', 'Bearer realm="%s"'%
            self.absolute_url())
          self.REQUEST.response.setHeader('Location', self.getPortalObject()\
            .portal_preferences.getPreferredRestApiV1TokenServerUrl())
          return self.REQUEST.response
        else:
          person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
          if person is None:
            transaction.abort()
            LOG('VifibRestApiV1Tool', ERROR,
              'Currenty logged in user %r has no Person document.'%
                self.getPortalObject().getAuthenticatedMember())
            self.REQUEST.response.setStatus(500)
            self.REQUEST.response.setBody(jsonify({'error':
              'There is system issue, please try again later.'}))
            return self.REQUEST.response
          self.person_url = person.getRelativeUrl()
      return fn(self, *args, **kwargs)
    wrapperResponseSupport.__doc__ = fn.__doc__
    return wrapperResponseSupport
  return outer

def extractInstance(fn):
  def wrapperExtractInstance(self, *args, **kwargs):
    if not self.REQUEST['traverse_subpath']:
      self.REQUEST.response.setStatus(404)
      return self.REQUEST.response
    instance_path = self.REQUEST['traverse_subpath'][:2]
    try:
      software_instance = self.getPortalObject().restrictedTraverse(instance_path)
      if getattr(software_instance, 'getPortalType', None) is None or \
        software_instance.getPortalType() not in ('Software Instance',
          'Slave Instance'):
        raise WrongRequest('%r is not an instance' % instance_path)
      self.software_instance_url = software_instance.getRelativeUrl()
    except WrongRequest:
      LOG('VifibRestApiV1Tool', ERROR,
        'Problem while trying to find instance:', error=True)
      self.REQUEST.response.setStatus(404)
    except (Unauthorized, KeyError):
      self.REQUEST.response.setStatus(404)
    except Exception:
      LOG('VifibRestApiV1Tool', ERROR,
        'Problem while trying to find instance:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      self.REQUEST['traverse_subpath'] = self.REQUEST['traverse_subpath'][2:]
      return fn(self, *args, **kwargs)
    return self.REQUEST.response
  wrapperExtractInstance.__doc__ = fn.__doc__
  return wrapperExtractInstance

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
  @requireHeader({'Accept': 'application/json',
    'Content-Type': 'application/json'})
  @requireJson(dict(
    title=(unicode, encode_utf8),
    connection=dict
  ), ['title', 'connection'])
  @extractInstance
  def PUT(self):
    """Instance PUT support"""
    d = {}
    try:
      self.REQUEST.response.setStatus(204)
      software_instance = self.restrictedTraverse(self.software_instance_url)
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
      LOG('VifibRestApiV1Tool', ERROR,
        'Problem while modifying:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      if d:
        self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  @requireHeader({'Accept': 'application/json',
    'Content-Type': 'application/json'})
  @requireJson(dict(log=unicode))
  @extractInstance
  def __bang(self):
    try:
      self.restrictedTraverse(self.software_instance_url
        ).reportComputerPartitionBang(comment=self.jbody['log'])
    except Exception:
      LOG('VifibRestApiV1Tool', ERROR,
        'Problem while trying to generate instance dict:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
    else:
      self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

  @requireHeader({'Accept': 'application/json',
    'Content-Type': 'application/json'})
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
      self.restrictedTraverse(self.person_url
        ).requestSoftwareInstance(**request_dict)
    except Exception:
      transaction.abort()
      LOG('VifibRestApiV1Tool', ERROR,
        'Problem with person.requestSoftwareInstance:', error=True)
      self.REQUEST.response.setStatus(500)
      self.REQUEST.response.setBody(jsonify({'error':
        'There is system issue, please try again later.'}))
      return self.REQUEST.response

    self.REQUEST.response.setStatus(202)
    self.REQUEST.response.setBody(jsonify({'status':'processing'}))
    return self.REQUEST.response

  @requireHeader({'Accept': 'application/json'})
  @extractInstance
  @supportModifiedSince('software_instance_url')
  def __instance_info(self):
    certificate = False
    software_instance = self.restrictedTraverse(self.software_instance_url)
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
          "software_release": "", # not ready yet
          "software_type": software_instance.getSourceReference(),
          "slave": software_instance.getPortalType() == 'Slave Instance',
          "connection": software_instance.getConnectionXmlAsDict(),
          "parameter": software_instance.getInstanceXmlAsDict(),
          "sla": software_instance.getSlaXmlAsDict(),
          "children_list": [q.absolute_url() for q in \
            software_instance.getPredecessorValueList()],
          "partition": { # not ready yet
            "public_ip": [],
            "private_ip": [],
            "tap_interface": "",
          }
        }
    except Exception:
      LOG('VifibRestApiV1Tool', ERROR,
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

  software_instance_module = 'software_instance_module'
  @supportModifiedSince('software_instance_module')
  @requireHeader({'Accept': 'application/json'})
  def __instance_list(self):
    kw = dict(
      portal_type=('Software Instance', 'Slave Instance'),
    )
    d = {"list": []}
    a = d['list'].append
    for si in self.getPortalObject().portal_catalog(**kw):
      a('/'.join([self.absolute_url(), 'instance', si.getRelativeUrl()]))
    try:
      d['list'][0]
    except IndexError:
      # no results, so nothing to return
      self.REQUEST.response.setStatus(204)
    else:
      self.REQUEST.response.setHeader('Last-Modified',
        rfc1123_date(self.getPortalObject().software_instance_module\
          .bobobase_modification_time()))
      self.REQUEST.response.setHeader('Cache-Control', 'must-revalidate')
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
        self.__instance_info()
      else:
        self.__instance_list()


class VifibRestApiV1Tool(BaseTool):
  """SlapOS REST API V1 Tool"""

  id = 'portal_vifib_rest_api_v1'
  meta_type = 'ERP5 Vifib Rest API V1 Tool'
  portal_type = 'Vifib Rest API V1 Tool'
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)
  allowed_types = ()

  security.declarePublic('instance')
  @ComputedAttribute
  def instance(self):
    """Instance publisher"""
    return InstancePublisher().__of__(self)

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

  # set this date to moment of API modification
  api_modification_date = DateTime('2012/05/15 11:36 GMT+2')

  @supportModifiedSince(modified_property_id='api_modification_date')
  def __api_discovery(self):
    self.REQUEST.response.setHeader('Last-Modified',
      rfc1123_date(self.api_modification_date))
    self.REQUEST.response.setHeader('Cache-Control', 'must-revalidate')
    self.REQUEST.response.setStatus(200)
    d = {
      "discovery": {
        "authentication": False,
        "url": self.absolute_url(),
        "method": "GET",
        "required": {},
        "optional": {}
      },
      "instance_list": {
        "authentication": True,
        "url": self.absolute_url() + '/instance',
        "method": "GET",
        "required": {},
        "optional": {}
      },
      "instance_bang": {
        "authentication": True,
        "url": "{instance_url}/bang",
        "method": "POST",
        "required": {
          "log": "unicode"
        },
        "optional": {}
      },
      "instance_certificate": {
        "authentication": True,
        "url": "{instance_url}/certificate",
        "method": "GET",
        "required": {},
        "optional": {}
      },
      "instance_edit": {
        "authentication": True,
        "url": "{instance_url}",
        "method": "PUT",
        "required": {},
        "optional": {
           "title": "unicode",
           "connection": "object"
        },
      },
      "instance_info": {
        "authentication": True,
        "url": "{instance_url}",
        "method": "GET",
        "required": {},
        "optional": {}
      },
      'request_instance': {
        "authentication": True,
        'url': self.absolute_url() + '/instance',
        'method': 'POST',
        'required': {
           "status": "unicode",
           "slave": "bool",
           "title": "unicode",
           "software_release": "unicode",
           "software_type": "unicode",
           "parameter": "object",
           "sla": "object"
        },
        'optional' : {}
      }
    }
    self.REQUEST.response.setBody(jsonify(d))
    return self.REQUEST.response

  @responseSupport(True)
  def OPTIONS(self, *args, **kwargs):
    """HTTP OPTIONS implementation"""
    self.REQUEST.response.setStatus(204)
    return self.REQUEST.response

  security.declarePublic('__call__')
  @responseSupport(True)
  @requireHeader({'Accept': 'application/json'})
  def __call__(self):
    """Possible API discovery"""
    if self.REQUEST['REQUEST_METHOD'] == 'GET':
      return self.__api_discovery()
    self.REQUEST.response.setStatus(400)
    return self.REQUEST.response

InitializeClass(VifibRestApiV1Tool)
