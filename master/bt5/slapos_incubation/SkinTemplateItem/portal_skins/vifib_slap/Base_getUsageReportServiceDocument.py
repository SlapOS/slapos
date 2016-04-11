# XXX: Convert to preference?
portal = context.getPortalObject()
usage_report_service_reference = 'usage_report'
catalog_result = portal.portal_catalog(
  portal_type=portal.getPortalServiceTypeList(),
  reference=usage_report_service_reference
)
if len(catalog_result) == 1:
  return catalog_result[0].getObject()
return None
