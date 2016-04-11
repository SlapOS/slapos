specialise = context.getSpecialiseValue(portal_type='Sale Trade Condition')
amount_list = specialise.getAggregatedAmountList(context)
if len(amount_list) != 1:
  return False

precision = context.getPriceCurrencyValue().getQuantityPrecision()

amount = amount_list[0]

total_price = amount.getTotalPrice()

invoice_tax = 0.
for line in context.getMovementList(context.getPortalInvoiceMovementTypeList()):
  if line.getUse() == 'trade/tax':
    invoice_tax += line.getTotalPrice()

return round(total_price, precision) == round(invoice_tax, precision)
