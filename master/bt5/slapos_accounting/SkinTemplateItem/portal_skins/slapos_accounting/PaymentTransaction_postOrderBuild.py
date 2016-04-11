from Products.ERP5Type.Message import translateString
payment_transaction = context
payment_transaction.immediateReindexObject() # in order to avoid selection in OrderBuilder_getAccountingTransactionLineListSlapOS
comment = translateString("Initialised by Order Builder.")
payment_transaction.confirm(comment=comment)
