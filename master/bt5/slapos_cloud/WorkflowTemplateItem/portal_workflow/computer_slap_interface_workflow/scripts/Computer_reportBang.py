computer = state_change['object']
portal = computer.getPortalObject()
for computer_partition in [x for x in computer.contentValues(portal_type='Computer Partition') if x.getSlapState() == 'busy']:
  for instance_sql in portal.portal_catalog(
                        default_aggregate_uid=computer_partition.getUid(),
                        portal_type=["Software Instance", "Slave Instance"],
                        ):
    instance = instance_sql.getObject()
    if instance.getSlapState() in ["start_requested", "stop_requested"]:
      instance.activate().SoftwareInstance_bangAsSelf(
        relative_url=instance.getRelativeUrl(),
        reference=instance.getReference(), 
        comment=state_change.kwargs.get('comment', ''))
