if params is None:
  params = {}

from DateTime import DateTime
from Products.ERP5Type.DateUtils import addToDate
from Products.ZSQLCatalog.SQLCatalog import Query

def getAccountingDate(accounting_date):
  accounting_day = 25
  if accounting_date.day() <= accounting_day:
    accounting_date = addToDate(accounting_date, dict(month=-1))
  diff = accounting_day - accounting_date.day()
  accounting_date = addToDate(accounting_date, dict(day=diff))
  return accounting_date

accounting_date = params.get('accounting_date', DateTime().earliestTime())

portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Sale Packing List',
  simulation_state='confirmed',
  causality_state='solved',
  specialise_uid=portal.restrictedTraverse(portal.portal_preferences.getPreferredAggregatedSaleTradeCondition()).getUid(),
  method_id='Delivery_startConfirmedAggregatedSalePackingList',
  activate_kw={'tag': tag},
  **{'delivery.start_date': Query(range="max",
    **{'delivery.start_date': getAccountingDate(accounting_date)})}
)
context.activate(after_tag=tag).getId()
