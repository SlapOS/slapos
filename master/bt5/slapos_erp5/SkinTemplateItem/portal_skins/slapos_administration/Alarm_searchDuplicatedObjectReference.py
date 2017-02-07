active_process = context.newActiveProcess().getRelativeUrl()



context.getPortalObject().portal_catalog.searchAndActivate(
      method_id='Base_checkDuplicatedReference',
      method_kw=dict(fixit=fixit, active_process=active_process),
      activate_kw=dict(tag=tag, priority=5),
      portal_type=["Hosting Subscription", "Computer", "Software Instance", "Slave Instance", "Software Installation"], 
      validation_state="validated")

return
