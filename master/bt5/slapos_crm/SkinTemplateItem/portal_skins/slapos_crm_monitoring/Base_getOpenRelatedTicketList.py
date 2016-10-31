"""
  Keep a custom script for permit render other times of documents, ie.: Software Installation.
"""
from Products.ZSQLCatalog.SQLCatalog import ComplexQuery, SimpleQuery

portal = context.getPortalObject()

query = ComplexQuery(
  ComplexQuery(
    SimpleQuery(portal_type="Support Request"),
    SimpleQuery(default_aggregate_uid=context.getUid()),
    logical_operator='and'),
  ComplexQuery(
    SimpleQuery(portal_type="Upgrade Decision Line"),
    SimpleQuery(default_aggregate_uid=context.getUid()),
    logical_operator='and'),
  logical_operator='or')

# Use event modification date instead. 
kw['sort_on'] = (("catalog.simulation_state='suspended'", 'DESC'),
                   ("catalog.simulation_state='validated'", 'DESC'),
                   ("catalog.simulation_state='confirmed'", 'DESC'),
                   ('modification_date', 'DESC'),)
kw['simulation_state'] = "NOT cancelled"
kw['limit'] = 30
result_list = []
for document in portal.portal_catalog(query=query, **kw):
  if document.getPortalType() == "Upgrade Decision Line":
    result_list.append(document.getParentValue())
    continue
  result_list.append(document)
return result_list
