invoice = context

total_price = invoice.getTotalPrice()
accounting_price = invoice.AccountingTransaction_getTotalCredit()
precision = invoice.getPriceCurrencyValue().getQuantityPrecision()
return round(total_price, precision) == round(accounting_price, precision)
