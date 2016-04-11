portal = context.getPortalObject()
if context.getPortalType() != 'Sale Invoice Transaction':
  raise TypeError('Incorrect delivery.')
isTransitionPossible = portal.portal_workflow.isTransitionPossible
if context.getSimulationState() == 'confirmed'\
  and len(context.checkConsistency()) == 0\
  and context.getCausalityState() == 'solved'\
  and context.getSpecialise() == portal.portal_preferences.getPreferredAggregatedSaleTradeCondition():
  comment = 'Stopped by alarm as all actions in confirmed state are ready.'
  if isTransitionPossible(context, 'start'):
    context.start(comment=comment)
  if isTransitionPossible(context, 'stop'):
    context.stop(comment=comment)
