project = state_change["object"]
from DateTime import DateTime

portal = context.getPortalObject()

if project.getValidationState() != "draft":
  return

if project.getReference() in [None, ""]:
  reference = "PROJ-%s" % portal.portal_ids.generateNewId(
    id_group='slap_project_reference',
    id_generator='uid', default=1)
  project.setReference(reference)

project.setStartDate(DateTime())
project.validate()

user_id = project.Base_getOwnerId()

person = portal.portal_catalog.getResultValue(user_id=user_id)

for assignment in person.objectValues(portal_type="Assignment"):
  if assignment.getDestinationProject() == project.getRelativeUrl():
    return

person.newContent(
  title="Assigment for Project %s" % project.getTitle(),
  portal_type="Assignment",
  destination_project_value=project).open()
