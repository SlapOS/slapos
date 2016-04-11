from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
payment_service = portal.portal_secure_payments.find(
  service_reference=portal.portal_preferences.getPreferredPayzenPaymentServiceReference())

return payment_service.getRelativeUrl()
