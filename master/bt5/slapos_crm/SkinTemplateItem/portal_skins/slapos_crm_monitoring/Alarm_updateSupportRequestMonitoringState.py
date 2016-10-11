portal = context.getPortalObject()


default_resource_uid = portal.restrictedTraverse("service_module/slapos_crm_monitoring", None).getUid()

portal.portal_catalog.searchAndActivate(
    portal_type='Support Request',
    simulation_state='validated',
    default_resource_uid=default_resource_uid,
    method_id='SupportRequest_updateMonitoringState',
    activate_kw = {'tag':tag}
  )

context.activate(after_tag=tag).getId()
