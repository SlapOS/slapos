# HARDCODED LIMIT TO BE MOVED TO GLOBAL PREFERENCES
limit = 5

portal = context.getPortalObject()

kw['limit'] = limit
kw['portal_type'] = 'Support Request'
kw['simulation_state'] = ["validated","submitted"]
kw['default_resource_uid'] = portal.service_module.slapos_crm_monitoring.getUid()
if destination_decision:
  kw['default_destination_decision_uid'] = context.restrictedTraverse(
                          destination_decision).getUid()

support_request_list = context.portal_catalog(**kw)

return len(support_request_list) >= limit
