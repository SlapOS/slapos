portal = context.getPortalObject()
from Products.ZSQLCatalog.SQLCatalog import SimpleQuery, NegatedQuery

portal.portal_catalog.searchAndActivate(
  portal_type='Hosting Subscription',
  validation_state='validated',
  where_expression="related_predecessor_title_1_catalog.title <> catalog.title",
  predecessor_title=NegatedQuery(SimpleQuery(predecessor_title=None, comparison_operator='is')),
  method_id='HostingSubscription_assertPredecessor',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
