portal = context.getPortalObject()
from Products.ZSQLCatalog.SQLCatalog import SimpleQuery

portal.portal_catalog.searchAndActivate(
  portal_type=["Software Instance", "Slave Instance"],
  validation_state="validated",
  specialise_validation_state="validated",
  predecessor_related_uid=SimpleQuery(predecessor_related_uid=None, comparison_operator='is'),
  method_id='SoftwareInstance_tryToGarbageUnlinkedInstance',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
