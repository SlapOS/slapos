# TODO: Return configured web page in case of system issues.
from ZTUtils import make_query
portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

def wrapWithShadow(payment_transaction, person_relative_url):
  web_site = context.getWebSiteValue()

  transaction_date, transaction_id = payment_transaction.PaymentTransaction_getPayzenId()
  if transaction_id is not None:
    message = payment_transaction.Base_translateString("Payment already registered.")
    return web_site.Base_redirect(keep_items={'portal_status_message': message})

  system_event = payment_transaction.PaymentTransaction_createPayzenEvent(
    title='User navigation script for %s' % payment_transaction.getTitle(),
    destination_section=person_relative_url,
  )

  callback_websection = web_site.payzen_callback
  query = make_query(dict(transaction=payment_transaction.getRelativeUrl()))
  system_event.generateManualPaymentPage(
    vads_url_cancel='%s?%s' % (callback_websection.cancel.absolute_url(), query),
    vads_url_error='%s?%s' % (callback_websection.error.absolute_url(), query),
    vads_url_referral='%s?%s' % (callback_websection.referral.absolute_url(), query),
    vads_url_refused='%s?%s' % (callback_websection.refused.absolute_url(), query),
    vads_url_success='%s?%s' % (callback_websection.success.absolute_url(), query),
    vads_url_return='%s?%s' % (getattr(callback_websection, 'return').absolute_url(), query),
  )

  return system_event.contentValues(
    portal_type="Payzen Event Message")[0].getTextContent()


return person.Person_restrictMethodAsShadowUser(
  shadow_document=person,
  callable_object=wrapWithShadow,
  argument_list=[context, person.getRelativeUrl()])
