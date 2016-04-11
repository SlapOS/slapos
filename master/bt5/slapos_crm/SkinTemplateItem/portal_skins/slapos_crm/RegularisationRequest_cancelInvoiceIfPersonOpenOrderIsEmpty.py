from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

mail_message = None
invoice_list = []

state = context.getSimulationState()
person = context.getSourceProjectValue(portal_type="Person")
if (state != 'suspended') or \
   (person is None):
  return mail_message, invoice_list
else:
  portal = context.getPortalObject()

  open_order = portal.portal_catalog.getResultValue(
    portal_type="Open Sale Order",
    validation_state="validated",
    default_destination_decision_uid=person.getUid())

  if (open_order is None) or \
   (open_order.getValidationState() != "validated") or \
   (len(open_order.contentValues(portal_type="Open Sale Order Line")) != 0):
    return mail_message, invoice_list
  else:
    assert open_order.getDestinationDecisionUid() == person.getUid()
    ticket = context

    for payment in portal.portal_catalog(
          portal_type="Payment Transaction", 
          payment_mode_uid=portal.portal_categories.payment_mode.payzen.getUid(),
          default_destination_section_uid=person.getUid(),
          simulation_state=["started"],
          ):
      
      if payment.PaymentTransaction_getPayzenId()[1] is None:
        invoice = payment.getCausalityValue(portal_type="Sale Invoice Transaction")
        assert payment.getDestinationSectionUid() == person.getUid()
        invoice.SaleInvoiceTransaction_createReversalPayzenTransaction()
        invoice_list.append(invoice.getRelativeUrl())

    # XXX Hardcoded
    cancel_service = portal.service_module.slapos_crm_invoice_cancellation
    mail_message = ticket.RegularisationRequest_checkToSendUniqEvent(
      cancel_service.getRelativeUrl(),
      'Cancellation of your bill',
      """Hello,

Thank you to have used our decentralized Cloud Computing service slapos.org.

We noticed that all your instances have been removed upon receiving your bill, so we conclude that the instances that you requested were not being used but probably ordered then forgotten.

To not to charge our first users a "non use" of our service, we have choosen to cancel your bill. That's mean: *You have nothing to pay us.*

We hope to see you using our services in the future.

Regards,
The slapos team
""",
      'Cancelled payment.')

return mail_message, invoice_list
