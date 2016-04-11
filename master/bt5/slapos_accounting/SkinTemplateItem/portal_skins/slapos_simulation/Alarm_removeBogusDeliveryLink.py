kw = {}
select_dict= {'delivery_uid': None}
kw.update(
  portal_type='Simulation Movement',
  select_dict=select_dict,
  left_join_list=select_dict.keys(),
  delivery_uid=None
)

context.getPortalObject().portal_catalog.searchAndActivate(
  method_id='SimulationMovement_removeBogusDeliveryLink',
  method_kw={'tag': tag},
  activate_kw={'tag': tag},
  **kw
)

# register activity on alarm object waiting for own tag in order to have only one alarm
# running in same time
context.activate(after_tag=tag).getId()
