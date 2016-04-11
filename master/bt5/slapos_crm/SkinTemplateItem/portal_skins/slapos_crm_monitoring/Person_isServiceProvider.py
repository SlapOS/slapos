if 'service_provider' in context.getRoleList():
  return True

for assignment in context.contentValues(portal_type="Assignment"):
  if assignment.getValidationState() == "open" and \
    assignment.getRole() == 'service_provider':
    return True

return False
