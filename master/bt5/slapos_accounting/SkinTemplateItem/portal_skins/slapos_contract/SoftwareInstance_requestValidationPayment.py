from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
software_instance = context
hosting_subscription = software_instance.getSpecialiseValue()
person = hosting_subscription.getDestinationSectionValue(portal_type='Person')
payment_portal_type = "Payment Transaction"
contract_portal_type = "Cloud Contract"

tag = "%s_requestValidationPayment_inProgress" % person.getUid()
if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The cloud contract is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  return None

contract = portal.portal_catalog.getResultValue(
  portal_type=contract_portal_type,
  default_destination_section_uid=person.getUid(),
  validation_state=['invalidated', 'validated'],
)

if (contract is None):
  # Prevent concurrent transaction to create 2 contracts for the same person
  person.serialize()

  # Time to create the contract
  contract = portal.cloud_contract_module.newContent(
    portal_type=contract_portal_type,
    title='Contract for "%s"' % person.getTitle(),
    destination_section_value=person
  )
  contract.validate(comment='New automatic contract for %s' % context.getTitle())
  contract.invalidate(comment='New automatic contract for %s' % context.getTitle())

  contract.reindexObject(activate_kw={'tag': tag})

if (contract.getValidationState() == "invalidated"):
  # Prevent concurrent transaction to create 2 invoices for the same person
  person.serialize()

  # search if the user already paid anything
  payment = portal.portal_catalog.getResultValue(
    portal_type=payment_portal_type,
    default_destination_section_uid=person.getUid(),
    simulation_state=['stopped'],
  )

  if (payment is None):
    # Manually create an invoice to request payment validation
    current_invoice = contract.getCausalityValue()

    if current_invoice is None:
      # Create the validation invoice
      # XXX Hardcoded
      invoice_template = portal.restrictedTraverse("accounting_module/template_contract_sale_invoice_transaction")
      current_invoice = invoice_template.Base_createCloneDocument(batch_mode=1)
      contract.edit(causality_value=current_invoice)
      contract.reindexObject(activate_kw={'tag': tag})

      current_invoice.edit(
        title="Account validation",
        source_value=person,
        destination_value=person,
        destination_section_value=person,
        destination_decision_value=person,
        start_date=DateTime(),
        stop_date=None,
      )
      comment = "Validation invoice for contract %s" % contract.getRelativeUrl()
      current_invoice.plan(comment=comment)
      current_invoice.confirm(comment=comment)
      current_invoice.startBuilding(comment=comment)
      current_invoice.reindexObject(activate_kw={'tag': tag})


    else:
      # Check if the invoice is still ongoing
      simulation_state = current_invoice.getSimulationState() 

      if simulation_state in ("planned", "confirmed", "ordered", "started"):
        # Waiting for payment
        result = "ongoing"
      elif simulation_state in ("cancelled", "deleted", "draft"):
        result = "cancelled"
      elif simulation_state in ("stopped", "delivered"):
        # Invoice is in final state.
        paid = True
        for line in current_invoice.getMovementList(portal.getPortalAccountingMovementTypeList()):
          node_value = line.getSourceValue(portal_type='Account')

          if node_value.getAccountType() == 'asset/receivable':
            if not line.hasGroupingReference():
              paid = False
              break

        if paid:
          result = "paid"
        else:
          result = "ongoing"

      else:
        raise NotImplementedError, "Unknow state %s" % simulation_state

      if result in ("paid", "cancelled"):
        # Maybe have been paid or not (mirror invoice may have been created)
        # Check in next alarm loop for a payment
        contract.edit(causality_value=None)
        contract.reindexObject(activate_kw={'tag': tag})

  else:
    # Found one payment, the contract can be validated
    comment = "Contract validated as paid payment %s found" % payment.getRelativeUrl()
    contract.validate(comment=comment)
    contract.reindexObject(activate_kw={'tag': tag})

return contract
