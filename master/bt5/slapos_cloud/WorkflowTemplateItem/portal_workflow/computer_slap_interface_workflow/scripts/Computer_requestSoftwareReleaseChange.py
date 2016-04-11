computer = state_change['object']
portal = computer.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  software_release_url = kwargs['software_release_url']
  state = kwargs["state"]
except KeyError:
  raise TypeError("Computer_requestSoftwareReleaseChange takes exactly 2 arguments")

tag = "%s_%s_inProgress" % (computer.getUid(), 
                               software_release_url)

if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The software instance is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  raise NotImplementedError(tag)

software_installation_portal_type = 'Software Installation'
# Check if it already exists
software_installation_list = portal.portal_catalog(
  portal_type=software_installation_portal_type,
  url_string={'query': software_release_url, 'key': 'ExactMatch'},
  validation_state="validated",
  default_aggregate_uid=computer.getUid(),
  limit=2,
  )

if len(software_installation_list) > 1:
  raise NotImplementedError("Too many Software Installation %s found %s" % (software_release_url, [x.path for x in software_installation_list]))
elif len(software_installation_list) == 1:
  software_installation = software_installation_list[0].getObject()
  if (software_installation.getUrlString() != software_release_url) or \
     (software_installation.getValidationState() != "validated") or \
     (software_installation.getAggregate() != computer.getRelativeUrl()):
    raise NotImplementedError("The system was not able to get the expected Software Installation")
else:
  if (state == "destroyed"):
    # No need to create destroyed subscription.
    return
  software_installation_reference = "SOFTINSTALL-%s" % context.getPortalObject().portal_ids\
      .generateNewId(id_group='slap_software_installation_reference', id_generator='uid')
  software_installation = portal.getDefaultModule(portal_type=software_installation_portal_type).newContent(
    portal_type=software_installation_portal_type,
    reference=software_installation_reference,
    url_string=software_release_url,
    aggregate=computer.getRelativeUrl(),
    activate_kw={'tag': tag},
    destination_section=computer.getSourceAdministration()
  )

# Change desired state
if (state == "available"):
  software_installation.requestStart()
elif (state == "destroyed"):
  software_installation.requestDestroy(activate_kw={'tag': tag})
else:
  raise ValueError("state should be available or destroyed, but is %s" % state)

# Change the state at the end to allow to execute updateLocalRoles only once in the transaction
validation_state = software_installation.getValidationState()
slap_state = software_installation.getSlapState()
if validation_state == 'draft':
  portal.portal_workflow.doActionFor(software_installation,
                                           'validate_action')

context.REQUEST.set('software_installation_url', software_installation.getRelativeUrl())
