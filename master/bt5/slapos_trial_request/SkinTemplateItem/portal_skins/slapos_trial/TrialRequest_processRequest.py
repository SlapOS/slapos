portal = context.getPortalObject()
person = portal.portal_catalog.getResultValue(
  portal_type="Person", 
  reference="free_trial_user")

if person is None: 
  return 

if context.getSpecialise() is not None:
  return

if context.getValidationState() == "validated":
  return 

state = "started"
shared = False

request_kw = {}
request_kw.update(
    software_release=context.getUrlString(),
    software_title=context.getTitle() + " %s" % str(context.getUid()),
    software_type="RootSoftwareInstance",
    instance_xml=context.getTextContent(),
    sla_xml="",
    shared=shared,
    state=state,
  )

person.requestSoftwareInstance(**request_kw)

requested_software_instance = context.REQUEST.get('request_instance')

if requested_software_instance is None: 
  return 

context.setAggregateValue(requested_software_instance)

context.setSpecialise(
  requested_software_instance.getSpecialise())

if context.getValidationState() == "draft":
  context.submit()

return
