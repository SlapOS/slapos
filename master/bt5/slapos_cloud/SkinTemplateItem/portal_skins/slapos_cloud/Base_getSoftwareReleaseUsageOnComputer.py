current = context.REQUEST.get('here')
if current.getPortalType() == 'Software Release':  
  software_release = current
  computer = context
else:
  computer = current
  software_release = context

return computer.Computer_getSoftwareReleaseUsage(software_release.getUid())
