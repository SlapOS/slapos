active_process = context.newActiveProcess().getRelativeUrl()

context.getPortalObject().portal_catalog.searchAndActivate(
      method_id='HostingSubscription_checkDuplicatedInstance',
      method_kw=dict(fixit=fixit, active_process=active_process),
      activate_kw=dict(tag=tag, priority=5),
      portal_type="Hosting Subscription", 
      validation_state="validated")
