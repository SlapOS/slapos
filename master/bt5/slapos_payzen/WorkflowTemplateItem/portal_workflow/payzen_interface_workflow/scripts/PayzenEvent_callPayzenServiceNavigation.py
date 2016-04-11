from DateTime import DateTime
payzen_event = state_change['object']

payment_service = payzen_event.getSourceValue(portal_type="Payzen Service")
return payment_service.navigate(
  page_template='payzen_payment',
  pay='Click to pay',
  payzen_dict=payzen_dict,
)
