portal_oauth = context.portal_oauth
error_list = []


for connector in portal_oauth.searchFolder(portal_type="Facebook Connector"):
  if connector.gerReference() == "default":
    return []

if fixit:
  system_preference = context.portal_preferences.getActiveSystemPreference()
  connector = portal_oauth.newContent(
    portal_type="Facebook Connector",
    reference="default",
    client_id=getattr(system_preference, "preferred_vifib_facebook_application_id", None),
    secret_key=getattr(system_preference, "preferred_vifib_facebook_application_secret", None)
  )
  connector.validate()
  return []

return ["Default Facebook Connector is missing."]
