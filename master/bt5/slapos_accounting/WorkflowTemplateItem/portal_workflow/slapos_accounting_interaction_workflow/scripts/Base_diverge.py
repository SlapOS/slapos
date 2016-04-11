document = state_change["object"]
if document.getPortalObject().portal_workflow.isTransitionPossible(document, 'diverge'):
  document.diverge()
