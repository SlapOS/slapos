person = context.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
if person:
  from Products.ZSQLCatalog.SQLCatalog import Query, NegatedQuery
  return context.getPortalObject().portal_catalog(
    default_destination_section_uid=person.getUid(),
    query=NegatedQuery(Query(title="Reversal Transaction for %")),
    sort_on=(("creation_date", "DESC"),),
    **kw
    )

else:
  return []
