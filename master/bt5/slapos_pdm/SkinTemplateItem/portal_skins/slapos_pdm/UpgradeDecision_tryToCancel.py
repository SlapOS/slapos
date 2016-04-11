upgrade_decision = context
cancellable_state_list = ['confirmed', 'planned']
require_state_list = ['rejected', 'confirmed', 'planned']
simulation_state = upgrade_decision.getSimulationState()

if simulation_state in require_state_list:
  current_release = upgrade_decision.UpgradeDecision_getSoftwareRelease()
  if not current_release:
    # This upgrade decision is not valid
    return False
  if current_release.getUrlString() == new_url_string:
    # Cannot cancel because the software releases are the same
    return False
  if simulation_state in cancellable_state_list:
    upgrade_decision.cancel()
  return True
else:
  return False
