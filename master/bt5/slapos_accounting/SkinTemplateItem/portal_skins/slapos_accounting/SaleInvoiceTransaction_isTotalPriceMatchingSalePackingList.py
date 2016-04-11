invoice = context
specialise = context.getPortalObject().portal_preferences.getPreferredAggregatedSaleTradeCondition()
if invoice.getSpecialise() != specialise:
  raise TypeError('Only invoice specialised by %s shall be checked' % specialise)

if len(invoice.getCausalityRelatedList(portal_type='Cloud Contract')) > 0:
  # Nothing to compare
  return True


delivery_list = invoice.getCausalityValueList(portal_type='Sale Packing List')
amount = len(delivery_list)
if amount != 1:
  raise TypeError('Wrong amount %s of related packing lists' % amount)
delivery = delivery_list[0]

return delivery.getTotalPrice(use='use/trade/sale') == context.getTotalPrice(use='use/trade/sale')
