portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Upgrade Decision',
  simulation_state='stopped',
  method_id='UpgradeDecision_notifyDelivered',
  activate_kw={'tag': tag }
)

context.activate(after_tag=tag).getId()
