instance = state_change['object']
assert instance.getPortalType() in ["Software Instance", "Slave Instance"]
portal = instance.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  computer_partition_url = kwargs['computer_partition_url']
except KeyError:
  raise TypeError, "RequestedInstance_allocatePartition takes exactly 1 argument"

assert instance.getAggregateValue() is None
computer_partition = portal.restrictedTraverse(computer_partition_url)
assert computer_partition.getPortalType() == "Computer Partition"

instance.edit(aggregate_value=computer_partition, activate_kw={'tag': 'allocate_%s' % computer_partition_url})
