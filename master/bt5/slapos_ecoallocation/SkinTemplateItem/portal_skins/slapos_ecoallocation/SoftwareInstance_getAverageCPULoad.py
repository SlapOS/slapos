portal = context.getPortalObject()

software_release_url = context.getUrlString()

resource_uid = context.service_module.cpu_load_percent.getUid()

# Select all software instances from a certain Software Release
packing_list_line_list = portal.portal_catalog(
  limit=20,
  sort_on=("creation_date", "DESC"),
  portal_type="Sale Packing List Line",
  default_resource_uid = resource_uid,
  default_aggregate_uid=[context.getUid()]
  )

if len(packing_list_line_list):
  # Remove the /8 and update the value on the clients.
  return sum([i.getQuantity() for i in packing_list_line_list])/len(packing_list_line_list)

return 0.0
