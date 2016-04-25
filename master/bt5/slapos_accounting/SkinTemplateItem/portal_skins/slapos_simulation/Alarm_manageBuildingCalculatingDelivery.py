portal = context.getPortalObject()
activate_kw = {
  'tag': tag
}
portal.portal_catalog.searchAndActivate(
  portal_type=portal.getPortalDeliveryTypeList(),
  causality_state=('building', 'calculating'),
  activate_kw=activate_kw,
  packet_size=30,
  method_id='Delivery_manageBuildingCalculatingDelivery'
)
context.activate(after_tag=tag).getId()
