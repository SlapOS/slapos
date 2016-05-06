"""
  Verify the consistency of the System Preference for the SlapOS Master to 
  ensure the site configuration is set. 
"""




if context.getPortalType() not in [ "System Preference"]:
  return []

if context.getPreferenceState() != "global":
  return []

portal = context.getPortalObject()

error_list = []

preference_method_list = [
  "getPreferredHateoasUrl",
  "getPreferredVifibFacebookApplicationId",
  "getPreferredVifibFacebookApplicationSecret",
  "getPreferredVifibGoogleApplicationId",
  "getPreferredVifibGoogleApplicationSecret",
  "getPreferredVifibRestApiLoginCheck"
  ]


for method_id in preference_method_list:

  result =  getattr(context.portal_preferences, method_id)()
  if result in [None, ""]:
    error_list.append(
      'The System Preference %s() should not return None or ""' % (method_id))

return error_list
