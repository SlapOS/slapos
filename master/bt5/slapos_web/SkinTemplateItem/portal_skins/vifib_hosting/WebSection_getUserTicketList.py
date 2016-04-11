portal = context.getPortalObject()
kw['portal_type'] = ["Support Request", "Regularisation Request", "Upgrade Decision"]
support_in_progress_url = context.REQUEST.get('new_support_request', '')

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
if person:
  kw['default_destination_decision_uid'] = person.getUid()
  kw['sort_on'] = [('modification_date', 'DESC'),]
  found = False
  support_request_list = []
  for support_request in context.getPortalObject().portal_catalog(**kw):
    if support_in_progress_url and \
          support_request.getRelativeUrl() == support_in_progress_url:
      found = True
    support_request_list.append(support_request.getObject())
  if support_in_progress_url and not found:
    support_in_progress = portal.restrictedTraverse(
                              support_in_progress_url, None)
    if support_in_progress and support_in_progress.getDestinationDecisionUid() == person.getUid():
      support_request_list.insert(0, support_in_progress)
  return support_request_list

else:
  return []
