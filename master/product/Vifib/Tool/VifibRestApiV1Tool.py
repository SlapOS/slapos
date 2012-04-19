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
from AccessControl import ClassSecurityInfo
from Products.ERP5Type.Globals import InitializeClass
from Products.ERP5Type import Permissions
from ComputedAttribute import ComputedAttribute

class GenericPublisher(Implicit):
  security = ClassSecurityInfo()
  security.declarePublic('OPTIONS')
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

  def prepareResponse(self):
    response = self.REQUEST.response
    response.setHeader('Content-Type', 'application/json; charset=utf-8')
    response.setHeader('Access-Control-Allow-Origin', '*')
    response.setHeader('Access-Control-Allow-Methods', 'DELETE, PUT, POST, '
      'GET, OPTIONS')
    return response

class InstancePublisher(GenericPublisher):
  """Instance publisher"""
  security = ClassSecurityInfo()
  security.declareObjectPublic()

  security.declarePublic('DELETE')
  def DELETE(self, *args, **kwargs):
    """HTTP DELETE implementation"""
    response = self.prepareResponse()
    try:
      instance_id = self.REQUEST['traverse_subpath'][0]
    except IndexError:
      response.setStatus(400)
      return response

    portal = self.getPortalObject()
    person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
    instance = portal.portal_catalog.getResultValue(
      portal_type=['Software Instance', 'Slave Instance'],
      reference=instance_id)
    if instance is None:
      response.setStatus(404)
      return response
    delivery_line = instance.Item_getInstancePackingListLine()
    person.requestSoftwareInstance(
      software_release=delivery_line.getAggregateValue(
        portal_type='Software Release').getUrlString(),
      software_title=instance.getTitle(),
      shared=instance.getPortalType() == 'Slave Instance',
      instance_xml=instance.getTextContent(),
      sla_xml=instance.getSlaXml(),
      state='destroyed'
    )
    response.setStatus(202)
    return response

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
