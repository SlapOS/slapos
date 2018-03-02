portal_oauth = context.portal_oauth
error_list = []


for connector in portal_oauth.searchFolder(portal_type="Google Connector"):
  if connector.getReference() == "default":
    return []

if fixit:
  system_preference = context.portal_preferences.getActiveSystemPreference()
  connector = portal_oauth.newContent(
    portal_type="Google Connector",
    reference="default",
    client_id=getattr(system_preference, "preferred_vifib_google_application_id", None),
    secret_key=getattr(system_preference, "preferred_vifib_google_application_secret", None)
  )
  connector.validate()
  return []

return ["Default Google Connector is missing."]
