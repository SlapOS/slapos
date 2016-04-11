from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

ticket = context
state = ticket.getSimulationState()
person = ticket.getSourceProjectValue(portal_type="Person")
if (state == 'suspended') and \
   (person is not None) and \
   (ticket.getResource() == 'service_module/slapos_crm_delete_acknowledgement'):
   
  portal = context.getPortalObject()
  portal.portal_catalog.searchAndActivate(
    portal_type="Hosting Subscription",
    validation_state=["validated"],
    default_destination_section_uid=person.getUid(),
    method_id='HostingSubscription_deleteFromRegularisationRequest',
    method_args=(person.getRelativeUrl(),),
    activate_kw={'tag': tag}
  )
  return True
return False
