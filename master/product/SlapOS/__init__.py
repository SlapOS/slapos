# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
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
from Products.ERP5Type.Utils import initializeProduct, updateGlobals
from AccessControl.Permissions import manage_users as ManageUsers
import sys
import Permissions
this_module = sys.modules[ __name__ ]
document_classes = updateGlobals(this_module, globals(),
    permissions_module=Permissions)
object_classes = ()
content_classes = ()
content_constructors = ()
from Tool import SlapOSRestAPITool
from Tool import StatusTool
portal_tools = (SlapOSRestAPITool.SlapOSRestAPITool, StatusTool.StatusTool)
from Products.PluggableAuthService.PluggableAuthService import registerMultiPlugin

import SlapOSMachineAuthenticationPlugin
import SlapOSShadowAuthenticationPlugin

def initialize(context):
  import Document
  initializeProduct(context, this_module, globals(), document_module=Document,
    document_classes=document_classes, object_classes=object_classes,
    portal_tools=portal_tools, content_constructors=content_constructors,
    content_classes=content_classes)

  context.registerClass( SlapOSMachineAuthenticationPlugin.SlapOSMachineAuthenticationPlugin
                         , permission=ManageUsers
                         , constructors=(
                            SlapOSMachineAuthenticationPlugin.manage_addSlapOSMachineAuthenticationPluginForm,
                            SlapOSMachineAuthenticationPlugin.addSlapOSMachineAuthenticationPlugin, )
                         , visibility=None
                         , icon='www/portal.gif'
                         )
  context.registerClass( SlapOSShadowAuthenticationPlugin.SlapOSShadowAuthenticationPlugin
                         , permission=ManageUsers
                         , constructors=(
                            SlapOSShadowAuthenticationPlugin.manage_addSlapOSShadowAuthenticationPluginForm,
                            SlapOSShadowAuthenticationPlugin.addSlapOSShadowAuthenticationPlugin, )
                         , visibility=None
                         , icon='www/portal.gif'
                         )


registerMultiPlugin(SlapOSMachineAuthenticationPlugin.SlapOSMachineAuthenticationPlugin.meta_type)
registerMultiPlugin(SlapOSShadowAuthenticationPlugin.SlapOSShadowAuthenticationPlugin.meta_type)
