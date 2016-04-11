return context.getPortalObject().portal_catalog(
  local_roles=["Assignee"],
  default_strict_allocation_scope_uid="!=%s" % context.getPortalObject().portal_categories.allocation_scope.close.forever.getUid(),
  **kw
  )
