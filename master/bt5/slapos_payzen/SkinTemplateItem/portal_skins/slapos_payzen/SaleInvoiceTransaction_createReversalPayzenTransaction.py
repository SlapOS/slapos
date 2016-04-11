""" Create a reversal transaction from current payzen transaction. """
from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()

# Check that we are in state that we are waiting for user manual payment
assert context.getPortalType() == 'Sale Invoice Transaction'
assert context.getPaymentMode() == 'payzen'
assert context.getSimulationState() == 'stopped'
assert context.getTotalPrice() != 0
assert context.getSpecialise() == "sale_trade_condition_module/slapos_aggregated_trade_condition"

paid = True
for line in context.getMovementList(portal.getPortalAccountingMovementTypeList()):
  node_value = line.getSourceValue(portal_type='Account')
  if node_value.getAccountType() == 'asset/receivable':
    if not line.hasGroupingReference():
      paid = False
      break
assert not paid

payment = portal.portal_catalog.getResultValue(
  portal_type="Payment Transaction",
  simulation_state="started",
  default_causality_uid=context.getUid(),
  default_payment_mode_uid=portal.portal_categories.payment_mode.payzen.getUid(),
)
assert payment is not None
assert payment.getSimulationState() == 'started'
assert payment.getPaymentMode() == 'payzen'
assert payment.PaymentTransaction_getPayzenId()[1] is None

# Should be safe now to fix everything
context.edit(payment_mode=None)
payment.edit(payment_mode=None)
reversal_transaction = context.Base_createCloneDocument(batch_mode=1)
payment.cancel(
  comment="Reversal sale invoice transaction created %s" % reversal_transaction.getRelativeUrl())

reversal_transaction.edit(
  title="Reversal Transaction for %s" % context.getTitle(),
  causality_value=context,
  description="Reversal Transaction for %s" % context.getTitle(),
  specialise_value=portal.sale_trade_condition_module.slapos_manual_accounting_trade_condition,
)

for line in reversal_transaction.getMovementList():
  line.edit(quantity=(-line.getQuantity()))

reversal_transaction.confirm(comment="Automatic because of reversal creation")
reversal_transaction.stop(comment="Automatic because of reversal creation")

return reversal_transaction
