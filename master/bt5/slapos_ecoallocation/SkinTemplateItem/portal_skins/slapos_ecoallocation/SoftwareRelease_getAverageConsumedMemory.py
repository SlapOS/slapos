portal = context.getPortalObject()

software_release_url = context.getUrlString()

resource_uid = context.service_module.memory_used.getUid()

# Select all software instances from a certain Software Release
software_instance_list = portal.portal_catalog(
  portal_type="Software Instance",
  limit=100,
  url_string=software_release_url)

packing_list_line_list = portal.portal_catalog(
  limit=100,
  sort_on=("creation_date", "DESC"),
  portal_type="Sale Packing List Line",
  default_resource_uid = resource_uid,
  default_aggregate_uid=[i.getUid() for i in software_instance_list]
  )

if len(packing_list_line_list):
  return sum([i.getQuantity() for i in packing_list_line_list])/len(packing_list_line_list)

return 0.0
