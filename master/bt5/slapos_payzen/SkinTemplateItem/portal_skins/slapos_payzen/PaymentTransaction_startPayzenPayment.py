from DateTime import DateTime
portal = context.getPortalObject()

state = context.getSimulationState()
transaction_amount = int(round((context.PaymentTransaction_getTotalPayablePrice() * -100), 2))
if (state != 'confirmed') or (context.getPaymentMode() != 'payzen') or (transaction_amount == 0):
  return
else:
  # Request manual payment
  context.start(comment='Requested manual payment')

#   raise NotImplementedError
#   if context.PaymentTransaction_getPreviousPayzenId() is not None:
#     # there is previous payment
#     context.setStartDate(DateTime())
#     context.updateCausalityState()
#     portal.system_event_module.newContent(
#        title='Transaction %s Payzen registration' % context.getTitle(),
#        portal_type='Payzen Event',
#        source_value=service,
#        destination_value=context).registerPayzen()
#     comment='Automatically duplicated in payzen.'
#   else:
