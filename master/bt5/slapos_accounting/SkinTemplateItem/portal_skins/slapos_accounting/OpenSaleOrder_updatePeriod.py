from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

if context.getValidationState() == 'validated':
  person = context.getDestinationDecisionValue(portal_type="Person")
  if person is not None:
    person.Person_storeOpenSaleOrderJournal()
