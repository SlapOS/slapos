instance = state_change['object']
portal = instance.getPortalObject()
software_title = state_change.kwargs['new_name']

assert instance.getPortalType() in ["Slave Instance", "Software Instance"]

hosting_subscription = instance.getSpecialiseValue(portal_type="Hosting Subscription")

# Instance can be moved from one requester to another
# Prevent creating two instances with the same title
tag = "%s_%s_inProgress" % (hosting_subscription.getUid(), software_title)
if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The software instance is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  raise NotImplementedError(tag)

# Check if it already exists
request_software_instance_list = portal.portal_catalog(
  # Fetch all portal type, as it is not allowed to change it
  portal_type=["Software Instance", "Slave Instance"],
  title={'query': software_title, 'key': 'ExactMatch'},
  specialise_uid=hosting_subscription.getUid(),
  # Do not fetch destroyed instances
  # XXX slap_state=["start_requested", "stop_requested"],
  validation_state="validated",
  limit=1,
)
if len(request_software_instance_list) == 1:
  raise ValueError, "Too many instances '%s' found: %s" % (software_title, [x.path for x in request_software_instance_list])

# Change the title
instance.edit(title=software_title, activate_kw={'tag': tag})
