from DateTime import DateTime
instance = state_change['object']
assert instance.getPortalType() in ["Slave Instance", "Software Instance"]

instance.edit(bang_timestamp=int(DateTime()))
comment = state_change.kwargs['comment'] # comment is required to pass the transition
if state_change.kwargs['bang_tree']:
  from Products.ZSQLCatalog.SQLCatalog import Query, NegatedQuery
  portal = instance.getPortalObject()
  hosting_subscription = instance.getSpecialiseValue(portal_type="Hosting Subscription")
  portal.portal_catalog.searchAndActivate(
    default_specialise_uid=hosting_subscription.getUid(),
    path=NegatedQuery(Query(path=instance.getPath())),
    portal_type=["Slave Instance", "Software Instance"],
    method_id='bang',
    method_kw={'bang_tree': False, 'comment': comment},
  )
