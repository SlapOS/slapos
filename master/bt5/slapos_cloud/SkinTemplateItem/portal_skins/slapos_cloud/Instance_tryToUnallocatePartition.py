instance = context
if instance.getSlapState() != 'destroy_requested':
  return

partition = instance.getAggregateValue(portal_type="Computer Partition")
portal = instance.getPortalObject()
if partition is not None:
  # Partition may be managed by another instance at the same time
  # Prevent creating two instances with the same title
  tag = "allocate_%s" % partition.getRelativeUrl()
  if (portal.portal_activities.countMessageWithTag(tag) == 0):
    # No concurrency issue
    instance.unallocatePartition()
    instance_sql_list = portal.portal_catalog(
                          portal_type=["Software Instance", "Slave Instance"],
                          default_aggregate_uid=partition.getUid(),
                        )
    count = len(instance_sql_list)
    if count == 0:
      # Current instance should at least be cataloggued
      pass
    else:
      can_be_free = True
      for instance_sql in instance_sql_list:
        new_instance = instance_sql.getObject()
        if new_instance.getAggregateValue(portal_type="Computer Partition") is not None:
          can_be_free = False
          break
      if can_be_free:
        partition.markFree()
