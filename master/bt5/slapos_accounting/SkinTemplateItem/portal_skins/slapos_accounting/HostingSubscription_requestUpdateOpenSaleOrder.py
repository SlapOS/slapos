from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

if context.getCausalityState() == 'diverged':

  person = context.getDestinationSectionValue(portal_type="Person")
  # Template document does not have person relation
  if person is not None:
    person.Person_storeOpenSaleOrderJournal()
    # Person_storeOpenSaleOrderJournal should fix all divergent Hosting Subscription in one run
    assert context.getCausalityState() == 'solved'
