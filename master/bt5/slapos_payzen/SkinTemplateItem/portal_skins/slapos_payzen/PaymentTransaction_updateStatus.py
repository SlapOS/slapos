from DateTime import DateTime
portal = context.getPortalObject()

state = context.getSimulationState()
if (state != 'started') or (context.getPaymentMode() != 'payzen'):
  return
else:
  transaction_date, transaction_id = context.PaymentTransaction_getPayzenId()

  if transaction_id is not None:
    # so the payment is registered in payzen
    context.PaymentTransaction_createPayzenEvent().updateStatus()
