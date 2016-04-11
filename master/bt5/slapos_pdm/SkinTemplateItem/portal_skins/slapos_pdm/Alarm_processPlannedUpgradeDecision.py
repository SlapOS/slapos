portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Upgrade Decision',
  simulation_state='planned',
  method_id='UpgradeDecision_notify',
  activate_kw={'tag': tag }
)

context.activate(after_tag=tag).getId()
