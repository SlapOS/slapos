movement = context

if not movement.SimulationMovement_testCommonRule(rule):
  return False

parent = movement.getParentValue()
if parent.getPortalType() != 'Applied Rule':
  return False

parent_rule = parent.getSpecialiseValue()
if parent_rule.getPortalType() not in ('Invoice Root Simulation Rule',
                                       'Invoice Simulation Rule'):
  return False

return True
