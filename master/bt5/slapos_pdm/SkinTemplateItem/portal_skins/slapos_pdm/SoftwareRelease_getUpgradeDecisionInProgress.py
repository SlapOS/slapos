portal = context.getPortalObject()
product_reference = context.getAggregateReference()

decision_line_in_progress_list = portal.portal_catalog(
                    portal_type='Upgrade Decision Line',
                    default_aggregate_uid=aggregate_uid)

for decision_line in decision_line_in_progress_list:
  upgrade_decision = decision_line.getParentValue()
  simulation_state = upgrade_decision.getSimulationState()
  if simulation_state not in ['planned', 'confirmed',
      'started', 'stopped', 'rejected']:
    continue
  release_list = decision_line.getAggregateValueList(portal_type="Software Release")
  if len(release_list) > 1:
    continue
  if not release_list[0]:
    continue
  # If the current sr in rejected we must prevent creation of new upgrade decision for this sr
  if simulation_state == 'rejected' and \
        release_list[0].getUrlString() != context.getUrlString():
    continue
    
  # If both software release belong to the same software product, there is an upgrade decision in progress 
  if product_reference == release_list[0].getAggregateReference():
    return upgrade_decision
