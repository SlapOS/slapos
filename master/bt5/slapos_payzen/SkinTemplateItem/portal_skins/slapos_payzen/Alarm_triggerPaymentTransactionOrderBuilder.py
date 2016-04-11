context.getPortalObject().portal_orders.slapos_payment_transaction_builder.build(
  activate_kw={'tag': tag}
)
context.activate(after_tag=tag).getId()
