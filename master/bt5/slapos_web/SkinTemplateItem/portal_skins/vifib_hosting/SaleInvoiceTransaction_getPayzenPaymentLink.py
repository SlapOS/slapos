result = None
if context.AccountingTransaction_getPaymentState() == "Pay now":
  portal = context.getPortalObject()
  payment = portal.portal_catalog.getResultValue(
    portal_type="Payment Transaction",
    simulation_state="started",
    default_causality_uid=context.getUid(),
    default_payment_mode_uid=portal.portal_categories.payment_mode.payzen.getUid(),
  )
  if payment is not None:
    result = "%s/PaymentTransaction_redirectToManualPayzenPayment" % payment.absolute_url()
  
return result
