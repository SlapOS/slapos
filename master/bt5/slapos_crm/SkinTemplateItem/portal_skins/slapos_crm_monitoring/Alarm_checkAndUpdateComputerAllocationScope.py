portal = context.getPortalObject()

category_public = portal.restrictedTraverse("portal_categories/allocation_scope/open/public", None)
category_friend = portal.restrictedTraverse("portal_categories/allocation_scope/open/friend", None)

if category_public is not None:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer',
    default_allocation_scope_uid=[category_public.getUid(), category_friend.getUid()],
    validation_state="validated",
    method_id='Computer_checkAndUpdateAllocationScope',
    activate_kw={'tag': tag}
  )

context.activate(after_tag=tag).getId()
