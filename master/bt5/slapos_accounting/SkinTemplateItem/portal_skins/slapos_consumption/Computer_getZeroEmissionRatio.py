if REQUEST is not None:
  raise Unauthorized("Unauthorized call script from URL")

portal = context.getPortalObject()

resource_uid = context.service_module.zero_emission_ratio.getUid()

packing_list_line_list = portal.portal_catalog(
  limit=1,
  sort_on=("creation_date", "DESC"),
  portal_type="Sale Packing List Line",
  default_resource_uid = resource_uid,
  default_aggregate_uid=context.getUid())

if len(packing_list_line_list):
  quantity = packing_list_line_list[0].getQuantity()
  if quantity > 0:
    return quantity

return 0.0
