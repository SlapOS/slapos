person = context.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  return False

if required_role_list is None:
  required_role_list = context.getLayoutProperty('layout_required_role', [])

if not len(required_role_list):
  return True

for role in required_role_list:
  if person.Person_hasRequiredRole(role):
    return True

return False
