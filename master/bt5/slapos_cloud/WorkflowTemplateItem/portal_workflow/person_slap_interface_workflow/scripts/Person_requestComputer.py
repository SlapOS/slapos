person = state_change['object']
portal = person.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  computer_title = kwargs['computer_title']
except KeyError:
  raise TypeError, "Person_requestComputer takes exactly 1 argument"

tag = "%s_%s_computerInProgress" % (person.getUid(), 
                               computer_title)
if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The software instance is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  raise NotImplementedError(tag)

computer_portal_type = "Computer"
computer_list = portal.portal_catalog.portal_catalog(portal_type=computer_portal_type, title=computer_title, limit=2)

if len(computer_list) == 2:
  raise NotImplementedError
elif len(computer_list) == 1:
  computer = computer_list[0]
else:
  computer = None

if computer is None:
  reference = "COMP-%s" % portal.portal_ids.generateNewId(
    id_group='slap_computer_reference',
    id_generator='uid')
  module = portal.getDefaultModule(portal_type=computer_portal_type)
  computer = module.newContent(
    portal_type=computer_portal_type,
    title=computer_title,
    reference=reference,
    capacity_scope='open',
    activate_kw={'tag': tag}
  )
  computer.requestComputerRegistration()
  computer.approveComputerRegistration()


computer = context.restrictedTraverse(computer.getRelativeUrl())

context.REQUEST.set("computer", computer.getRelativeUrl())
context.REQUEST.set("computer_url", computer.absolute_url())
context.REQUEST.set("computer_reference", computer.getReference())
