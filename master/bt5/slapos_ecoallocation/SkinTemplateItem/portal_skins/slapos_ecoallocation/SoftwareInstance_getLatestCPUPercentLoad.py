portal = context.getPortalObject()

packing_list_line = portal.portal_catalog.getResultValue(
  sort_on=("creation_date", "DESC"),
  portal_type="Sale Packing List Line",
  default_resource_uid = context.service_module.cpu_load_percent.getUid(),
  default_aggregate_uid=context.getUid())

if packing_list_line is not None:
  return packing_list_line.getQuantity()

return 0.0
