portal = context.getPortalObject()
kw['portal_type'] = ["Support Request", "Regularisation Request", "Upgrade Decision"]
support_in_progress_url = context.REQUEST.get('new_support_request', '')

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
if person:
  kw['default_destination_decision_uid'] = person.getUid()
  kw['simulation_state'] = "NOT cancelled"
  kw['sort_on'] = [('modification_date', 'DESC'),]

  if not support_in_progress_url:
    return portal.portal_catalog(**kw)

  support_in_progress = portal.restrictedTraverse(
                              support_in_progress_url, None)
  kw['uid'] = "NOT %s" % support_in_progress.getUid()

  support_request_list = portal.portal_catalog(**kw)

  if support_in_progress and \
            support_in_progress.getDestinationDecisionUid() == person.getUid():
    support_request_list = list(portal.portal_catalog(**kw))
    support_request_list.insert(0, support_in_progress)
  return support_request_list

else:
  return []
