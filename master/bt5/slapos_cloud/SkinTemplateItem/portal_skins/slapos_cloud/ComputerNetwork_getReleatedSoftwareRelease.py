portal = context.getPortalObject()
network = context

computter_list_uid = [x.getUid() for x in network.getSubordinationRelatedValueList()]
kw['portal_type']='Software Installation'
kw['validation_state']='validated'
kw['default_aggregate_uid']=computter_list_uid

return portal.portal_catalog(**kw)
