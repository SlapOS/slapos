portal = context.getPortalObject()
public_category_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/public", None).getUid()

friend_category_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/friend", None).getUid()


if None not in [friend_category_uid, public_category_uid]:
  portal.portal_catalog.searchAndActivate(
    portal_type = 'Computer',
    validation_state = 'validated',
    default_allocation_scope_uid = [public_category_uid, friend_category_uid],
    method_id = 'Computer_checkState',
    activate_kw = {'tag':tag}  
  )

context.activate(after_tag=tag).getId()
