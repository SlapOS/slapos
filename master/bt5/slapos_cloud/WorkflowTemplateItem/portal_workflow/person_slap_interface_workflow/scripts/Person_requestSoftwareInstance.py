person = state_change['object']
portal = person.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  software_release_url_string = kwargs['software_release']
  software_title = kwargs["software_title"]
  software_type = kwargs["software_type"]
  instance_xml = kwargs["instance_xml"]
  sla_xml = kwargs["sla_xml"]
  is_slave = kwargs["shared"]
  root_state = kwargs["state"]
except KeyError:
  raise TypeError, "Person_requestSoftwareInstance takes exactly 7 arguments"

if is_slave not in [True, False]:
  raise ValueError, "shared should be a boolean"

empty_parameter = """<?xml version="1.0" encoding="utf-8"?>
<instance>
</instance>"""
empty_parameter2 = """<?xml version='1.0' encoding='utf-8'?>
<instance/>"""


# XXX Hardcode default parameter
if (instance_xml == empty_parameter) or (instance_xml.startswith(empty_parameter2)):
  if software_release_url_string == "http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/heads/erp5-frontend:/software/erp5/software.cfg":  
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
<instance>
<parameter id="frontend-instance-guid">SOFTINST-9238</parameter>
<parameter id="frontend-software-url">http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg</parameter>
</instance>
"""

hosting_subscription_portal_type = "Hosting Subscription"

tag = "%s_%s_inProgress" % (person.getUid(), 
                               software_title)

if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The software instance is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  raise NotImplementedError(tag)

# Check if it already exists
request_hosting_subscription_list = portal.portal_catalog(
  portal_type=hosting_subscription_portal_type,
  title={'query': software_title, 'key': 'ExactMatch'},
  validation_state="validated",
  default_destination_section_uid=person.getUid(),
  limit=2,
  )
if len(request_hosting_subscription_list) > 1:
  raise NotImplementedError, "Too many hosting subscription %s found %s" % (software_title, [x.path for x in request_hosting_subscription_list])
elif len(request_hosting_subscription_list) == 1:
  request_hosting_subscription = request_hosting_subscription_list[0].getObject()
  if (request_hosting_subscription.getSlapState() == "destroy_requested") or \
     (request_hosting_subscription.getTitle() != software_title) or \
     (request_hosting_subscription.getValidationState() != "validated") or \
     (request_hosting_subscription.getDestinationSection() != person.getRelativeUrl()):
    raise NotImplementedError, "The system was not able to get the expected hosting subscription"
else:
  if (root_state == "destroyed"):
    # No need to create destroyed subscription.
    context.REQUEST.set('request_hosting_subscription', None)
    return
  hosting_subscription_reference = "HOSTSUBS-%s" % context.getPortalObject().portal_ids\
      .generateNewId(id_group='slap_hosting_subscription_reference', id_generator='uid')
  request_hosting_subscription = portal.getDefaultModule(portal_type=hosting_subscription_portal_type).newContent(
    portal_type=hosting_subscription_portal_type,
    reference=hosting_subscription_reference,
    title=software_title,
    destination_section=person.getRelativeUrl(),
    activate_kw={'tag': tag},
  )

promise_kw = {
  'instance_xml': instance_xml,
  'software_type': software_type,
  'sla_xml': sla_xml,
  'software_release': software_release_url_string,
  'shared': is_slave,
}

context.REQUEST.set('request_hosting_subscription', request_hosting_subscription)
# Change desired state
if (root_state == "started"):
  request_hosting_subscription.requestStart(**promise_kw)
elif (root_state == "stopped"):
  request_hosting_subscription.requestStop(**promise_kw)
elif (root_state == "destroyed"):
  request_hosting_subscription.requestDestroy(**promise_kw)
  context.REQUEST.set('request_hosting_subscription', None)
else:
  raise ValueError, "state should be started, stopped or destroyed"

request_hosting_subscription.requestInstance(
  software_release=software_release_url_string,
  software_title=software_title,
  software_type=software_type,
  instance_xml=instance_xml,
  sla_xml=sla_xml,
  shared=is_slave,
  state=root_state,
)

# Change the state at the end to allow to execute updateLocalRoles only once in the transaction
validation_state = request_hosting_subscription.getValidationState()
slap_state = request_hosting_subscription.getSlapState()
if validation_state == 'draft':
  request_hosting_subscription.portal_workflow.doActionFor(request_hosting_subscription,
                                           'validate_action')
if (validation_state != 'archived') and \
   (slap_state == 'destroy_requested'):
  # XXX TODO do not use validation workflow to filter destroyed subscription
  request_hosting_subscription.archive()
