portal = context.getPortalObject()

public_scope_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/public", None).getUid()
friend_scope_uid =  portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/friend", None).getUid()

if public_scope_uid and friend_scope_uid:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer',
    validation_state = 'validated',
    default_allocation_scope_uid=[public_scope_uid, friend_scope_uid],
    method_id = 'Computer_checkAndCreateUpgradeDecision',
    activate_kw = {'tag':tag}
  )
  
  context.activate(after_tag=tag).getId()
