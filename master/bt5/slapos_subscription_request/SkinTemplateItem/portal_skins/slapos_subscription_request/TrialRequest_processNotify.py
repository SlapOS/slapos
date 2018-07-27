from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
portal = context.getPortalObject()

person = portal.portal_catalog.getResultValue(
  portal_type="Person", 
  reference="free_trial_user")

if person is None:
  return "Free Trial Person not Found"

connection_key_list = context.getSubjectList()
instance = context.getAggregateValue()

if context.getValidationState() in ["validated", "invalidated"]:
  return

if instance.getSlapState() != "destroy_requested":
  connection_dict = instance.getConnectionXmlAsDict()
  if connection_dict:

    if len([ x for x, y in connection_dict.items() if x in connection_key_list]) != len(connection_key_list):
      return "Not ready %s != %s" % ([ x for x, y in connection_dict.items() if x in connection_key_list], connection_key_list)
 
    for x, y in connection_dict.items():
      if x in connection_key_list and y in ['None', None, 'http://', '']:
        return "key %s has invalid value %s" % (x, y)

    connection_string = '\n'.join(
      ['%s: %s' % (x,y) for x,y in connection_dict.items() if x in connection_key_list])

    mapping_dict = {"token": connection_string }

    context.TrialRequest_sendMailMessage(person,
      context.getDefaultEmailText(),
     'slapos-free.trial.token', 
      mapping_dict)

    context.validate()
