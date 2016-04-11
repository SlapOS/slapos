payzen_event = state_change['object']
payment_transaction = payzen_event.getDestinationValue(portal_type="Payment Transaction")
portal = payment_transaction.getPortalObject()

transaction_date, transaction_id = payment_transaction.PaymentTransaction_getPayzenId()
if transaction_id is None:
  raise ValueError('Transaction not registered in payzen integration tool')

payment_service = payzen_event.getSourceValue(portal_type="Payzen Service")
data_kw, signature, sent_text, received_text = payment_service.soap_getInfo(
  transaction_date.toZone('UTC').asdatetime(),
  transaction_id)

sent = payzen_event.newContent(
  title='Sent SOAP', 
  portal_type='Payzen Event Message', 
  text_content=sent_text)
received = payzen_event.newContent(
  title='Received SOAP', 
  portal_type='Payzen Event Message', 
  text_content=received_text, 
  predecessor_value=sent)
payzen_event.PayzenEvent_processUpdate(data_kw, signature)
