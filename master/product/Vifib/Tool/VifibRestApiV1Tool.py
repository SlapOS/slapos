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
from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.ERP5Type.Globals import InitializeClass
from Products.ERP5Type import Permissions
from ComputedAttribute import ComputedAttribute
from zLOG import LOG, ERROR
import json
import transaction

def jsonResponse(fn):
  def wrapper(self, *args, **kwargs):
    self.REQUEST.response.setHeader('Content-Type', 'application/json')
    return fn(self, *args, **kwargs)
  wrapper.__doc__ = fn.__doc__
  return wrapper

def responseSupport(fn):
  def wrapper(self, *args, **kwargs):
    response = self.REQUEST.response
    response.setHeader('Access-Control-Allow-Origin', '*')
    response.setHeader('Access-Control-Allow-Methods', 'DELETE, PUT, POST, '
      'GET, OPTIONS')
    if getSecurityManager().getUser().getId() is None:
      # force login
      response.setStatus(401)
      response.setHeader('WWW-Authenticate', 'Bearer realm="%s"' % self.absolute_url())
      response.setHeader('Location', self.getPortalObject()\
        .portal_preferences.getPreferredRestApiV1TokenServerUrl())
      return response
    return fn(self, *args, **kwargs)
  wrapper.__doc__ = fn.__doc__
  return wrapper

class GenericPublisher(Implicit):
  def OPTIONS(self, *args, **kwargs):
    """HTTP OPTIONS implementation"""
    response = self.REQUEST.response
    response.setHeader('Access-Control-Allow-Origin', '*')
    response.setHeader('Access-Control-Allow-Methods', 'DELETE, PUT, POST, '
      'GET, OPTIONS')
    response.setStatus(200)
    return response

  def __before_publishing_traverse__(self, self2, request):
    path = request['TraversalRequestNameStack']
    subpath = path[:]
    path[:] = []
    subpath.reverse()
    request.set('traverse_subpath', subpath)

class InstancePublisher(GenericPublisher):
  """Instance publisher"""

  @jsonResponse
  def __request(self):
    response = self.REQUEST.response
    self.REQUEST.stdin.seek(0)
    try:
      jbody = json.load(self.REQUEST.stdin)
    except Exception:
      response.setStatus(400)
      response.setBody(json.dumps({'error': 'Data is not json object.'}))
      return response

    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
    if person is None:
      transaction.abort()
      LOG('VifibRestApiV1Tool', ERROR,
        'Currenty logged in user %r has no Person document.'%
          self.getPortalObject().getAuthenticatedMember())
      response.setStatus(500)
      response.setBody(json.dumps({'error':
        'There is system issue, please try again later.'}))
      return response

    request_dict = {}
    error_dict = {}
    if 'slave' in jbody:
      if not isinstance(jbody['slave'], bool):
        error_dict['slave'] = 'Not boolean.'
    for k_j, k_i in (
        ('software_release', 'software_release'),
        ('title', 'software_title'),
        ('software_type', 'software_type'),
        ('parameter', 'instance_xml'),
        ('sla', 'sla_xml'),
        ('slave', 'shared'),
        ('status', 'state')
      ):
      try:
        request_dict[k_i] = jbody[k_j]
      except KeyError:
        error_dict[k_j] = 'Missing.'

    if error_dict:
      response.setStatus(400)
      response.setBody(json.dumps(error_dict))
      return response

    try:
      person.requestSoftwareInstance(**request_dict)
    except Exception:
      transaction.abort()
      LOG('VifibRestApiV1Tool', ERROR, 'Problem with request.',
          error=True)
      response.setStatus(500)
      response.setBody(json.dumps({'error':
        'There is system issue, please try again later.'}))
      return response

    response.setStatus(202)
    response.setBody(json.dumps({'status':'processing'}))
    return response

  @responseSupport
  def __call__(self):
    """Instance GET/POST support"""
    if self.REQUEST['REQUEST_METHOD'] == 'POST':
      self.__request()


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

InitializeClass(VifibRestApiV1Tool)
