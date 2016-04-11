computer = context.REQUEST.get('here')
software_release = context

return computer.Computer_getSoftwareReleaseState(software_release.getUid())
