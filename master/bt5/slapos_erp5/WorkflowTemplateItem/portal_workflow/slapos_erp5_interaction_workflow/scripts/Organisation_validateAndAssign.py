organisation = state_change["object"]
portal = context.getPortalObject()

if organisation.getValidationState() != "draft":
  return

if organisation.getRole() != "host":
  return

if organisation.getReference() in [None, ""]:
  reference = "SITE-%s" % portal.portal_ids.generateNewId(
    id_group='slap_organisation_reference',
    id_generator='uid')

  organisation.setReference(reference)

organisation.validate()

user_id = organisation.Base_getOwnerId()

person = context.getPortalObject().portal_catalog.getResultValue(user_id=user_id)

for assignment in person.objectValues(portal_type="Assignment"):
  if assignment.getSubordination() == organisation.getRelativeUrl():
    return

person.newContent(
  title="Assigment for Site %s" % organisation.getTitle(),
  portal_type="Assignment",
  destination_value=organisation).open()
