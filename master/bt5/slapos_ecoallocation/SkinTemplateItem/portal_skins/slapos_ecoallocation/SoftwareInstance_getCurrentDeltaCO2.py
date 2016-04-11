if REQUEST is not None:
  raise Unauthorized

computer_partition_list = context.getAggregateValueList(portal_type="Computer Partition")

current_watt = context.SoftwareRelease_getDeltaCO2List(
  computer_partition_list, context.SoftwareInstance_getAverageCPULoad()
)

return current_watt.keys()[0]
