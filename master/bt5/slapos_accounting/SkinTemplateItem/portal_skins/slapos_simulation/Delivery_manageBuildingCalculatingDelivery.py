from zExceptions import Unauthorized

if REQUEST is not None:
  raise Unauthorized

delivery = context
if delivery.getCausalityState() not in ('building', 'calculating'):
  return
path = delivery.getPath()
portal_activities = context.getPortalObject().portal_activities


if portal_activities.countMessage(method_id='Delivery_manageBuildingCalculatingDelivery', path=path) <= 1 \
  and portal_activities.countMessageWithTag('%s_solve' % path) == 0:
  delivery.serialize()
  delivery.updateCausalityState(solve_automatically=True)
  delivery.updateSimulation(expand_root=1, expand_related=1)
