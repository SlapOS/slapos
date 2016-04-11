select_kw = kwargs.copy()
select_kw.pop('portal_type', None)
select_kw.pop('delivery_relative_url_list', None)
from Products.ERP5Type.Document import newTempSimulationMovement
from Products.ZSQLCatalog.SQLCatalog import Query, NegatedQuery, ComplexQuery
portal = context.getPortalObject()

business_process_uid_list = [
  portal.business_process_module.slapos_consumption_business_process.getUid(),
  portal.business_process_module.slapos_subscription_business_process.getUid()]
specialise_reference_list = [q.getReference() for q in portal.portal_catalog(specialise_uid=business_process_uid_list,
  portal_type='Sale Trade Condition')]
select_dict= {'default_aggregate_portal_type': None}

select_kw.update(
  limit=50, # just take a bit
  portal_type='Sale Packing List Line',
  simulation_state='delivered',
  parent_specialise_reference=specialise_reference_list,
  parent_specialise_portal_type='Sale Trade Condition',
  select_dict=select_dict,
  left_join_list=select_dict.keys(),
  default_aggregate_portal_type=ComplexQuery(NegatedQuery(Query(default_aggregate_portal_type='Computer')),
    Query(default_aggregate_portal_type=None), operator="OR"),
  grouping_reference=None,
  sort_on=(('modification_date', 'ASC'),) # the highest chance to find movement which can be delivered
)
movement_list = portal.portal_catalog(**select_kw)

specialise = portal.portal_preferences.getPreferredAggregatedSaleTradeCondition()
temp_movement_list = []
id = 1
for movement in movement_list:
  if movement.getGroupingReference() is not None:
    continue
  temp_movement = newTempSimulationMovement(
    portal, movement.getRelativeUrl(),
    quantity=movement.getQuantity(),
    resource=movement.getResource(),
    source=movement.getDestination(),
    destination=movement.getDestination(),
    source_section=movement.getSourceSection(),
    destination_section=movement.getDestination(),
    destination_decision=movement.getDestination(),
    specialise=specialise,
    price_currency=movement.getPriceCurrency()
  )
  if movement.getResource() == 'service_module/slapos_instance_subscription':
    temp_movement.edit(price=0.83612040133800003)
  else:
    temp_movement.edit(price=0.0)
  temp_movement_list.append(temp_movement)
  id += 1

return temp_movement_list
