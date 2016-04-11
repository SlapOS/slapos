"""Add selected product to the cart and continue"""
portal = context.getPortalObject()

session = context.WebSection_getVifibSession()
params = portal.portal_selections.getSelectionParamsFor('vifib_session_id')

##Get item list
item_list = []
if uids:
  item_list = [item.getObject() for item in portal.portal_catalog(uid=uids, portal_type="Software Release")]

if len(item_list) != 1:
  return context.Base_redirect(dialog_id,
                        keep_items={'portal_status_message':context.Base_translateString("Please select one software release.")})

item = item_list[0]
# XXX Check that release is associate to product

computer = portal.portal_catalog.getResultValue(
  uid=params['computer_uid'],
  portal_type="Computer",
)

computer.requestSoftwareRelease(software_release_url=item.getUrlString(), state='available')

return context.restrictedTraverse(context.REQUEST.get('software_installation_url')).Base_redirect(form_id='view', keep_items={'portal_status_message': 'Requested installation'})
