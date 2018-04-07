portal = context.getPortalObject()

for cr in portal.portal_catalog(reference=["testSlapOSJSSubscribeUser", "demo_functional_user"],
                               portal_type="Credential Request"):
  related_person = cr.getDestinationDecisionValue()
  portal.person_module.manage_delObjects(ids=[related_person.getId()])
  event_list = cr.getFollowUpRelatedValueList()
  if len(event_list):
    portal.event_module.manage_delObjects(ids=[e.getId() for e in event_list])
  portal.credential_request_module.manage_delObjects(ids=[cr.getId()])

return "Done."
