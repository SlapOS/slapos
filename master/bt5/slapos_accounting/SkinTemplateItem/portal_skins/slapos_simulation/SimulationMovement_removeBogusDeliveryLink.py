if context.getDelivery() is not None and context.getDeliveryValue() is None:
  activate_kw=dict(tag=tag)
  context.edit(delivery=None, activate_kw=activate_kw)
  context.expand(expand_policy='immediate', activate_kw=activate_kw)
