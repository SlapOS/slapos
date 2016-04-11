"""Add selected product to the cart and continue"""
portal = context.getPortalObject()

# XXX context is a computer
if context.getPortalType() != "Computer":
  raise NotImplementedError, "Should be called on a Computer"

session = context.WebSection_getVifibSession()
portal.portal_selections.setSelectionParamsFor('vifib_session_id', {'computer_uid': context.getUid()})
# session['computer_uid'] = context.getUid()

web_section = context.getWebSectionValue()
return web_section.Base_redirect('install-a-software', keep_items={'editable_mode': 0})
