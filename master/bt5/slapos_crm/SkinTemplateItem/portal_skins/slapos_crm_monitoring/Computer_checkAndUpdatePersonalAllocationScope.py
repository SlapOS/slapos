if context.Computer_hasContactedRecently():
  return

return context.Computer_checkAndUpdateAllocationScope(
  target_allocation_scope = 'close/outdated',
  notification_message_reference='slapos-crm-computer-allocation-scope-closed.notification',
  check_service_provider=False,
  force=True)
