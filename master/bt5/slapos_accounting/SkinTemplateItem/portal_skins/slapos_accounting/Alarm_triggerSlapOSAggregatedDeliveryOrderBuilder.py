context.getPortalObject().portal_orders.slapos_aggregated_delivery_builder.build(
  activate_kw={'tag': tag}
)
context.activate(after_tag=tag).getId()
