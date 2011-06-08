##############################################################################
#
# Copyright (c) 2002-2010 Nexedi SA and Contributors. All Rights Reserved.
#                         Stephane COLLE <scolle@ville-sevran.fr>
#                         Romain Courteaud <romain@nexedi.com>
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

from Products.ERP5Type.Constraint import Constraint
from Products.ERP5Type.Utils import convertToUpperCase
from DateTime import DateTime

class AvailableItemOnSource(Constraint):
  """
    This method checks if an Item is available
    at the source node of a movement at the date start_date.

    Configuration example:
    { 'id'            : 'available_item',
      'description'   : '',
      'type'          : 'AvailableItemOnSource',
      'base_category' : 'aggregate',
      'portal_type'   : ('Item', ),
    },

  """

  def checkConsistency(self, obj, fixit=0):
    """
      This is the check method, we return a list of string,
      each string corresponds to an error.
    """
    if not self._checkConstraintCondition(obj):
      return []

    errors = []
    base_category = self.constraint_definition['base_category']
    portal_type = self.constraint_definition['portal_type']

    aggregate_item_uid_list = [obj.restrictedTraverse(x).getUid() for x in
         obj.getCategoryMembershipList(base_category,
         portal_type=portal_type)]

    # only if there are aggregate items, of course...
    if (len(aggregate_item_uid_list)>0):
      source_value = obj.getSourceValue()
      start_date = obj.getStartDate()
      resource_value = obj.getResourceValue()
      quantity = obj.getQuantity(0)
      #  we check if each aggregate item is actually on the source node 
      kw={}
      kw['at_time'] = start_date
      # kw['resource_uid'] = resource_value.getUid()
      if source_value is not None:
        kw['node_uid'] = source_value.getUid()
      kw['item.aggregate_uid'] = aggregate_item_uid_list

      results = obj.portal_simulation.getCurrentTrackingList(**kw)

      if (source_value is None):
        if len(results):
          error_message = "Items are already located"
          errors.append(self._generateError(obj, error_message))
      else:
        if (len(results) != len(aggregate_item_uid_list)):
          error_message = "Items must be located on source node 1"
          errors.append(self._generateError(obj, error_message))
        else:
          for result in results:
            if (result.uid not in aggregate_item_uid_list):
              error_message = "Items must be located on source node 2"
              errors.append(self._generateError(obj, error_message))

    return errors
