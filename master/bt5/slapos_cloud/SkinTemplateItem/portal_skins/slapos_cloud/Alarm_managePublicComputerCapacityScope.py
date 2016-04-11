portal = context.getPortalObject()

category = portal.restrictedTraverse("portal_categories/allocation_scope/open/public", None)
if category is not None:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer',
    default_allocation_scope_uid=category.getUid(),
    validation_state="validated",
    method_id='Computer_checkAndUpdateCapacityScope',
    activate_kw={'tag': tag}
  )
context.activate(after_tag=tag).getId()
