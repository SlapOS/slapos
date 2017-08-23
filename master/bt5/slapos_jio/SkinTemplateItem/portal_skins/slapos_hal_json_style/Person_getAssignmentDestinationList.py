if REQUEST is not None:
  raise Unauthorized

# Use a script for overcome security
return [i.getDestination() for i in context.objectValues(portal_type="Assignment")
          if i.getDestination() and i.getValidationState() == "open"]
