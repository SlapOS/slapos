import json

state = context.AccountingTransaction_getPaymentState()
payment_transaction = None
if state == "Pay now":
  payment_transaction = context.SaleInvoiceTransaction_getPayzenPaymentRelatedValue().getRelativeUrl()

return json.dumps({"state": state,
                   "payment_transaction": payment_transaction})
