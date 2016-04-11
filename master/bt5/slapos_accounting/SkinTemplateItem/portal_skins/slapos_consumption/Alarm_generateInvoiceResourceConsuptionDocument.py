from Products.ERP5Type.DateUtils import addToDate
from Products.ZSQLCatalog.SQLCatalog import Query
from DateTime import DateTime

portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Sale Invoice Transaction',
  simulation_state='confirmed',
  causality_state='solved',
  creation_date=Query(creation_date=addToDate(DateTime(), to_add={'day': -20}), range="min"),
  method_id='SaleInvoiceTransaction_generateResourceConsumptionDocument',
  activity_count=1,
  packet_size=1,
  activate_kw={'tag': tag}
)
context.activate(after_tag=tag, priority=5).getId()
