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
    'accounting_module',
    'account_module',
    'campaign_module',
    'component_module',
    'currency_module',
    'document_ingestion_module',
    'document_module',
    'event_module',
    'image_module',
    'internal_packing_list_module',
    'inventory_module',
    'knowledge_pad_module',
    'meeting_module',
    'notification_message_module',
    'open_sale_order_module',
    'organisation_module',
    'person_module',
    'product_module',
    'purchase_order_module',
    'purchase_packing_list_module',
    'purchase_trade_condition_module',
    'query_module',
    'sale_opportunity_module',
    'sale_order_module',
    'sale_packing_list_module',
    'sale_trade_condition_module',
    'service_module',
    'software_product_module',
    'software_release_module',
    'support_request_module',
    'transformation_module',
    'web_page_module',
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

    error_list = []
    for module_id in portal.objectIds(spec=('ERP5 Folder',)):
      if module_id in self.used_module_id_list:
        try:
          portal.restrictedTraverse(module_id)
        except Unauthorized:
          error_list.append("User can not access '%s'" % module_id)
      else:
        try:
          self.assertRaises(Unauthorized, portal.restrictedTraverse, module_id)
        except AssertionError:
          error_list.append("User can access '%s'" % module_id)
    self.assertEqual([], error_list, '\n'.join(error_list))
