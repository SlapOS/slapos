if REQUEST is not None:
  from zExceptions import Unauthorized
  raise Unauthorized

if role_id in context.getRoleList():
  return True

for assignment in context.contentValues(portal_type="Assignment"):
  if assignment.getValidationState() == "open" and \
    assignment.getRole() == role_id:
    return True

return False
