portal = context.getPortalObject()
from Products.ZSQLCatalog.SQLCatalog import SimpleQuery, NegatedQuery

# XXX TODO: use getInventory to directly fetch user with a wrong balance
portal.portal_catalog.searchAndActivate(
      portal_type="Person", 
      validation_state="validated",
      reference=NegatedQuery(SimpleQuery(reference=None)),
      default_email_text=NegatedQuery(SimpleQuery(default_email_text=None)),
      method_id='Person_checkToCreateRegularisationRequest',
      activate_kw={'tag': tag}
      )
context.activate(after_tag=tag).getId()
