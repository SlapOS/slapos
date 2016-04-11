if context.getPortalObject().portal_workflow.isTransitionPossible(context, 'mark_busy') and context.getParentValue().isMemberOf('allocation_scope/open'):
  return 1
return 0
