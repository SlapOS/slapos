from Products.ERP5Type.Message import translateString
from DateTime import DateTime

payment_transaction = context
comment = translateString("Initialised by Delivery Builder.")
payment_transaction.plan(comment=comment)
payment_transaction.confirm(comment=comment)
payment_transaction.start(comment=comment)
payment_transaction.stop(comment=comment)
payment_transaction.deliver(comment=comment)
