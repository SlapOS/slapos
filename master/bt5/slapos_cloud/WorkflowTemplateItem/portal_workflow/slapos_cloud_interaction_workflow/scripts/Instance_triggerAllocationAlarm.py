software_instance = state_change['object']

portal = software_instance.getPortalObject()

if software_instance.getValidationState() == 'validated':
  context.Alarm_safeTrigger(portal.portal_alarms.slapos_allocate_instance)
