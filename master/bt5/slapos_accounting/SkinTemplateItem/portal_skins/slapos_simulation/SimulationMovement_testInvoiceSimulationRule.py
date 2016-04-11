movement = context

if not movement.SimulationMovement_testCommonRule(rule):
  return False

source_section = movement.getSourceSection()
destination_section = movement.getDestinationSection()
if source_section == destination_section or source_section is None \
    or destination_section is None:
  return False

return True
