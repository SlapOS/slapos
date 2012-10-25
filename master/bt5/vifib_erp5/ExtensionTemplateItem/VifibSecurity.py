###############################################################################
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
  # Caller check
  if relative_url is None:
    raise TypeError('relative_url has to be defined')
  if reference is None:
    raise TypeError('reference has to be defined')
  # micro security: can caller access software instance?
  software_instance = self.restrictedTraverse(relative_url)
  sm = getSecurityManager()
  if (software_instance.getPortalType() == "Slave Instance") and \
    (software_instance.getReference() == reference):
    # XXX There is no account for Slave Instance
    reference = SUPER_USER
  newSecurityManager(None, self.getPortalObject().acl_users.getUserById(
    reference))
  try:
    software_instance.bang(bang_tree=True, comment=comment)
  finally:
    # Restore the original user.
    setSecurityManager(sm)

