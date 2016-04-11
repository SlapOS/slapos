portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  # XXX Filter directly the right open sale order
  method_id='OpenSaleOrder_reindexIfIndexedBeforeLine',
  portal_type="Open Sale Order",
  children_portal_type="Open Sale Order Line",
  activate_kw={'tag': tag},
)

context.activate(after_tag=tag).getId()
