from DateTime import DateTime
portal = context.getPortalObject()
if context.getPortalType() != 'Sale Packing List':
  raise TypeError('Incorrect delivery.')
isTransitionPossible = portal.portal_workflow.isTransitionPossible
if context.getSimulationState() == 'started' \
  and len(context.checkConsistency()) == 0 \
  and context.getCausalityState() == 'solved' \
  and context.getSpecialise() == portal.portal_preferences.getPreferredAggregatedSaleTradeCondition():
  comment = 'Delivered by alarm as all actions in started state are ready.'
  if isTransitionPossible(context, 'stop'):
    context.stop(comment=comment)
  if isTransitionPossible(context, 'deliver'):
    context.deliver(comment=comment)
