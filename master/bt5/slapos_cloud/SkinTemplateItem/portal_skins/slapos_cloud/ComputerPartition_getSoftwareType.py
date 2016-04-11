instance = context.getPortalObject().portal_catalog.getResultValue(
  portal_type="Software Instance",
  validation_state="validated",
  default_aggregate_uid=context.getUid(),
)
if (instance is None) or (instance.getSlapState() != "start_requested"):
  return ""
else:
  return instance.getSourceReference()
