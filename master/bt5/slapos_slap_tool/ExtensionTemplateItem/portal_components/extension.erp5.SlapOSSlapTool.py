from Products.ERP5Type.UnrestrictedMethod import UnrestrictedMethod
from AccessControl.SecurityManagement import getSecurityManager, \
    setSecurityManager, newSecurityManager

@UnrestrictedMethod
def getComputerReferenceAndUserId(item):
  portal_type = item.getPortalType()
  computer = None

  if portal_type == 'Software Installation':
    computer = item.getAggregateValue(portal_type='Computer')
  elif portal_type == 'Computer Partition':
    computer = item.getParentValue()
  elif portal_type in ['Software Instance', 'Slave Instance']:
    partition = item.getAggregateValue(portal_type='Computer Partition')
    if partition is not None:
      computer = partition.getParentValue()

  if computer is not None and computer.getValidationState() == 'validated':
    return computer.getReference(), computer.getUserId()
  return None, None


def Item_activateFillComputerInformationCache(state_change):
  item = state_change['object']
  portal = item.getPortalObject()
  computer_reference, user_id = getComputerReferenceAndUserId(item)
  if computer_reference is None:
    return None

  if user_id is None:
    return None

  user = portal.acl_users.getUserById(user_id)

  if user is None:
    raise ValueError("User %s not found" % user_id)

  sm = getSecurityManager()
  try:
    newSecurityManager(None, user)
    portal.portal_slap._activateFillComputerInformationCache(
        computer_reference, computer_reference)
  finally:
    setSecurityManager(sm)
