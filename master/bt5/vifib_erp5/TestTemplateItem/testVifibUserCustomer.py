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
from DateTime import DateTime
from random import random
import transaction

class TestVifibUserCustomer(testVifibMixin):
  """
  Test Vifib User: customer access to the system
  """

  def getTitle(self):
    return "Test Vifib User Customer security"

  def test_base_UserCustomerCanRequestAnInstance(self):
    """
    Check if customer can request an instance
    """
    login_id = 'test_vifib_customer'
    self.login(user_name=login_id)

    # User has to access his person profile
    person_module_id = self.portal.getDefaultModuleId(portal_type='Person')
    person_module = self.portal.restrictedTraverse(person_module_id)
    person_value = person_module.restrictedTraverse(login_id)

    # Access software product module
    software_product_module_id = self.portal.getDefaultModuleId(portal_type='Software Product Module')
    software_product_module = self.portal.restrictedTraverse(software_product_module_id)
    software_product_value = software_product_module.restrictedTraverse("test_software_product")

    # Access software release module
    software_release_module_id = self.portal.getDefaultModuleId(portal_type='Software Release Module')
    software_release_module = self.portal.restrictedTraverse(software_release_module_id)
    software_release_value = software_release_module.restrictedTraverse("test_software_release")

    software_title = self.id() + str(random())
    person_value.requestSoftwareInstance(
      software_release=software_release_value.getUrlString(),
      software_title=software_title,
      instance_xml='<?xml version="1.0" encoding="utf-8"?><instance/>')
    transaction.commit()
    self.tic()
    # Note: This is tricky part. Workflow methods does not return nothing
    # so the only way is to find again the computer partition.
    # But only title can be passed, that is why random is used to avoid
    # duplication
    software_instance_list = self.portal.portal_catalog(
        portal_type='Software Instance',
        title=software_title)
    self.assertEqual(1, len(software_instance_list))
    software_instance = software_instance_list[0]

    # Access vifib organisation
    organisation_module_id = self.portal.getDefaultModuleId(portal_type='Organisation')
    organisation_module = self.portal.restrictedTraverse(organisation_module_id)
    organisation_value = organisation_module.unrestrictedTraverse("vifib_internet")

    # Access currency module
    currency_module_id = self.portal.getDefaultModuleId(portal_type='Currency Module')
    currency_module = self.portal.restrictedTraverse(currency_module_id)
    currency_value = currency_module.restrictedTraverse("EUR")

    # Access service module
    service_module_id = self.portal.getDefaultModuleId(portal_type='Service Module')
    service_module = self.portal.restrictedTraverse(service_module_id)
    service_value = self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredInstanceSetupResource())

    # Access open sale order module
    open_sale_order_module_id = self.portal.getDefaultModuleId(portal_type='Open Sale Order Module')
    open_sale_order_module = self.portal.restrictedTraverse(open_sale_order_module_id)

    # Access sale packing list module
    sale_packing_list_module_id = self.portal.getDefaultModuleId(portal_type='Sale Packing List Module')
    sale_packing_list_module = self.portal.restrictedTraverse(sale_packing_list_module_id)

    # Access hosting subscription module
    hosting_subscription_module_id = self.portal.getDefaultModuleId(portal_type='Hosting Subscription Module')
    hosting_subscription_module_id = self.portal.restrictedTraverse(hosting_subscription_module_id)

    # Access computer module
    computer_module_id = self.portal.getDefaultModuleId(portal_type='Computer')
    computer_module = self.portal.restrictedTraverse(computer_module_id)

    raise NotImplementedError
