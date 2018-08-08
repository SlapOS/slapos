""" Wrapper PaymentTransaction_redirectToManualPayzenPayment to allow
 anonymous pay their Payment Transactions before login.
"""
portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

def wrapWithShadow(payment_transaction, web_site):
  return payment_transaction.PaymentTransaction_redirectToManualPayzenPayment(web_site)

if person is None:
  if portal.portal_membership.isAnonymousUser():
    invoice = context.getCausalityValue()
    if invoice is not None and invoice.getCausalityRelated(portal_type="Subscription Request"):
      person = context.getDestinationSectionValue()

return person.Person_restrictMethodAsShadowUser(
  shadow_document=person,
  callable_object=wrapWithShadow,
  argument_list=[context, web_site])
