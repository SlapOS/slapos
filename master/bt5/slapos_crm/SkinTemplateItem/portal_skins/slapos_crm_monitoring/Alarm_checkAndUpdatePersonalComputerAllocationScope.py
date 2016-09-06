from DateTime import DateTime
# from Products.ERP5Type.DateUtils import addToDate
# from Products.ZSQLCatalog.SQLCatalog import Query

portal = context.getPortalObject()

category_personal = portal.restrictedTraverse("portal_categories/allocation_scope/open/personal", None)

if category_personal is not None:
  portal.portal_catalog.searchAndActivate(
    portal_type='Computer',
    validation_state='validated',
    # XXX - creation_date is not indexed for computer
    # creation_date=Query(range="max", creation_date=addToDate(DateTime(), {'day': -30})),
    default_allocation_scope_uid=category_personal.getUid(),
    method_id='Computer_checkAndUpdatePersonalAllocationScope',
    activate_kw={'tag': tag})

context.activate(after_tag=tag).getId()
