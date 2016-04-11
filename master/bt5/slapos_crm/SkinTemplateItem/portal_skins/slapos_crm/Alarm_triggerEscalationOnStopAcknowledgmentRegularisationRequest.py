portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
      portal_type="Regularisation Request", 
      simulation_state=["suspended"],
      default_resource_uid=portal.service_module.slapos_crm_stop_acknowledgement.getUid(),
      method_id='RegularisationRequest_triggerStopAcknowledgmentEscalation',
      activate_kw={'tag': tag}
      )
context.activate(after_tag=tag).getId()
