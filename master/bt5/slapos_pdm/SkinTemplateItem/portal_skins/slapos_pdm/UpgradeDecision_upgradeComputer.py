if context.getSimulationState() != 'started':
  # Update Decision is not on started state, Upgrade is not possible!
  return False

computer = context.UpgradeDecision_getComputer()
software_release = context.UpgradeDecision_getSoftwareRelease()

if computer is None:
  return False

if software_release is None:
  return False 

software_release_url = software_release.getUrlString()

computer.requestSoftwareRelease(
   software_release_url=software_release_url,
   state="available")

context.stop()

return True
