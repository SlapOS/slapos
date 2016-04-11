slap_state = context.getSlapState()
portal = context.getPortalObject()
portal_preferences = portal.portal_preferences

if slap_state == 'free':
  computer = context.getParentValue()
  return computer.Computer_getSoftwareReleaseUrlStringList()

elif slap_state == 'busy':

  instance = portal.portal_catalog.getResultValue(
    portal_type="Software Instance",
    validation_state="validated",
    default_aggregate_uid=context.getUid(),
  )
  if (instance is None) or (instance.getSlapState() != "start_requested"):
    return []
  else:
    return [instance.getUrlString()]

else:
  return []
