computer_partition_list = context.getAggregateValueList(portal_type="Computer Partition")

master_node = context.SoftwareInstance_getResilientMasterNode()

current_watt = context.SoftwareRelease_getDeltaCO2List(
  computer_partition_list, context.SoftwareInstance_getAverageCPULoad()
)
current_watt = current_watt.keys()

master_node = context.SoftwareInstance_getResilientMasterNode()
if master_node is not None:
  future_watt = context.SoftwareRelease_getDeltaCO2List(
    computer_partition_list, master_node.SoftwareInstance_getAverageCPULoad()
  )
  future_watt = future_watt.keys()[0]

return current_watt, future_watt
