"""Add selected release to the cart and continue"""
portal = context.getPortalObject()

if len(uids) != 1:
  return context.Base_redirect(dialog_id,
                        keep_items={'portal_status_message':context.Base_translateString("Please select one software release.")})
else:
  session = context.WebSection_getVifibSession()
  params = portal.portal_selections.getSelectionParamsFor('vifib_session_id')
  params["instance_software_release_uid"] = uids[0]
  portal.portal_selections.setSelectionParamsFor('vifib_session_id', params)

if kw.has_key('came_from'):
  #we override the context to redirect the user to the next web section
  context = portal.restrictedTraverse(kw['came_from'])

software_release = portal.portal_catalog.getResultValue(uid=uids[0])
return software_release.Base_redirect('SoftwareRelease_viewRequestDialog')
# context.WebSection_viewNextStep()
