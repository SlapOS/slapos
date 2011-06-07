##############################################################################
#
# Copyright (c) 2002-2010 Nexedi SA and Contributors. All Rights Reserved.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from VifibMixin import testVifibMixin
from zExceptions import Unauthorized
 
class TestVifibModuleSecurity(testVifibMixin):
  """
  Test Vifib Person security
  """
 
  used_module_id_list = [
    'knowledge_pad_module',
    'web_site_module',
  ]
 
  def getTitle(self):
    return "Test Vifib Module security"
 
  def test_VifibUserCanNotAccessModules(self):
    """
    Check if member of vifib group can not access modules.
    """
    portal = self.getPortal()
    self.login(user_name='test_vifib_member')
 
    for module_id in portal.objectIds(spec=('ERP5 Folder',)):
      if module_id in self.used_module_id_list:
        try:
          portal.restrictedTraverse(module_id)
        except Unauthorized:
          raise AssertionError, "User can not access '%s'" % module_id
      else:
        try:
          self.assertRaises(Unauthorized, portal.restrictedTraverse, module_id)
        except AssertionError:
          raise AssertionError, "User can access '%s'" % module_id
