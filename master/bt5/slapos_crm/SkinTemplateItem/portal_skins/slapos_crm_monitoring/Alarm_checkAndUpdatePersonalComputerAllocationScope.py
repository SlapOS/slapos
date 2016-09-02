portal = context.getPortalObject()

category_personal = portal.restrictedTraverse("portal_categories/allocation_scope/open/personal", None)

if category_personal is not None:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer',
    validation_state='validated',
    default_allocation_scope_uid=category_personal.getUid(),
    method_id='Computer_checkAndUpdatePersonalAllocationScope',
    activate_kw={'tag': tag})

context.activate(after_tag=tag).getId()
