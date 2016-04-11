portal = context.getPortalObject()


portal.portal_catalog.searchAndActivate(
  portal_type="Upgrade Decision Line", 
  simulation_state="confirmed",
  method_id = 'UpgradeDecisionLine_cancelDestroyed',
  activate_kw = {'tag':tag}
  )
  
context.activate(after_tag=tag).getId()
