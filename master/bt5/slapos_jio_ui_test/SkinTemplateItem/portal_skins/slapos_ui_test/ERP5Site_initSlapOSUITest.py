# PreferenceTool

portal = context.getPortalObject()
preference = portal.portal_preferences.getActiveSystemPreference()

preference.edit(
  preferred_credential_alarm_automatic_call=1,
  preferred_credential_recovery_automatic_approval=1,
  preferred_credential_request_automatic_approval=1
)

return "Done."
