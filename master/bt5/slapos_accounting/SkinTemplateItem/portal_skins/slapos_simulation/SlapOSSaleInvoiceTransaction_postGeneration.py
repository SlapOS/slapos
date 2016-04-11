"""This script is called on the Invoice after the delivery builder has created
the new Invoice.
"""
from Products.ERP5Type.Message import translateString
from DateTime import DateTime
if related_simulation_movement_path_list is None:
  raise RuntimeError, 'related_simulation_movement_path_list is missing. Update ERP5 Product.'

invoice = context
price_currency = invoice.getPriceCurrency()
if invoice.getResource() != price_currency:
  invoice.setResource(price_currency)
if invoice.getPaymentMode("") == "":
  invoice.setPaymentModeValue(invoice.getPortalObject().portal_categories.payment_mode.payzen)
comment = translateString('Initialised by Delivery Builder.')
if invoice.portal_workflow.isTransitionPossible(invoice, 'plan'):
  invoice.plan(comment=comment)
if invoice.portal_workflow.isTransitionPossible(invoice, 'confirm'):
  invoice.confirm(comment=comment)
invoice.startBuilding(comment=comment)
