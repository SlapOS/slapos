instance = state_change['object']
portal = instance.getPortalObject()

for requester_instance in portal.portal_catalog(
    portal_type="Software Instance",
    default_predecessor_uid=instance.getUid()):
  requester_instance.getObject().bang(
    bang_tree=False,
    comment="%s parameters changed" % instance.getRelativeUrl())
