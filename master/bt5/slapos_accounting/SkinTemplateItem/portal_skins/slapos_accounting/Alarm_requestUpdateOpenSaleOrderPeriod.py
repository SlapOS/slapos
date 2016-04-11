portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Open Sale Order',
  validation_state='validated',
  children_portal_type='Open Sale Order Line',
  method_id='OpenSaleOrder_updatePeriod',
  activate_kw={'tag': tag},
  packet_size=1,
  activity_count=100
)
context.activate(after_tag=tag).getId()
