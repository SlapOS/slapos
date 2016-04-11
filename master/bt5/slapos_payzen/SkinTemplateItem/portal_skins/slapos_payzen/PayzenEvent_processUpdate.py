from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

def storeWorkflowComment(ctx, comment):
  portal = ctx.getPortalObject()
  workflow_tool = portal.portal_workflow
  workflow_tool.doActionFor(ctx, 'edit_action', comment=comment)

payzen_event = context
transaction = payzen_event.getDestinationValue()
portal = transaction.getPortalObject()

assert signature in (True, False)
if signature is False:
  # signature is wrong, bye bye
  payzen_event.confirm(comment='Signature does not match')
  return

isTransitionPossible = context.getPortalObject().portal_workflow.isTransitionPossible

error_code = data_kw['errorCode']
if error_code == '2':
  transaction_date, payzen_id = transaction.PaymentTransaction_getPayzenId()
  # Mark on payment transaction history log that transaction was not processed yet
  payzen_event.confirm()
  payzen_event.acknowledge(comment='Transaction not found on payzen side.')
  if int(DateTime()) - int(transaction_date) > 86400:
    if isTransitionPossible(transaction, 'cancel'):
      transaction.cancel(comment='Aborting unknown payzen payment.')
  else:
    storeWorkflowComment(transaction, 
                         'Error code 2 (Not found) did not changed the document state.')
  return

elif error_code == '0':
  transaction_code_mapping = {
    '0': 'Initial (being treated)',
    '1': 'To be validated ',
    '2': 'To be forced - Contact issuer',
    '3': 'To be validated and authorized',
    '4': 'Waiting for submission',
    '5': 'Waiting for authorization',
    '6': 'Submitted',
    '7': 'Expired',
    '8': 'Refused',
    '9': 'Cancelled',
    '10': 'Waiting',
    '11': 'Being submitted',
    '12': 'Being authorized',
    '13': 'Failed',
  }
  mark_transaction_id_list = ['0', '1', '3', '4', '5', '10', '11', '12']
  continue_transaction_id_list = ['6']
  cancel_transaction_id_list = ['8']

  transaction_status = data_kw['transactionStatus']

  transaction_status_description = transaction_code_mapping.get(transaction_status, None)
  if transaction_status_description is None:
    payzen_event.confirm(comment='Unknown transactionStatus %r' % transaction_status)
    return

  doActionFor = context.getPortalObject().portal_workflow.doActionFor

  if transaction_status in mark_transaction_id_list:
    # Mark on payment transaction history log that transaction was not processed yet
    storeWorkflowComment(transaction, 'Transaction status %s (%s) did not changed the document state' % (transaction_status, transaction_status_description))
    payzen_event.confirm()
    payzen_event.acknowledge(comment='Automatic acknowledge as result of correct communication')
    if isTransitionPossible(transaction, 'confirm'):
      transaction.confirm(comment='Confirmed as really saw in PayZen.')

  elif transaction_status in continue_transaction_id_list:
    # Check authAmount and authDevise and if match, stop transaction
    auth_amount = int(data_kw['authAmount'])
    auth_devise = data_kw['authDevise']
    transaction_amount = int(round((transaction.PaymentTransaction_getTotalPayablePrice() * -100), 2))

    if transaction_amount != auth_amount:
      payzen_event.confirm(comment='Received amount (%r) does not match stored on transaction (%r)'% (auth_amount, transaction_amount))
      return

    transaction_devise = transaction.getResourceValue().Currency_getIntegrationMapping()
    if transaction_devise != auth_devise:
      payzen_event.confirm(comment='Received devise (%r) does not match stored on transaction (%r)'% (auth_devise, transaction_devise))
      return

    comment = 'PayZen considered as paid.'
    if isTransitionPossible(transaction, 'confirm'):
      transaction.confirm(comment=comment)
    if isTransitionPossible(transaction, 'start'):
      transaction.start(comment=comment)
    if isTransitionPossible(transaction, 'stop'):
      transaction.stop(comment=comment)

    if transaction.getSimulationState() == 'stopped':
      payzen_event.confirm()
      payzen_event.acknowledge(comment='Automatic acknowledge as result of correct communication')
    else:
      payzen_event.confirm(comment='Expected to put transaction in stopped state, but achieved only %s state' % transaction.getSimulationState())

  elif transaction_status in cancel_transaction_id_list:
    payzen_event.confirm()
    payzen_event.acknowledge(comment='Refused payzen payment.')
    if isTransitionPossible(transaction, 'cancel'):
      transaction.cancel(comment='Aborting refused payzen payment.')
    return
  else:
    payzen_event.confirm(comment='Transaction status %r (%r) is not supported' \
                           % (transaction_status, transaction_status_description))
    return

else:
  # Unknown errorCode
  payzen_event.confirm(comment='Unknown errorCode %r' % error_code)
