"""
  Get a related Upgrade Decision 
"""
if simulation_state not in ["confirmed", "started", "stopped"]:
  raise ValueError(
    "You shouldn't request for this state: %s" % simulation_state)


decision_line_list = context.getAggregateValueList(
                        portal_type="Upgrade Decision Line", 
                        simulation_state=simulation_state)

if len(decision_line_list) > 1:
  raise ValueError("Your have more them one valid decison line!")
 
if len(decision_line_list) == 0:
  return None

return decision_line_list[0].getParentValue()
