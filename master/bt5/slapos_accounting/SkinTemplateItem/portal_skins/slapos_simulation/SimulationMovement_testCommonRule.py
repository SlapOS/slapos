movement = context

business_link = movement.getCausalityValue(portal_type='Business Link')

rule_trade_phase_list = rule.getTradePhaseList()
if len(rule_trade_phase_list) > 0:
  # if rule defines trade phase check if there is sense to apply it
  if len(business_link.getParentValue().getBusinessLinkValueList(trade_phase=rule_trade_phase_list)) == 0:
    # If Business Process does not define trade phase do not apply
    return False

if movement.getSimulationState() in business_link.getCompletedStateList():
  return True

return False
