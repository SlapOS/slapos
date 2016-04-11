from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
portal = context.getPortalObject()

computer = context

return portal.portal_catalog.countResults(
  portal_type='Computer Partition',
  parent_uid=computer.getUid(),
  free_for_request=0,
  software_release_url=portal.portal_catalog.getResultValue(uid=software_release_uid).getUrlString()
)[0][0]
