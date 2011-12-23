##############################################################################
#
# Copyright (c) 2002-2011 Nexedi SA and Contributors. All Rights Reserved.
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

from Products.ERP5Security.ERP5GroupManager import ConsistencyError
from AccessControl.SecurityManagement import getSecurityManager, \
             setSecurityManager, newSecurityManager
from AccessControl import Unauthorized

def restrictMethodAsShadowUser(self, open_order=None, callable_object=None,
    argument_list=None, argument_dict=None):
  """
  Restrict the security access of a method to the unaccessible shadow user
  associated to the current user.
  """
  if argument_list is None:
    argument_list = []
  if argument_dict is None:
    argument_dict = {}
  if open_order is None or callable_object is None:
    raise TypeError('open_order and callable_object cannot be None')
  relative_url = open_order.getRelativeUrl()
  if open_order.getPortalType() != 'Open Sale Order':
    raise Unauthorized("%s is not an Open Sale Order" % relative_url)
  else:
    # Check that open order is the validated one for the current user
    if open_order.getValidationState() != 'validated':
      raise Unauthorized('Open Sale Order %s is not validated.' % relative_url)

    acl_users = open_order.getPortalObject().acl_users
    # Switch to the shadow user temporarily, so that the behavior would not
    # change even if this method is invoked by random users.
    sm = getSecurityManager()
    newSecurityManager(None, acl_users.getUserById(open_order.getReference()))
    try:
      return callable_object(*argument_list, **argument_dict)
    finally:
      # Restore the original user.
      setSecurityManager(sm)

def SoftwareInstance_bangAsSelf(self, relative_url=None, reference=None,
  comment=None):
  """Call bang on self."""
  # micro security: can caller access software instance?
  software_instance = self.restrictedTraverse(relative_url)
  sm = getSecurityManager()
  newSecurityManager(None, self.getPortalObject().acl_users.getUserById(
    reference))
  try:
    software_instance.reportComputerPartitionBang(comment=comment)
  finally:
    # Restore the original user.
    setSecurityManager(sm)

def SoftwareInstance_requestDestroySlaveInstanceRelated(self):
  """ request destroy all Slave Instance allocated in the Computer Partition 
  related to the Software Instance """
  sm = getSecurityManager()
  portal = self.getPortalObject()
  service_relative_url = portal.portal_preferences.getPreferredInstanceCleanupResource()
  newSecurityManager(None, portal.acl_users.getUserById(
    self.getReference()))
  computer_partition_relative_url = self.getAggregateRelatedValue(
    "Sale Packing List Line").getAggregate(portal_type="Computer Partition")
  portal_preferences = portal.portal_preferences
  simulation_state = ["started", "confirmed"]
  service_uid_list = [
    portal.restrictedTraverse(portal_preferences.getPreferredInstanceHostingResource()).getUid(),
    portal.restrictedTraverse(portal_preferences.getPreferredInstanceSetupResource()).getUid(),
  ]
  try:
    result_list = self.portal_catalog(portal_type="Sale Packing List Line",
       aggregate_portal_type="Slave Instance",
       computer_partition_relative_url=computer_partition_relative_url,
       simulation_state=simulation_state,
       default_resource_uid=service_uid_list)
    slave_instance_list = [line.getAggregateValue(portal_type="Slave Instance") for line in result_list]
    for slave_instance in slave_instance_list:
      cleanup_packing_list = self.portal_catalog(
         portal_type='Sale Packing List Line',
         aggregate_relative_url=slave_instance.getRelativeUrl(),
         resource_relative_url=service_relative_url,
         limit=1,
      )
      if len(cleanup_packing_list) == 0:
        slave_instance.requestDestroyComputerPartition()
  finally:
    # Restore the original user.
    setSecurityManager(sm)

def SoftwareInstance_destroySlaveInstanceRelated(self):
  """ destroy all Slave Instance allocated in the Computer Partition 
  related to the Software Instance """
  sm = getSecurityManager()
  newSecurityManager(None, self.getPortalObject().acl_users.getUserById(
    self.getReference()))
  portal = self.getPortalObject()
  portal_preferences = portal.portal_preferences
  computer_partition_relative_url = self.getAggregateRelatedValue(
    "Sale Packing List Line").getAggregate(portal_type="Computer Partition")
  simulation_state = ["confirmed"]
  service_uid_list = [
    portal.restrictedTraverse(portal_preferences.getPreferredInstanceCleanupResource()).getUid(),
  ]
  try:
    result_list = self.portal_catalog(portal_type="Sale Packing List Line",
       aggregate_portal_type="Slave Instance",
       computer_partition_relative_url=computer_partition_relative_url,
       simulation_state=simulation_state,
       default_resource_uid=service_uid_list)
    slave_instance_list = [line.getAggregateValue(portal_type="Slave Instance") for line in result_list]
    # restore the original user to destroy each Slave Instance
    setSecurityManager(sm)
    for slave_instance in slave_instance_list:
      slave_instance.destroyComputerPartition()
  finally:
    # Restore the original user.
    setSecurityManager(sm)

def getComputerSecurityCategory(self, base_category_list, user_name, 
                                object, portal_type):
  """
  This script returns a list of dictionaries which represent
  the security groups which a computer is member of.
  """
  category_list = []

  computer_list = self.portal_catalog.unrestrictedSearchResults(
    portal_type='Computer', 
    reference=user_name,
    validation_state="validated",
    limit=2,
  )

  if len(computer_list) == 1:
    for base_category in base_category_list:
      if base_category == "role":
        category_list.append(
         {base_category: ['role', 'role/computer']})
  elif len(computer_list) > 1:
    raise ConsistencyError, "Error: There is more than one Computer " \
                            "with reference '%s'" % user_name

  return category_list

def getSoftwareInstanceSecurityCategory(self, base_category_list, user_name, 
                                object, portal_type):
  """
  This script returns a list of dictionaries which represent
  the security groups which a Software Instance is member of.
  """
  category_list = []

  software_instance_list = self.portal_catalog.unrestrictedSearchResults(
    portal_type='Software Instance', 
    reference=user_name,
    validation_state="validated",
    limit=2,
  )

  if len(software_instance_list) == 1:
    category_dict = {}
    for base_category in base_category_list:
      if base_category == "role":
        category_dict.setdefault(base_category, []).extend(['role', 'role/instance'])
      if base_category == "aggregate":
        software_instance = software_instance_list[0]
        current_delivery_line = self.portal_catalog.unrestrictedGetResultValue(
          portal_type='Sale Packing List Line',
          aggregate_uid=software_instance.getUid(),
          simulation_state=self.getPortalCurrentInventoryStateList() + \
              self.getPortalFutureInventoryStateList() + \
              self.getPortalReservedInventoryStateList() + \
              self.getPortalTransitInventoryStateList(),
          sort_on=(('movement.start_date', 'DESC'),)
        )
        if current_delivery_line is not None:
          hosting_item = current_delivery_line.getAggregateValue(portal_type='Hosting Subscription')
          if hosting_item is not None:
            category_dict.setdefault(base_category, []).append(hosting_item.getRelativeUrl())
    category_list.append(category_dict)
  elif len(software_instance_list) > 1:
    raise ConsistencyError, "Error: There is more than one Software Instance " \
                            "with reference %r" % user_name

  return category_list

