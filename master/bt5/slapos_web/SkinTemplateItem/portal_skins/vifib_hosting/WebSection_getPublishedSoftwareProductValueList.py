person = context.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  return []

kw["portal_type"] = "Software Product"
kw["validation_state"] = "published"

return context.portal_catalog(**kw)
