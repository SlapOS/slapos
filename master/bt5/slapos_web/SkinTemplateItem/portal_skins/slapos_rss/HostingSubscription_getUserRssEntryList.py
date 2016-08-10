"""
  Keep a custom script for permit render other times of documents, ie.: Software Installation.
"""

portal = context.getPortalObject()
kw['portal_type'] = ["Support Request", "Upgrade Decision"]
kw['source_project_uid'] = context.getUid()

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
if person:
  kw['default_destination_decision_uid'] = person.getUid()
  
  # Use event modification date instead. 
  kw['sort_on'] = [('modification_date', 'DESC'),]
  return context.getPortalObject().portal_catalog(**kw)

else:
  return []
