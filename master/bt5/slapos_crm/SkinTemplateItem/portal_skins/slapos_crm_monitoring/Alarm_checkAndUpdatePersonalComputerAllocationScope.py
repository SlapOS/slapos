portal = context.getPortalObject()

category_personal = portal.restrictedTraverse("portal_categories/allocation_scope/open/personal", None)

if category_personal is not None:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer', 
    validation_state='validated', 
    modification_date=(DateTime() - 30).strftime('<=%Y/%m/%d'), 
    default_allocation_scope_uid=category_personal.getUid(), 
    left_join_list=['aggregate_related_uid'], 
    aggregate_related_uid=None,
    method_id='Computer_checkAndUpdatePersonalAllocationScope',
    activate_kw={'tag': tag})

context.activate(after_tag=tag).getId()
