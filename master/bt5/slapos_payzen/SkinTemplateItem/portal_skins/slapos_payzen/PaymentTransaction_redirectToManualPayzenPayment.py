from zExceptions import Unauthorized
portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if getattr(context, "PaymentTransaction_getVADSUrlDict", None) is None:
  raise ValueError("PaymentTransaction_getVADSUrlDict is missing on this site")

def wrapWithShadow(payment_transaction, person_relative_url):

  vads_url_dict = payment_transaction.PaymentTransaction_getVADSUrlDict()

  _ , transaction_id = payment_transaction.PaymentTransaction_getPayzenId()
  vads_url_already_registered = vads_url_dict.pop('vads_url_already_registered')
  if transaction_id is not None:
    return context.REQUEST.RESPONSE.redirect(vads_url_already_registered)

  system_event = payment_transaction.PaymentTransaction_createPayzenEvent(
    title='User navigation script for %s' % payment_transaction.getTitle(),
    destination_section=person_relative_url,
  )

  system_event.generateManualPaymentPage(
    **vads_url_dict
  )

  return system_event.contentValues(
    portal_type="Payzen Event Message")[0].getTextContent()

if person is None:
  if not portal.portal_membership.isAnonymousUser():
    return wrapWithShadow(context, context.getDestinationSection())
  raise Unauthorized("You must be logged in")

return person.Person_restrictMethodAsShadowUser(
  shadow_document=person,
  callable_object=wrapWithShadow,
  argument_list=[context, person.getRelativeUrl()])
