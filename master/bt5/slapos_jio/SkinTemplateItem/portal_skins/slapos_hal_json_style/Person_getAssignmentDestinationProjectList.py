if REQUEST is not None:
  raise Unauthorized

# Use a script for overcome security
return [i.getDestinationProject() for i in context.objectValues(portal_type="Assignment")
          if i.getDestinationProject() and i.getValidationState() == "open"]
