person = context.getPortalObject().portal_membership.getAuthenticatedMember().getUserValue()

for assignment in person.objectValues(portal_type="Assignment"):
  if assignment.getDestinationProject() == context.getRelativeUrl():
    assignment.close()
    return
