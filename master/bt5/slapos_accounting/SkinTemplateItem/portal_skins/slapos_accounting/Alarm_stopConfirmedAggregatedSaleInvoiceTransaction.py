from DateTime import DateTime
from Products.ERP5Type.DateUtils import getClosestDate

portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Sale Invoice Transaction',
  simulation_state='confirmed',
  causality_state='solved',
  specialise_uid=portal.restrictedTraverse(portal.portal_preferences.getPreferredAggregatedSaleTradeCondition()).getUid(),
  method_id='Delivery_stopConfirmedAggregatedSaleInvoiceTransaction',
  activate_kw={'tag': tag}
)
context.activate(after_tag=tag).getId()
