portal = context.getPortalObject()
kw['portal_type'] = ["Support Request", "Regularisation Request", "Upgrade Decision"]

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
if person:
  kw['default_destination_decision_uid'] = person.getUid()
  kw['simulation_state'] = "NOT cancelled"
  kw['sort_on'] = (('modification_date', 'DESC'),)
  kw['limit'] = 50

  return portal.portal_catalog(**kw)

else:
  return []
