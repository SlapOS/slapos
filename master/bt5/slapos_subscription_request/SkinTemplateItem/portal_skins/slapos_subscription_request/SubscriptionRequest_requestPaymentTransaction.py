from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()

current_invoice = context.getCausalityValue()

if current_invoice is None:
  # Create the Pre-Payment Invoice invoice
  # XXX Hardcoded
  invoice_template = portal.restrictedTraverse("accounting_module/template_pre_payment_subscription_sale_invoice_transaction")
  current_invoice = invoice_template.Base_createCloneDocument(batch_mode=1)
  context.edit(causality_value=current_invoice)

  current_invoice.edit(
        title="Reservation Fee",
        source_value=context.getDestinationSection(),
        destination_value=context.getDestinationSection(),
        destination_section_value=context.getDestinationSection(),
        destination_decision_value=context.getDestinationSection(),
        start_date=DateTime(),
        stop_date=DateTime(),
      )
  current_invoice["1"].setQuantity(amount)

  comment = "Validation invoice for subscription request %s" % context.getRelativeUrl()
  current_invoice.plan(comment=comment)
  current_invoice.confirm(comment=comment)
  current_invoice.startBuilding(comment=comment)
  current_invoice.reindexObject(activate_kw={'tag': tag})

  payment_template = portal.restrictedTraverse("accounting_module/slapos_pre_payment_template")
  current_payment = payment_template.Base_createCloneDocument(batch_mode=1)

  current_payment.edit(
        title="Payment for Reservation Fee",
        source_value=context.getDestinationSection(),
        destination_value=context.getDestinationSection(),
        destination_section_value=context.getDestinationSection(),
        destination_decision_value=context.getDestinationSection(),
        start_date=current_invoice.getStartDate(),
        stop_date=current_invoice.getStopDate(),
        causality_value=current_invoice
      )
  quantity = int(amount)*19.95
  for line in current_payment.contentValues():
    if line.getSource() == "account_module/bank":
      line.setQuantity(-1*quantity)
    if line.getSource() == "account_module/receivable":
      line.setQuantity(quantity)

  # Accelarate job of alarms before proceed to payment.
  comment = "Validation payment for subscription request %s" % context.getRelativeUrl()
  current_payment.confirm(comment=comment)
  current_payment.start(comment=comment)
  current_payment.PaymentTransaction_updateStatus()
  current_payment.reindexObject(activate_kw={'tag': tag})
  context.immediateReindexObject()
  context.reindexObject(activate_kw={'tag': tag})


return current_payment
