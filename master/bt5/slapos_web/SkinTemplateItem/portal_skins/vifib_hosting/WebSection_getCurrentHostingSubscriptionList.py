portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if person is not None:
  return portal.portal_catalog(
    portal_type="Hosting Subscription",
    default_destination_section_uid=person.getUid(),
    validation_state='validated',
    sort_on=(('title', ),)
    )
    
return []
