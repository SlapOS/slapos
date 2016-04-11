if context.getPortalType() == 'Sale Packing List' \
  and context.getSpecialise() == 'sale_trade_condition_module/slapos_consumption_trade_condition':
  # no rule for consumption
  return None
return 'default_delivery_rule'
