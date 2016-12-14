from DateTime import DateTime
portal = context.getPortalObject()
person = portal.portal_catalog.getResultValue(
  portal_type="Person", 
  reference="free_trial_user")


if context.getStopDate() >= DateTime():
  return

if person is None: 
  return 

if context.getSpecialise() is None:
  return

if context.getValidationState() != "validated":
  return 

state = "destroyed"
shared = False

request_kw = {}
request_kw.update(
    software_release=context.getUrlString(),
    software_title=context.getTitle(),
    software_type="RootSoftwareInstance",
    instance_xml=context.getTextContent(),
    sla_xml="",
    shared=shared,
    state=state,
  )

person.requestSoftwareInstance(**request_kw)

context.invalidate()

return
