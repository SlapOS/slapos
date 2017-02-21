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

hosting_subscription = context.getSpecialiseValue()

request_kw = {}
request_kw.update(
    software_release=hosting_subscription.getUrlString(),
    software_title=hosting_subscription.getTitle(),
    software_type=hosting_subscription.getSourceReference(),
    instance_xml=hosting_subscription.getTextContent(),
    sla_xml="",
    shared=hosting_subscription.getRootSlave(),
    state=state,
  )

person.requestSoftwareInstance(**request_kw)


connection_dict = hosting_subscription.getPredecessorValue().getConnectionXmlAsDict()

connection_key_list = context.getSubjectList()
connection_string = '\n'.join(['%s: %s' % (x,y) for x,y in connection_dict.items() if x in connection_key_list])

mapping_dict = {"token": connection_string }


context.TrialRequest_sendMailMessage(person,
    context.getDefaultEmailText(),
   'slapos-free.trial.destroy', 
   mapping_dict)

context.invalidate()
