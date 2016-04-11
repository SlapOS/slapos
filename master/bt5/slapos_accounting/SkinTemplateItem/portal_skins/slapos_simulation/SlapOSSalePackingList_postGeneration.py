if related_simulation_movement_path_list is None:
  raise RuntimeError, 'related_simulation_movement_path_list is missing. Update ERP5 Product.'

packing_list = context

try:
  packing_list.PackingList_copyOrderProperties()
except AttributeError:
  # does not come from Order
  pass

portal = packing_list.getPortalObject()
comment = context.Base_translateString('Automatic transition during build.')
if portal.portal_workflow.isTransitionPossible(context, 'confirm'):
  context.confirm(comment=comment)
if portal.portal_workflow.isTransitionPossible(context, 'start'):
  context.start(comment=comment)
  context.stop(comment=comment)
  context.deliver(comment=comment)

# Initialise causality workflow
packing_list.startBuilding()
