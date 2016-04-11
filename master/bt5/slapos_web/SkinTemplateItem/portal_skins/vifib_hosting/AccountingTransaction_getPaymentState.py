simulation_state = context.getSimulationState() 

if simulation_state in ("cancelled", "deleted", "draft"):
  result = "Cancelled"

elif simulation_state in ("planned", "confirmed", "ordered", "started"):
  result = "Ongoing"

else:
  portal = context.getPortalObject()

  paid = True
  for line in context.getMovementList(portal.getPortalAccountingMovementTypeList()):
    node_value = line.getSourceValue(portal_type='Account')
    if node_value.getAccountType() == 'asset/receivable':
      if not line.hasGroupingReference():
        paid = False
        break

  reversal = portal.portal_catalog.getResultValue(
      portal_type="Sale Invoice Transaction",
      simulation_state="stopped",
      default_causality_uid=context.getUid()
    )
  if reversal is not None and (context.getTotalPrice() + reversal.getTotalPrice()) == 0:
    result = "Cancelled"
  elif paid:
    result = "Paid"
  elif context.getTotalPrice() == 0:
    result = "Free!"
  else:
    # Check if there is an ongoing payzen payment
    payment = portal.portal_catalog.getResultValue(
      portal_type="Payment Transaction",
      simulation_state="started",
      default_causality_uid=context.getUid(),
      default_payment_mode_uid=portal.portal_categories.payment_mode.payzen.getUid(),
    )
    if payment is None:
      result = "Unpaid"
    else:
      # Check if mapping exists
      person = portal.ERP5Site_getAuthenticatedMemberPersonValue()
      payzen_id = person.Person_restrictMethodAsShadowUser(
        shadow_document=person,
        callable_object=payment.PaymentTransaction_getPayzenId,
        argument_list=[])[0]
      if payzen_id is None:
        result = "Pay now"
      else:
        result = "Waiting for payment confirmation"

return result
