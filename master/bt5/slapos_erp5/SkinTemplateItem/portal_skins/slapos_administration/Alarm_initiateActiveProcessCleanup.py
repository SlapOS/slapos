from Products.ERP5Type.DateUtils import addToDate
from Products.ZSQLCatalog.SQLCatalog import Query
from DateTime import DateTime

context.portal_catalog.searchAndActivate(
  portal_type='Active Process',
  creation_date=Query(creation_date=addToDate(DateTime(), to_add={'day': -21}), range="max"),
  method_id='ActiveProcess_deleteSelf',
  activate_kw={'tag': tag}
)


# register activity on alarm object waiting for own tag in order to have only one alarm
# running in same time
context.activate(after_tag=tag).getId()
